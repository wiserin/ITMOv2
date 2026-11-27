import http from 'node:http';
import https from 'node:https';
import { readFileSync } from 'node:fs';
import { once } from 'node:events';
import { spawn } from 'node:child_process';
import { createApp } from '../../../server/app.mjs';

// Real servers, not browser API interception. API mode uses API_ORIGIN.
export async function startHarness() {
  const publicOrigin = process.env.PUBLIC_ORIGIN || 'https://localhost:3443';
  const fixture = { status: 204, calls: [], delay: 0 };
  const upstream = http.createServer(async (request, response) => {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    fixture.calls.push({
      url: request.url, headers: request.headers,
      body: Buffer.concat(chunks).toString(),
    });
    if (fixture.delay) await new Promise(r => setTimeout(r, fixture.delay));
    const status = fixture.status;
    const headers = { 'Cache-Control': 'no-store' };
    if (status === 204 || status === 401) {
      headers['Set-Cookie'] = 'session_token=; Path=/; Max-Age=0; ' +
        'Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; HttpOnly; SameSite=Lax';
    }
    response.writeHead(status, headers);
    response.end(status === 204 ? undefined : JSON.stringify({
      error: 'authentication_failed', message: 'Safe', details: {},
    }));
  });
  upstream.listen(0, '127.0.0.1');
  await once(upstream, 'listening');
  const apiOrigin = process.env.LOGOUT_E2E_MODE === 'api'
    ? process.env.API_ORIGIN
    : `http://127.0.0.1:${upstream.address().port}`;
  if (!apiOrigin) throw new Error('API mode requires API_ORIGIN');
  let api;
  if (process.env.LOGOUT_E2E_MODE === 'api' && process.env.LOGOUT_API_TEST_SERVER === '1') {
    const target = new URL(apiOrigin);
    api = spawn('uv', ['run', '--group', 'tests', 'uvicorn',
      'logout_support:create_server_app', '--factory', '--host', target.hostname,
      '--port', target.port, '--log-level', 'error', '--no-access-log'], {
      cwd: '../backend', env: { ...process.env, PYTHONPATH: '.:tests/integration/database' },
      stdio: 'ignore',
    });
    let ready = false;
    for (let i = 0; i < 100; i++) {
      try { ready = (await fetch(`${apiOrigin}/openapi.json`)).ok; }
      catch { /* Startup, bounded readiness polling. */ }
      if (ready) break;
      if (api.exitCode !== null) throw new Error('Test API exited during startup');
      await new Promise(r => setTimeout(r, 100));
    }
    if (!ready) { api.kill('SIGTERM'); throw new Error('Test API readiness timed out'); }
  }
  const app = createApp({ apiOrigin, publicOrigin });
  const server = https.createServer({
    cert: readFileSync(process.env.TLS_CERT),
    key: readFileSync(process.env.TLS_KEY),
  }, async (request, response) => {
    if (process.env.LOGOUT_E2E_MODE !== 'api' &&
        request.url === '/__fixture/status' && request.method === 'POST') {
      let body = '';
      for await (const chunk of request) body += chunk;
      const value = JSON.parse(body);
      fixture.status = value.status;
      fixture.delay = value.delay || 0;
      response.end('{}');
      return;
    }
    await app(request, response);
  });
  server.listen(Number(new URL(publicOrigin).port || 443));
  await once(server, 'listening');
  return { fixture, close: async () => {
    server.closeAllConnections();
    upstream.closeAllConnections();
    await Promise.all([server, upstream].map(s =>
      new Promise(resolve => s.close(resolve))));
    if (api) { api.kill('SIGTERM'); await once(api, 'exit'); }
  } };
}

if (process.argv[1] === new URL(import.meta.url).pathname) {
  const harness = await startHarness();
  process.on('SIGTERM', () => harness.close().then(() => process.exit()));
}
