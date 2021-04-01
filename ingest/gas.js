/* eslint-disable */
/* This file is es5-only */

var tgStandard = {
  fields: {
    field_1: 1,
    field_2: 2,
    field_3: 3,
    field_4: 4,
  },
  name: 'docker',
  tags: {
    host: 'gas.host',
  },
  timestamp: 1458229140,
};

function doGet(e) {
  var res = AppLib.handleRequest(null, tgStandard);
  return ContentService.createTextOutput(JSON.stringify(res));
}

function doPost(e) {
  var res = AppLib.handleRequest(null, JSON.parse(e.postData.contents));
  // TODO figure out why curl gets a 302 to a 405 (telegraf doesn't seem to mind)
  return ContentService.createTextOutput(JSON.stringify(res));
}
