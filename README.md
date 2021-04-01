# Opsgrid

Opsgrid was a simple hosted server monitoring service that stored data in users' Google Sheets.
The [old homepage](https://web.archive.org/web/20210119181448/https://www.opsgrid.net/) has more information.

It worked reasonably well, but I didn't want to maintain it after moving to a more sophisticated setup.

This repo has the code as-is, including infra/deployment tooling.
The only exception is secrets, which used to be encrypted and checked in using transcrypt; they're just stubbed out in this repo.

## Technical Overview

There's two pieces to Opsgrid:
* ingest: a node app that receives telegraf metric requests and posts them to Google Sheets
* web: a django app that handles user management

Here's the end-to-end flow when metrics are received:
* ingest receives a telegraf request in json format
* ingest exchanges the ingest token with web for a Google OAuth access token
* for each host, ingest:
  * ensures a sheet for each host in the request exists and is formatted to receive metric rows
  * writes metrics to the row number stored in Google Sheets metadata
  * requests alert config from web and reports back any status changes (which web will notify the user about)
  * reports sheet metadata to web for presentation

It ran on one nixos host.

## Curiosities

### Google Apps Script Support

I originally intended to support a free tier that was hosted entirely on Google Apps Script.
In this mode, ingest code would run as an [Apps Script Web App](https://developers.google.com/apps-script/guides/web) and communicate with a preconfigured sheet instead of interacting with the backend.

There were a few challenges in getting this working:
* Apps Script ran under Rhino and only supported ES5
* the Apps Script Google Sheets client library had a different interface from the one on NPM, and was synchronous

The webpack config in ingest/webpack.gas.js handled this by:
* removing await/async keywords for the synchronous client library
* swapping node export syntax for ES6 syntax
* then, transpiling code for ES5 support

Then, the ES5-only entry point in ingest/gas.js could be used as a Web App handler.
It all worked, but I ended up abandoning it due to limitations in Web App distribution.
