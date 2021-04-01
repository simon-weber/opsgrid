test-local:
	node server.js & \
	sleep 2 && \
	curl -d '{ "fields": { "bad": false, "other": 0 }, "name": "cpu", "tags": { "host": "curl.test" }, "timestamp": 1458229140 }' -H "Content-Type: application/json" -H "X-Opsgrid-IngestToken: d4bf5570-3026-4269-aca1-597c206b9a40" -X POST http://samus.simon.codes:8001/telegraf; \
	sleep 1 && \
	killall -e node

test-local-ratelimit:
	node server.js & \
	sleep 2 && \
	curl -d '{ "fields": { "bad": false, "other": 0 }, "name": "cpu", "tags": { "host": "test.host" }, "timestamp": 1458229140 }' -H "Content-Type: application/json" -H "X-Opsgrid-IngestToken: d4bf5570-3026-4269-aca1-597c206b9a40" -X POST http://samus.simon.codes:8001/telegraf; \
	curl -d '{ "fields": { "bad": false, "other": 0 }, "name": "cpu", "tags": { "host": "test.host" }, "timestamp": 1458229140 }' -H "Content-Type: application/json" -H "X-Opsgrid-IngestToken: d4bf5570-3026-4269-aca1-597c206b9a40" -X POST http://samus.simon.codes:8001/telegraf; \
	sleep 1 && \
	killall -e node

test-remote:
	curl -d @tgStandard.json -H "Content-Type: application/json" -H "X-Opsgrid-IngestToken: 696a8a70-edbd-4287-8f64-f825b053aad3" -X POST https://ingest.opsgrid.net/telegraf
