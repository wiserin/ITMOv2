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

export async function proxy(request, response, url, apiOrigin) {
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
