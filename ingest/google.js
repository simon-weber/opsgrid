const { google } = require('googleapis'); // webpack-omit
const { isNode } = require('./compat.js');

function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
}

// see https://developers.google.com/apps-script/guides/services/advanced#how_method_signatures_are_determined
async function goog(path, args, initArg) {
  // args: {body, path, query}
  console.log('goog', JSON.stringify({ path, args }));
  if (isNode()) {
    // node
    const serviceName = path.split('.')[0]; // drive
    const serviceFunc = google[serviceName]; // google.drive
    const service = serviceFunc(initArg); // google.drive({...})
    let action = service;
    for (const part of path.split('.').slice(1)) {
      console.log('part', part);
      action = action[part];
    }
    console.log('action', action);
    const unifiedArgs = {};
    if (args.body !== undefined) Object.assign(unifiedArgs, { resource: args.body });
    if (args.path !== undefined) Object.assign(unifiedArgs, args.path);
    if (args.query !== undefined) Object.assign(unifiedArgs, args.query);
    console.log('unifiedArgs', JSON.stringify(unifiedArgs));
    const res = await action.bind(service)(unifiedArgs);
    console.log('result', res);
    return res.data;
  } else {
    const [, prefix, actionName] = path.match(/(.*)\.(.*)/); // drive.files, list
    const pathParts = prefix.split('.').map(capitalizeFirstLetter);
    pathParts.push(actionName); // ['Drive', 'Files', 'list']
    const global = Function('return this')(); // eslint-disable-line no-new-func
    const service = global[pathParts[0]];
    let action = service;
    for (const part of pathParts.slice(1)) {
      action = action[part];
    }
    console.log('action', action);
    const argList = [];
    if (args.body !== undefined) argList.push(args.body);
    if (args.path !== undefined) argList.push(...Object.values(args.path));
    // see note on drive.files.insert
    // if (actionName === 'insert') argList.push(Utilities.newBlob("").setContentType(args.body.mimeType))
    if (args.query !== undefined) argList.push(args.query);
    console.log('argList', JSON.stringify(argList));
    const res = action.bind(service)(...argList);
    console.log('result', res);
    return res;
  }
}

module.exports = {
  goog,
};
