FROM python:3.7.9-slim-stretch

WORKDIR /app
EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=opsgrid.settings
ENV NEW_RELIC_CONFIG_FILE=newrelic.ini

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ADD docker-archive.tar ./
COPY pack-dist/ ./pack-dist

RUN groupadd --gid 501 opsgrid-web \
  && useradd --uid 500 --gid opsgrid-web --shell /bin/bash --create-home opsgrid-web
USER opsgrid-web:opsgrid-web

CMD ["newrelic-admin", "run-program", "gunicorn", "--worker-class", "gevent", "opsgrid.wsgi", "-b", "0.0.0.0:8000"]
