import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { once } from 'node:events';
import { createApp } from '../server/app.mjs';

async function listen(handler) {
  const server = http.createServer(handler);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return {
    origin: `http://127.0.0.1:${server.address().port}`,
    close: () => new Promise(resolve => server.close(resolve)),
  };
}

test('Node server and documented API contracts', async t => {
  const calls = [];
  const upstream = await listen(async (request, response) => {
    let body = '';
    for await (const chunk of request) body += chunk;
    calls.push({
      url: request.url,
      method: request.method,
      cookie: request.headers.cookie,
      body,
    });
    if (request.url === '/v1/auth/register') {
      response.writeHead(303, { Location: '/v1/auth/login' });
      response.end();
    } else if (request.url === '/v1/auth/login') {
      response.writeHead(200, {
        'Set-Cookie': 'session_token=jwt; HttpOnly; Secure; ' +
          'SameSite=Lax; Path=/',
      });
      response.end('{}');
    } else if (request.url.includes('/find/denied')) {
      response.writeHead(403, {
        'Content-Type': 'application/json',
      });
      response.end(JSON.stringify({ error: 'access_denied' }));
    } else {
      response.writeHead(200);
      response.end('{"accounts":[]}');
    }
  });
  const frontend = await listen(createApp({ apiOrigin: upstream.origin }));
  t.after(async () => {
    await frontend.close();
    await upstream.close();
  });
  const fetchApp = (path, init) => fetch(frontend.origin + path, init);

  await t.test('303 becomes 201 without following redirect', async () => {
    const count = calls.length;
    const response = await fetchApp('/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email: 'fan@example.com' }),
    });
    assert.equal(response.status, 201);
    assert.deepEqual(await response.json(), { registered: true });
    assert.equal(calls.length, count + 1);
    assert.equal(calls.at(-1).method, 'POST');
  });

  await t.test('login preserves cookie flags and password spaces', async () => {
    const response = await fetchApp('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password: '  secret  ' }),
    });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('set-cookie'),
      'session_token=jwt; HttpOnly; Secure; SameSite=Lax; Path=/');
    assert.equal(JSON.parse(calls.at(-1).body).password, '  secret  ');
    assert.equal(response.headers.get('cache-control'), 'no-store');
  });

  await t.test('search forwards encoded prefix, page and cookie', async () => {
    await fetchApp('/v1/account/find/ani%25_?limit=20&offset=40', {
      headers: { Cookie: 'session_token=jwt' },
    });
    assert.equal(calls.at(-1).url,
      '/v1/account/find/ani%25_?limit=20&offset=40');
    assert.equal(calls.at(-1).cookie, 'session_token=jwt');
  });

  await t.test('403 is not masked as empty results', async () => {
    const response = await fetchApp('/v1/account/find/denied');
    assert.equal(response.status, 403);
    assert.deepEqual(await response.json(), { error: 'access_denied' });
  });

  await t.test('blocks cross-origin mutations and unknown routes', async () => {
    const count = calls.length;
    const response = await fetchApp('/v1/auth/login', {
      method: 'POST', headers: { Origin: 'https://other.example' },
    });
    assert.equal(response.status, 403);
    assert.equal((await fetchApp('/v1/other')).status, 404);
    assert.equal(calls.length, count);
  });

  await t.test('serves built SPA, assets and health', async () => {
    const response = await fetchApp('/');
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.match(html, /<html lang="ru">/);
    const asset = html.match(/src="([^"]+\.js)"/)[1];
    const script = await fetchApp(asset);
    assert.match(script.headers.get('content-type'), /javascript/);
    assert.match(script.headers.get('cache-control'), /immutable/);
    assert.equal((await fetchApp('/missing.js')).status, 404);
    assert.equal((await fetchApp('/health')).status, 200);
    assert.equal((await fetchApp('/%2e%2e%2fpackage.json')).status, 404);
  });
});

test('unavailable API gives 502', async t => {
  const dead = await listen(() => {});
  await dead.close();
  const frontend = await listen(createApp({ apiOrigin: dead.origin }));
  t.after(frontend.close);
  const response = await fetch(frontend.origin + '/v1/account/me');
  assert.equal(response.status, 502);
});

test('Logout public boundary preserves strict contract', async t => {
  const calls = [];
  let status = 204;
  const upstream = await listen(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    calls.push({ headers: req.headers, body, url: req.url });
    const headers = { 'Cache-Control': 'no-store', Allow: 'POST' };
    if ([204, 401].includes(status)) {
      headers['Set-Cookie'] = 'session_token=; Max-Age=0; Path=/; ' +
        'Secure; HttpOnly; SameSite=Lax';
    }
    res.writeHead(status, headers);
    res.end(status === 204 ? undefined : '{}');
  });
  const frontend = await listen(createApp({
    apiOrigin: upstream.origin, publicOrigin: 'https://animemap.test',
  }));
  t.after(async () => { await frontend.close(); await upstream.close(); });
  const raw = (method, path = '/v1/auth/logout', headers = {}, body = '') =>
    new Promise((resolve, reject) => {
      const req = http.request(frontend.origin + path, { method, headers }, res => {
        let text = '';
        res.on('data', chunk => { text += chunk; });
        res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, text }));
      });
      req.on('error', reject);
      req.end(body);
    });
  const csrf = { 'X-AnimeMap-Logout': '1' };
  for (const method of ['GET', 'HEAD', 'OPTIONS', 'PUT', 'DELETE']) {
    const response = await raw(method);
    assert.equal(response.status, 405);
    assert.equal(response.headers.allow, 'POST');
    assert.equal(response.headers['cache-control'], 'no-store');
    assert.equal(response.headers['set-cookie'], undefined);
    assert.equal(response.headers['access-control-allow-credentials'], undefined);
    if (method === 'HEAD') assert.equal(response.text, '');
    else assert.equal(JSON.parse(response.text).error, 'method_not_allowed');
  }
  for (const origin of ['null', 'broken', 'http://animemap.test',
    'https://other.test', 'https://animemap.test:444']) {
    const response = await raw('POST', undefined, { ...csrf, Origin: origin });
    assert.equal(response.status, 403);
    assert.equal(JSON.parse(response.text).details.reason, 'origin_check_failed');
  }
  for (const header of [undefined, '0', ['1', '1'], ['1', '0']]) {
    const headers = { 'Content-Length': '2', Cookie: 'bad=credential' };
    if (header !== undefined) headers['X-AnimeMap-Logout'] = header;
    const response = await raw('POST', '/v1/auth/logout?x=', headers, '{}');
    assert.equal(response.status, 403);
    assert.equal(JSON.parse(response.text).details.reason, 'csrf_check_failed');
  }
  for (const body of ['{}', 'null', ' ', '{bad', 'x'.repeat(17000)]) {
    const response = await raw('POST', undefined,
      { ...csrf, 'Content-Length': String(Buffer.byteLength(body)) }, body);
    assert.equal(response.status, 400);
    assert.equal(response.headers['set-cookie'], undefined);
  }
  assert.equal((await raw('POST', '/v1/auth/logout?x=', csrf)).status, 400);
  assert.equal(calls.length, 0);
  for (const code of [204, 401, 400, 503, 405]) {
    status = code;
    const response = await raw('POST', undefined, { ...csrf,
      Origin: 'https://animemap.test:443', Cookie: 'session_token=original',
      'Content-Type': 'application/json', 'X-Forwarded-Proto': 'http',
    });
    assert.equal(response.status, code);
    assert.equal(response.headers.allow, 'POST');
    assert.equal(response.headers['cache-control'], 'no-store');
    assert.equal(calls.at(-1).headers.cookie, 'session_token=original');
    assert.equal(calls.at(-1).headers['x-animemap-logout'], '1');
    assert.equal(calls.at(-1).body, '');
    if (code === 204) assert.equal(response.text, '');
  }
});
