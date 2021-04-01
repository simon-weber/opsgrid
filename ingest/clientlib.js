const fetch = require('node-fetch');
const { google } = require('googleapis');

const { WEB_BASE, INGEST_CLIENT_SECRET } = require('./config.js');

// TODO cache this locally?
async function exchangeToken(ingestToken) {
  console.info('exchanging', ingestToken);

  const data = {
    ingestToken,
  };
  const response = await fetch(
    `${WEB_BASE}/exchange`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Opsgrid-Ingest-Client-Secret': INGEST_CLIENT_SECRET,
      },
      body: JSON.stringify(data),
    });

  const res = await response.json();
  console.log('exchanged', ingestToken, 'for', res);
  const auth = new google.auth.OAuth2('fake_id', 'fake_secret', 'fake_redirect');
  auth.setCredentials(
    {
      access_token: res.accessToken,
      token_type: 'Bearer',
    });
  return auth;
}

async function reportRows(ingestToken, hostMetrics, spreadsheetId) {
  for (const timestamp in hostMetrics.rows) {
    const data = {
      ingestToken,
      spreadsheetId,
      host: hostMetrics.host,
      metricRow: hostMetrics.rows[timestamp],
    };
    await fetch(
      `${WEB_BASE}/row`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Opsgrid-Ingest-Client-Secret': INGEST_CLIENT_SECRET,
        },
        body: JSON.stringify(data),
      });
  }
}

async function getAlerts(ingestToken) {
  const data = {
    ingestToken,
  };
  const response = await fetch(
    `${WEB_BASE}/alerts`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Opsgrid-Ingest-Client-Secret': INGEST_CLIENT_SECRET,
      },
      body: JSON.stringify(data),
    });

  const res = await response.json();
  return res.alerts;
}

async function changeAlertAlarm(ingestToken, alertId, hostName, status, metricRow, sheetRowStart, sheetRowEnd) {
  const data = {
    ingestToken,
    alertId,
    hostName,
    status,
    metricRow,
    sheetRowStart,
    sheetRowEnd,
  };
  const response = await fetch(
    `${WEB_BASE}/alarm`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Opsgrid-Ingest-Client-Secret': INGEST_CLIENT_SECRET,
      },
      body: JSON.stringify(data),
    });

  return response.json();
}

module.exports = { exchangeToken, reportRows, getAlerts, changeAlertAlarm };
