const routes = [
  ['POST', /^\/v1\/auth\/(login|register)$/],
  ['GET', /^\/v1\/account\/me$/],
  ['GET', /^\/v1\/account\/find\/[^/]+$/],
];

export function json(response, status, data) {
  response.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  });
  response.end(JSON.stringify(data));
}

export async function proxy(request, response, url, apiOrigin, options = {}) {
  if (url.pathname === '/v1/auth/logout') {
    await logoutProxy(request, response, url, apiOrigin, options);
    return;
  }
  if (!routes.some(([method, pattern]) =>
    request.method === method && pattern.test(url.pathname))) {
    json(response, 404, { message: 'Ручка не найдена.' });
    return;
  }

  // The browser's Origin must match the public host for mutations.
  if (request.method === 'POST' && request.headers.origin) {
    let originHost;
    try { originHost = new URL(request.headers.origin).host; }
    catch { originHost = ''; }
    if (originHost !== request.headers.host) {
      json(response, 403, { message: 'Недопустимый origin.' });
      return;
    }
  }

  try {
    const chunks = [];
    let size = 0;
    for await (const chunk of request) {
      size += chunk.length;
      if (size > 16384) {
        json(response, 413, { message: 'Запрос слишком большой.' });
        return;
      }
      chunks.push(chunk);
    }
    const headers = { Accept: 'application/json' };
    if (request.headers.cookie) headers.Cookie = request.headers.cookie;
    if (request.method === 'POST') {
      headers['Content-Type'] = 'application/json';
    }
    const upstream = await fetch(
      new URL(url.pathname + url.search, apiOrigin),
      {
        method: request.method,
        headers,
        body: request.method === 'POST'
          ? Buffer.concat(chunks) : undefined,
        redirect: 'manual',
        signal: AbortSignal.timeout(15000),
      },
    );
    // A browser cannot inspect manual redirect responses reliably.
    // Consume the documented success redirect here, never GET login.
    if (url.pathname === '/v1/auth/register' &&
        upstream.status === 303) {
      await upstream.body?.cancel();
      json(response, 201, { registered: true });
      return;
    }
    if (upstream.status >= 300 && upstream.status < 400) {
      await upstream.body?.cancel();
      json(response, 502, { message: 'Неожиданный редирект API.' });
      return;
    }
    const outgoing = {
      'Content-Type': upstream.headers.get('content-type') ||
        'application/json',
      'Cache-Control': 'no-store',
    };
    const cookies = upstream.headers.getSetCookie();
    if (cookies.length) outgoing['Set-Cookie'] = cookies;
    const body = Buffer.from(await upstream.arrayBuffer());
    response.writeHead(upstream.status, outgoing);
    response.end(body);
  } catch (error) {
    // Do not log request bodies, cookies or session secrets.
    console.error('[API proxy]', {
      method: request.method,
      upstream: new URL(apiOrigin).origin,
      code: error.cause?.code || error.code || error.name,
    });
    json(response, error.name === 'TimeoutError' ? 504 : 502, {
      message: 'Не удалось связаться с API.',
    });
  }
}

function error(request, response, status, reason, allow) {
  request.resume();
  const codes = { 400: 'bad_request', 403: 'access_denied',
    405: 'method_not_allowed', 502: 'service_unavailable', 504: 'service_unavailable' };
  response.writeHead(status, { 'Cache-Control': 'no-store',
    'Content-Type': 'application/json; charset=utf-8', ...(allow ? { Allow: 'POST' } : {}) });
  response.end(request.method === 'HEAD' ? undefined : JSON.stringify({
    error: codes[status], message: 'Logout request failed', details: { reason },
  }));
}

function origin(value) {
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol) || url.username ||
        url.password || url.pathname !== '/' || url.search || url.hash) return null;
    return url.origin;
  } catch { return null; }
}

function nonemptyBody(request) {
  return new Promise((resolve, reject) => {
    const clean = () => {
      request.off('data', data); request.off('end', end); request.off('error', fail);
    };
    const data = chunk => {
      if (!chunk.length) return;
      clean(); request.resume(); resolve(true);
    };
    const end = () => { clean(); resolve(false); };
    const fail = err => { clean(); reject(err); };
    request.on('data', data); request.once('end', end); request.once('error', fail);
  });
}

async function logoutProxy(request, response, url, apiOrigin,
  { publicOrigin, logoutClock = { setTimeout, clearTimeout } }) {
  if (request.method !== 'POST') {
    error(request, response, 405, 'unsupported_method', true);
    return;
  }
  if (request.headers.origin !== undefined &&
      (!origin(request.headers.origin) || origin(request.headers.origin) !== origin(publicOrigin))) {
    error(request, response, 403, 'origin_check_failed');
    return;
  }
  const values = [];
  for (let i = 0; i < request.rawHeaders.length; i += 2) {
    if (request.rawHeaders[i].toLowerCase() === 'x-animemap-logout') {
      values.push(request.rawHeaders[i + 1]);
    }
  }
  if (values.length !== 1 || values[0] !== '1') {
    error(request, response, 403, 'csrf_check_failed');
    return;
  }
  if (url.search || await nonemptyBody(request)) {
    error(request, response, 400, 'invalid_input');
    return;
  }
  const controller = new AbortController();
  let timedOut = false;
  const timer = logoutClock.setTimeout(() => {
    timedOut = true; controller.abort();
  }, 15000);
  try {
    const headers = { Accept: 'application/json', 'X-AnimeMap-Logout': values[0] };
    if (request.headers.cookie !== undefined) headers.Cookie = request.headers.cookie;
    if (request.headers['content-type']) headers['Content-Type'] = request.headers['content-type'];
    const upstream = await fetch(new URL('/v1/auth/logout', apiOrigin), {
      method: 'POST', headers, redirect: 'manual', signal: controller.signal,
    });
    if (upstream.status >= 300 && upstream.status < 400) {
      await upstream.body?.cancel();
      error(request, response, 502, 'upstream_failure');
      return;
    }
    const body = Buffer.from(await upstream.arrayBuffer());
    if (timedOut) throw new Error('Deadline exceeded');
    const outgoing = {};
    for (const name of ['content-type', 'cache-control', 'allow']) {
      if (upstream.headers.has(name)) outgoing[name] = upstream.headers.get(name);
    }
    outgoing['cache-control'] ??= 'no-store';
    const cookies = upstream.headers.getSetCookie();
    if (cookies.length) outgoing['set-cookie'] = cookies;
    response.writeHead(upstream.status, outgoing);
    response.end(upstream.status === 204 ? undefined : body);
  } catch {
    if (!response.destroyed && !response.headersSent) {
      error(request, response, timedOut ? 504 : 502,
        timedOut ? 'upstream_timeout' : 'upstream_failure');
    }
  } finally {
    logoutClock.clearTimeout(timer);
  }
}
