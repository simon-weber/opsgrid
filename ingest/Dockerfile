FROM node:12-stretch-slim

WORKDIR /app
EXPOSE 8001
ENV OPSGRID_WEB_BASE=https://www.opsgrid.net/ingest
ENV NODE_ENV=production

COPY package*.json ./
RUN apt-get update \
  && apt-get install -y python3 build-essential \
  && npm ci --only=production \
  && apt-get purge --auto-remove -y python3 build-essential \
  && rm -rf /var/lib/apt/lists/*

ADD docker-archive.tar ./

RUN groupadd --gid 502 opsgrid-ingest \
  && useradd --uid 503 --gid opsgrid-ingest --shell /bin/bash --create-home opsgrid-ingest
USER opsgrid-ingest:opsgrid-ingest

# using cmd doesn't send signals due to something weird in the node entry point
ENTRYPOINT ["node", "server.js" ]
