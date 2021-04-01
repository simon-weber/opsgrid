const jsonLogic = require('json-logic-js');

const clientlib = require('./clientlib.js');

const OK = 'OK';
const ALARM = 'ALARM';
const UNKNOWN = 'UNKNOWN';

function checkAlarmStatus(alertJsonLogic, metricsRow) {
  const alertVars = jsonLogic.uses_data(alertJsonLogic);
  for (const alertVar of alertVars) {
    if (!(alertVar in metricsRow)) {
      return UNKNOWN;
    }
  }

  if (jsonLogic.apply(alertJsonLogic, metricsRow)) {
    return ALARM;
  } else {
    return OK;
  }
}

async function processAlerts(ingestToken, hostMetrics, alerts, sheetRowStart, sheetRowEnd) {
  for (const timestamp in hostMetrics.rows) {
    for (const alert of alerts) {
      if (alert.hostName && alert.hostName !== hostMetrics.host) {
        continue;
      }

      const metricRow = hostMetrics.rows[timestamp];
      const currentStatus = checkAlarmStatus(alert.jsonlogic, metricRow);
      const isAlarming = alert.alarmHosts.includes(hostMetrics.host);
      if (currentStatus === UNKNOWN) {
        console.warn('unknown alert status', alert, metricRow);
      } else if (currentStatus === OK && isAlarming) {
        console.warn('now ok', hostMetrics.host, alert, metricRow);
        await clientlib.changeAlertAlarm(ingestToken, alert.id, hostMetrics.host, currentStatus, metricRow, sheetRowStart, sheetRowEnd);
      } else if (currentStatus === ALARM && !isAlarming) {
        console.warn('now alarming', hostMetrics.host, alert, metricRow);
        await clientlib.changeAlertAlarm(ingestToken, alert.id, hostMetrics.host, currentStatus, metricRow, sheetRowStart, sheetRowEnd);
      }
    }
  }
}

module.exports = { processAlerts };
