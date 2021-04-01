const { RateLimiterMemory } = require('rate-limiter-flexible');

const { processAlerts } = require('./alerting2.js');
const { goog } = require('./google.js');
const { isNode } = require('./compat.js');
const clientlib = require('./clientlib.js');

const FOLDER_NAME = `opsgrid${isNode() ? '' : '-gas'}`;
const WRITE_ROW_METADATA_ID = 507892; // it's unclear what project-scoped metadata can collide with, so use a random number
const SHEET_ID = 0; // ie, the autocreated sheet TODO this could break if they delete it, since you can't recreate it probably
const MAX_CELLS = 4000000; // google's max is 5 million
// const MAX_CELLS = 100

const oneMinRateLimiter = new RateLimiterMemory(
  {
    points: 1,
    duration: 60 * 0.75, // wiggle room
  });

async function handleRequest(auth, tgRequest, ingestToken) {
  console.log('handling', tgRequest);

  const hostsMetrics = getHostsMetrics(tgRequest);
  console.info('hosts:', Object.keys(hostsMetrics));

  const folderId = await ensureFolder(auth);
  console.log('folder id:', folderId);

  for (const host in hostsMetrics) {
    const hostMetrics = hostsMetrics[host];

    const key = `${ingestToken}:${host}`;
    try {
      await oneMinRateLimiter.consume(key, 1);
    } catch (e) {
      console.warn(`rate limited ${key}`);
      // TODO return something to the client?
      // would probably cause them to retry
      // TODO report to backend/user?
      continue;
    }

    // TODO each host can be done in parallel
    const spreadsheetId = await ensureSpreadsheet(auth, folderId, host);
    console.log('spreadsheet id:', spreadsheetId);
    const writeRow = await ensureWriteMetadata(auth, spreadsheetId);
    console.log('writeRow', writeRow);

    // TODO gas only later on (ie node alert storage in db)
    // const alertsMetadata = await ensureAlertsMetadata(auth, spreadsheetId);
    // console.log('alerts metadata', alertsMetadata);

    // TODO probably all of these can be batched
    const gridInfo = await prepGrid(auth, spreadsheetId, hostMetrics, writeRow);
    console.log('gridInfo', gridInfo);
    await ensureHeaders(auth, spreadsheetId, gridInfo);
    console.log('headers ready');
    const rowsWritten = await appendRows(auth, spreadsheetId, gridInfo, hostMetrics, writeRow);
    console.log('rowsWritten', rowsWritten);
    let newWriteRow = (writeRow + rowsWritten) % gridInfo.numRows;
    if (newWriteRow < writeRow) {
      // we wrapped. skip the header row
      newWriteRow++;
    }
    console.log('updating write row to', newWriteRow);
    await updateWriteRow(auth, spreadsheetId, newWriteRow);

    console.log('checking alerts');
    const alerts = await clientlib.getAlerts(ingestToken);
    await processAlerts(ingestToken, hostMetrics, alerts, writeRow, newWriteRow);

    console.log('reporting row');
    await clientlib.reportRows(ingestToken, hostMetrics, spreadsheetId);

    console.log('done');
  }

  return {};
}

async function ensureSpreadsheet(auth, folderId, host) {
  // return spreadsheet id
  let res = await goog(
    'drive.files.list',
    {
      query: {
        maxResults: 1,
        q: `title='${host}' and mimeType='application/vnd.google-apps.spreadsheet' and '${folderId}' in parents and trashed = false`,
        fields: 'items(id, title)',
      },
    },
    { version: 'v2', auth },
  );
  const files = res.items;

  if (files.length) {
    console.log('spreadsheet exists');
    return files[0].id;
  }

  console.log('creating spreadsheet');
  const fileMetadata = {
    title: host,
    mimeType: 'application/vnd.google-apps.spreadsheet',
    parents: [{ id: folderId }],
  };
  res = await goog(
    'drive.files.insert',
    {
      body: fileMetadata,
      // query: {
      //   uploadType: 'multipart',
      //   fields: 'id',
      // }
    },
    { version: 'v2', auth },
  );

  console.log('renaming sheet');
  const requests = [{
    updateSheetProperties: {
      properties: {
        sheetId: SHEET_ID,
        title: "opsgrid",
      },
      fields: "title",
    },
  }];

  const renameResult = await goog(
    'sheets.spreadsheets.batchUpdate',
    {
      body: { requests },
      path: { spreadsheetId: res.id },
    },
    { version: 'v4', auth },
  );
  console.log(renameResult);

  return res.id;
}

async function ensureWriteMetadata(auth, spreadsheetId) {
  let writeRow = await getWriteRow(auth, spreadsheetId);
  if (!writeRow) { // ok since it's never 0
    console.log('initializing write metadata');
    await createWriteRow(auth, spreadsheetId, 1);
    writeRow = 1;
  }
  return writeRow;
}

async function getWriteRow(auth, spreadsheetId) {
  let res;
  try {
    res = await goog(
      'sheets.spreadsheets.developerMetadata.get',
      {
        path: { spreadsheetId, metadataId: WRITE_ROW_METADATA_ID },
      },
      { version: 'v4', auth },
    );
  } catch (e) {
    if (e.code === 404 || // node
        (e.details && e.details.code === 404)) { // gas
      return undefined;
    }
    throw e;
  }
  console.log('got write metadata', res);
  return parseInt(res.metadataValue, 10);
}

async function createWriteRow(auth, spreadsheetId, rowIndex) {
  // TODO this seems to create duplicate rows
  const requests = [{
    createDeveloperMetadata: {
      developerMetadata: {
        metadataId: WRITE_ROW_METADATA_ID,
        metadataKey: 'writeRow',
        metadataValue: rowIndex.toString(),
        location: { sheetId: SHEET_ID },
        visibility: 'PROJECT',
      },
    },
  }];

  const result = await goog(
    'sheets.spreadsheets.batchUpdate',
    {
      body: { requests },
      path: { spreadsheetId },
    },
    { version: 'v4', auth },
  );
  return result;
}

async function updateWriteRow(auth, spreadsheetId, rowIndex) {
  const requests = [{
    updateDeveloperMetadata: {
      dataFilters: {
        developerMetadataLookup: {
          locationType: 'SHEET',
          metadataId: WRITE_ROW_METADATA_ID,
        },
      },
      developerMetadata: {
        metadataValue: rowIndex.toString(),
      },
      fields: 'metadataValue',
    },
  }];

  const result = await goog(
    'sheets.spreadsheets.batchUpdate',
    {
      body: { requests },
      path: { spreadsheetId },
    },
    { version: 'v4', auth },
  );
  return result;
}

function getHostsMetrics(tgRequest) {
  // $host.rows.$timestamp.$colName = $value
  // $host.headerSet = Set()
  // $host.host = $host
  const hostsMetrics = {};
  const metrics = tgRequest.metrics || [tgRequest];
  for (const metric of metrics) {
    const host = metric.tags.host;
    const inputName = metric.name;
    const colSuffixTags = Object.keys(metric.tags).filter(k => k !== 'host').map(k => metric.tags[k]).sort();
    const timestamp = metric.timestamp;

    hostsMetrics[host] = hostsMetrics[host] || { rows: {}, headerSet: new Set(), host };
    hostsMetrics[host].rows[timestamp] = hostsMetrics[host].rows[timestamp] || {};

    const row = hostsMetrics[host].rows[timestamp];
    const headerSet = hostsMetrics[host].headerSet;
    for (const fieldName in metric.fields) {
      const header = [inputName, fieldName, ...colSuffixTags].join(':');
      headerSet.add(header);
      row[header] = metric.fields[fieldName];
    }

    // handle the timestamp like other columns
    // TODO make this on the left always
    headerSet.add('timestamp');
    row.timestamp = timestamp;
    // row.timestamp = Date.now()
  }

  // sort rows by timestamp (iteration is in order of insertion)
  for (const host in hostsMetrics) {
    const hostMetrics = hostsMetrics[host];
    const orderedRows = {};
    Object.keys(hostMetrics.rows).sort().forEach(function(timestamp) {
      orderedRows[timestamp] = hostMetrics.rows[timestamp];
    });
    hostMetrics.rows = orderedRows;
  }

  return hostsMetrics;
}

async function ensureFolder(auth) {
  // return folder id
  let res = await goog(
    'drive.files.list',
    {
      query: {
        maxResults: 1,
        q: `title='${FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed = false`,
        fields: 'items(id, title)',
      },
    },
    { version: 'v2', auth },
  );
  const files = res.items;
  if (files.length) {
    console.log('folder exists');
    return files[0].id;
  }

  console.log('creating folder', FOLDER_NAME);
  const fileMetadata = {
    title: FOLDER_NAME,
    mimeType: 'application/vnd.google-apps.folder',
  };
  res = await goog(
    'drive.files.insert',
    {
      body: fileMetadata,
      // I can't figure out how to support this in gas.
      // It needs a blob arg between them, and that seems to override my mimeType.
      // query: {
      //   uploadType: 'multipart',
      //   fields: 'id'
      // }
    },
    { version: 'v2', auth },
  );
  return res.id;
}

async function prepGrid(auth, spreadsheetId, hostMetrics, writeRow) {
  const res = await goog(
    'sheets.spreadsheets.get',
    {
      path: { spreadsheetId },
      query: {
        ranges: ['A1:ZZZ1'],
        includeGridData: true,
      },
    },
    { version: 'v4', auth },
  );
  let dataSheet;
  console.log(res);
  for (const sheet of res.sheets) {
    if (sheet.properties.sheetId === SHEET_ID) {
      dataSheet = sheet;
      break;
    }
  }
  if (!dataSheet) {
    throw Error(`default sheet not found in ${res.sheets}`);
  }
  console.log('sheet', dataSheet);
  const curRows = dataSheet.properties.gridProperties.rowCount;
  const curCols = dataSheet.properties.gridProperties.columnCount;
  const gridInfo = {};
  let wantRows, wantCols;
  if (dataSheet.data[0].rowData) {
    console.log('sheet is populated');
    const headers = dataSheet.data[0].rowData[0].values.map(cell => cell.effectiveValue ? cell.effectiveValue.stringValue : undefined);
    const headerSet = new Set(headers);
    const incomingHeaderSet = hostMetrics.headerSet;

    const newHeaders = [...incomingHeaderSet].filter(x => !headerSet.has(x));
    console.log('new headers', newHeaders);
    const extraHeaders = headers.filter(x => !incomingHeaderSet.has(x));
    console.log('extra headers', extraHeaders);

    wantCols = curCols + newHeaders.length; // TODO this breaks if there are empty trailing cols -- is that a problem?
    wantRows = Math.trunc(MAX_CELLS / wantCols);

    Object.assign(gridInfo, {
      newHeaders,
      extraHeaders,
      effectiveHeaders: headers.concat(newHeaders),
      numRows: wantRows,
    });
  } else {
    console.log('sheet is empty');

    // ensure the timestamp is the leftmost column
    hostMetrics.headerSet.delete('timestamp');
    const newHeaders = ['timestamp', ...hostMetrics.headerSet];
    hostMetrics.headerSet.add('timestamp');

    wantCols = newHeaders.length;
    wantRows = Math.trunc(MAX_CELLS / wantCols);
    Object.assign(gridInfo, {
      newHeaders: newHeaders,
      effectiveHeaders: newHeaders,
      numRows: wantRows,
    });
  }
  console.log('syncing for', gridInfo);
  await syncGrid(auth, spreadsheetId, writeRow, curRows, curCols, wantRows, wantCols);
  return gridInfo;
}

async function syncGrid(auth, spreadsheetId, writeRow, curRows, curCols, wantRows, wantCols) {
  const rowDiff = wantRows - curRows;
  const colDiff = wantCols - curCols;
  let writeRowAdjustment = 0;
  console.log('have', curRows, curCols, wantRows, wantCols);
  console.log('diff', rowDiff, colDiff);
  const requests = [];
  for (const [dimension, diff] of [['ROWS', rowDiff], ['COLUMNS', colDiff]]) {
    if (diff === 0) {
      continue;
    }
    const op = diff < 0 ? 'deleteDimension' : 'appendDimension';

    // these may be shallow copied
    const request = {};
    const body = {
      sheetId: SHEET_ID,
      dimension,
    };

    if (op === 'appendDimension') {
      body.length = diff;
      request[op] = body;
      requests.push(request);
    } else {
      if (dimension === 'ROWS' && writeRow + diff >= curRows) {
        // ranges won't wrap; create two if needed
        const topSheetRequest = { ...request };
        const topSheetBody = { ...body };
        topSheetBody.startIndex = 1;
        topSheetBody.endIndex = curRows - writeRow; // not inclusive
        topSheetRequest[op] = { range: topSheetBody };
        requests.unshift(request); // the bottom sheet delete will be prepended before this one so the indices are stable

        body.startIndex = writeRow + 1;
        body.endIndex = curRows;
        request[op] = { range: body };
        requests.unshift(request);

        // move up the write row by the rows we deleted
        writeRowAdjustment = topSheetBody.endIndex - topSheetBody.startIndex;
      } else if (dimension === 'ROWS') {
        // deleting rows without wrapping
        body.startIndex = writeRow + 1;
        body.endIndex = writeRow + 1 + Math.abs(diff);
        request[op] = { range: body };
        // delete before add to ensure we don't exceed capacity temporarily (operations are applied one at a time)
        requests.unshift(request);
      } else {
        // deleting cols from an empty sheet
        body.startIndex = 0;
        body.endIndex = Math.abs(diff);
        request[op] = { range: body };
        requests.unshift(request);
      }
    }
  }

  if (requests.length) {
    const res = await goog(
      'sheets.spreadsheets.batchUpdate',
      {
        path: { spreadsheetId },
        body: { requests },
      },
      { version: 'v4', auth },
    );
    console.log('updated grid', res);
    if (writeRowAdjustment) {
      console.log('adjusting write row by', writeRowAdjustment);
      await updateWriteRow(auth, spreadsheetId, writeRow - writeRowAdjustment);
    }
  }
}

async function ensureHeaders(auth, spreadsheetId, gridInfo) {
  if (gridInfo.newHeaders.length) {
    const range = calculateRowRange(0, gridInfo.effectiveHeaders.length - gridInfo.newHeaders.length, gridInfo.effectiveHeaders.length);
    const valueInputOption = 'RAW';
    const body = { values: [gridInfo.newHeaders] };

    const res = await goog(
      'sheets.spreadsheets.values.update',
      {
        path: { spreadsheetId, range },
        body,
        query: { valueInputOption },
      },
      { version: 'v4', auth },
    );
    console.log(res);
  }
}

function calculateRowRange(rowIndex, startCol, endCol) {
  // 0 indexed, endCol exclusive
  // eg 0, 2, 4 -> C1:D1
  const [c1, c2] = [startCol, endCol - 1].map(colIndexToLetter);
  return `${c1}${rowIndex + 1}:${c2}${rowIndex + 1}`;
}

function colIndexToLetter(colIndex) {
  // adapted from https://github.com/mike182uk/cellref/blob/master/index.js
  let column = colIndex + 1;
  let columnStr = '';

  for (; column; column = Math.floor((column - 1) / 26)) {
    columnStr = String.fromCharCode(((column - 1) % 26) + 65) + columnStr;
  }

  return columnStr;
}

async function appendRows(auth, spreadsheetId, gridInfo, hostMetrics, writeRow) {
  // TODO these could be batched into larger ranges (ala deletion), rather than row-by-row
  // need to handle wraparound in that case though
  const valueRanges = [];
  let rowsWritten = 0;
  console.log('writing', JSON.stringify(hostMetrics, null, 2));
  for (const timestamp in hostMetrics.rows) { // TODO sort these
    const metricRow = hostMetrics.rows[timestamp];
    const values = [];
    for (const header of gridInfo.effectiveHeaders) {
      let val = metricRow[header];
      if (val === null || val === undefined) {
        val = ''; // empty the cell rather than skipping it
      }
      values.push(val);
    }

    let rangeWriteRow = (writeRow + rowsWritten) % gridInfo.numRows;
    if (rangeWriteRow < writeRow + rowsWritten) {
      // skip header row
      // TODO duplicated above
      rangeWriteRow++;
    }
    valueRanges.push(
      {
        range: calculateRowRange(rangeWriteRow, 0, values.length),
        values: [values],
      });

    rowsWritten++;
  }
  const body = {
    data: valueRanges,
  };
  const valueInputOption = 'RAW';

  await goog(
    'sheets.spreadsheets.values.batchUpdate',
    {
      path: { spreadsheetId },
      body,
      query: { valueInputOption },
    },
    { version: 'v4', auth },
  );
  return rowsWritten;
}

module.exports = {
  handleRequest,
};
