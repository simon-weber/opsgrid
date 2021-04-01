require('newrelic');

const Sentry = require('@sentry/node');
const { SENTRY_DSN } = require('./config.js');
Sentry.init({ dsn: SENTRY_DSN });

const fastify = require('fastify')({
  logger: true,
});
const { getAuth, test } = require('./index.js');
const { handleRequest } = require('./lib.js');
const { exchangeToken } = require('./clientlib.js');

fastify.addHook('onError', (request, reply, error, done) => {
  if (process.env.NODE_ENV === 'production') {
    Sentry.withScope(scope => {
      scope.setUser({ ip_address: request.raw.ip, id: request.headers['x-opsgrid-ingesttoken'] });
      scope.setTag('path', request.raw.url);
      scope.setExtra('body', request.body);
      scope.setExtra('headers', request.headers);
      scope.setExtra('query', request.query);
      scope.setExtra('params', request.params);

      Sentry.captureException(error);
    });
  }
  done();
});
fastify.register(require('fastify-graceful-shutdown'));
fastify.setErrorHandler(function (error, request, reply) {
	if (reply.raw && reply.raw.statusCode === 500 && error.explicitInternalServerError !== true) {
		request.log.error(error)
		reply.send(new Error('internal error'))
	} else {
		reply.send(error)
	}
})

fastify.post('/telegraf', async(request, reply) => {
  request.log.info(request.body);
  const ingestToken = request.headers['x-opsgrid-ingesttoken'];
  const auth = await exchangeToken(ingestToken);
  const res = await handleRequest(auth, request.body, ingestToken);
  return res;
});

fastify.get('/health', async(request, reply) => {
  return { status: 'ok' };
});

async function runServer(auth) {
  try {
    await fastify.listen(8001, '0.0.0.0');
  } catch (err) {
    fastify.log.error(err); // disable debug logging
    process.exit(1);
  }
}

const args = process.argv.slice(2);
if (args[0] === '--test') {
  getAuth(test);
} else {
  console.log = () => {};
  runServer();
}
