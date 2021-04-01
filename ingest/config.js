const fs = require('fs');

const WEB_BASE = process.env.OPSGRID_WEB_BASE || 'http://127.0.0.1:8000/ingest';
const INGEST_CLIENT_SECRET = fs.readFileSync('./secrets/ingest_client_secret.txt', 'utf8').trim();
const SENTRY_DSN = fs.readFileSync('./secrets/sentry.dsn', 'utf8').trim();
const GA_TRACKING_ID = 'UA-169365761-2';

module.exports = { WEB_BASE, INGEST_CLIENT_SECRET, SENTRY_DSN, GA_TRACKING_ID };
