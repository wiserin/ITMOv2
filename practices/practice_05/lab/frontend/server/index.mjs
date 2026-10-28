import http from 'node:http';
import https from 'node:https';
import { readFileSync } from 'node:fs';
import { createApp } from './app.mjs';

const port = Number(process.env.PORT || 3000);
const apiOrigin = process.env.API_ORIGIN || 'http://localhost:8080';
const app = createApp({ apiOrigin });
const cert = process.env.TLS_CERT;
const key = process.env.TLS_KEY;
if (Boolean(cert) !== Boolean(key)) {
  throw new Error('Set both TLS_CERT and TLS_KEY');
}
const server = cert
  ? https.createServer({
    cert: readFileSync(cert), key: readFileSync(key),
  }, app)
  : http.createServer(app);

server.requestTimeout = 30000;
server.listen(port, '0.0.0.0', () => {
  console.log(`AnimeMap: ${cert ? 'https' : 'http'}://localhost:${port}`);
  console.log(`API upstream: ${new URL(apiOrigin).origin}`);
});
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(1), 10000).unref();
  });
}
