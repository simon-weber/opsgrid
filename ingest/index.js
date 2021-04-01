const fs = require('fs');
const readline = require('readline');
const { google } = require('googleapis');

const { handleRequest } = require('./lib.js');

// If modifying these scopes, delete token.json.
const SCOPES = ['https://www.googleapis.com/auth/drive.file'];
// The file token.json stores the user's access and refresh tokens, and is
// created automatically when the authorization flow completes for the first
// time.
const TOKEN_PATH = './secrets/token.json';
const CREDENTIALS_PATH = './secrets/credentials.json';

process.on('unhandledRejection', (e, p) => {
  console.error('Unhandled Rejection at: Promise', p, 'e:', e);
  console.error(e.stack);
});

/**
 * Create an OAuth2 client with the given credentials, and then execute the
 * given callback function.
 * @param {Object} credentials The authorization client credentials.
 * @param {function} callback The callback to call with the authorized client.
 */
function authorize(credentials, callback) {
  const { client_secret, client_id, redirect_uris } = credentials.installed; // eslint-disable-line camelcase
  const oAuth2Client = new google.auth.OAuth2(
    client_id, client_secret, redirect_uris[0]);

  // Check if we have previously stored a token.
  fs.readFile(TOKEN_PATH, (err, token) => {
    if (err) return getNewToken(oAuth2Client, callback);
    oAuth2Client.setCredentials(JSON.parse(token));
    callback(oAuth2Client);
  });
}

function getAuth(callback) {
  // Load client secrets from a local file.
  fs.readFile(CREDENTIALS_PATH, (err, content) => {
    if (err) return console.error('Error loading client secret file:', err);
    authorize(JSON.parse(content), callback);
  });
}

/**
 * Get and store new token after prompting for user authorization, and then
 * execute the given callback with the authorized OAuth2 client.
 * @param {google.auth.OAuth2} oAuth2Client The OAuth2 client to get token for.
 * @param {getEventsCallback} callback The callback for the authorized client.
 */
function getNewToken(oAuth2Client, callback) {
  const authUrl = oAuth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
  });
  console.info('Authorize this app by visiting this url:', authUrl);
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  rl.question('Enter the code from that page here: ', (code) => {
    rl.close();
    oAuth2Client.getToken(code, (err, token) => {
      if (err) return console.error('Error while trying to retrieve access token', err);
      oAuth2Client.setCredentials(token);
      // Store the token to disk for later program executions
      fs.writeFile(TOKEN_PATH, JSON.stringify(token), (err) => {
        if (err) return console.error(err);
        console.info('Token stored to', TOKEN_PATH);
      });
      callback(oAuth2Client);
    });
  });
}

const tgStandard = {
  fields: {
    field_1: 1,
    field_2: 2,
    field_3: 3,
    field_4: 4,
  },
  name: 'docker',
  tags: {
    host: 'node.host',
  },
  timestamp: 1458229140,
};

// eslint-disable-next-line no-unused-vars
const tgBatch = {
  metrics: [
    {
      fields: {
        field_1: 1,
        field_2: 2,
      },
      name: 'docker',
      tags: {
        host: 'batch.host',
      },
      timestamp: 1,
    },
    {
      fields: {
        field_1: 3,
        field_2: 4,
        field_3: 5,
      },
      name: 'docker',
      tags: {
        host: 'batch.host',
      },
      timestamp: 2,
    },
  ],
};

// from my local config
// eslint-disable-next-line no-unused-vars
const tgSample = { metrics: [{ fields: { uptime: 189564 }, name: 'system', tags: { host: 'pixel_docker_test' }, timestamp: 1578269880 }, { fields: { inodes_free: 1302020, used_percent: 89.20879096331755 }, name: 'disk', tags: { host: 'pixel_docker_test', path: '/' }, timestamp: 1578269880 }, { fields: { bytes_recv: 2744, bytes_sent: 0 }, name: 'net', tags: { host: 'pixel_docker_test', interface: 'eth0' }, timestamp: 1578269880 }, { fields: { iops_in_progress: 0, weighted_io_time: 1874034 }, name: 'diskio', tags: { host: 'pixel_docker_test', name: 'sda' }, timestamp: 1578269880 }, { fields: { used: 0, used_percent: 0 }, name: 'swap', tags: { host: 'pixel_docker_test' }, timestamp: 1578269880 }, { fields: { write_time_ns: 0 }, name: 'internal_write', tags: { host: 'pixel_docker_test' }, timestamp: 1578269880 }, { fields: { buffer_size: 0, metrics_dropped: 0 }, name: 'internal_write', tags: { host: 'pixel_docker_test' }, timestamp: 1578269880 }, { fields: { available_percent: 93.6718157318721 }, name: 'mem', tags: { host: 'pixel_docker_test' }, timestamp: 1578269880 }] };

function test(auth) {
  handleRequest(auth, tgStandard);
}

module.exports = { getAuth, test };
