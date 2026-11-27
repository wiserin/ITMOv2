import { readFile, stat } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { proxy, json } from './proxy.mjs';

const defaultRoot = fileURLToPath(new URL('../dist/', import.meta.url));
const mime = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

export function createApp({
  apiOrigin = 'http://localhost:8080',
  root = defaultRoot,
} = {}) {
  const target = new URL(apiOrigin);
  if (!['http:', 'https:'].includes(target.protocol)) {
    throw new Error('API_ORIGIN must use HTTP or HTTPS');
  }
  return async (request, response) => {
    response.setHeader('X-Content-Type-Options', 'nosniff');
    response.setHeader('Referrer-Policy', 'same-origin');
    let url;
    try {
      // Keep paths on the configured upstream, including // prefixes.
      url = new URL(request.url, 'http://frontend.local');
      if (url.origin !== 'http://frontend.local') throw new Error();
    } catch {
      json(response, 400, { message: 'Некорректный URL.' });
      return;
    }
    if (url.pathname.startsWith('/v1/')) {
      await proxy(request, response, url, target.origin);
      return;
    }
    if (url.pathname === '/health') {
      json(response, 200, { status: 'ok' });
      return;
    }
    if (!['GET', 'HEAD'].includes(request.method)) {
      json(response, 405, { message: 'Метод не поддерживается.' });
      return;
    }
    try {
      const path = decodeURIComponent(url.pathname);
      let file = resolve(root, `.${path}`);
      if (file !== resolve(root) &&
          !file.startsWith(resolve(root) + sep)) {
        json(response, 404, { message: 'Файл не найден.' });
        return;
      }
      if (!extname(path)) file = resolve(root, 'index.html');
      const info = await stat(file);
      if (!info.isFile()) throw new Error('Not a file');
      const body = await readFile(file);
      response.writeHead(200, {
        'Content-Type': mime[extname(file)] ||
          'application/octet-stream',
        'Cache-Control': url.pathname.startsWith('/assets/')
          ? 'public, max-age=31536000, immutable' : 'no-cache',
      });
      response.end(request.method === 'HEAD' ? undefined : body);
    } catch {
      json(response, 404, { message: 'Файл не найден.' });
    }
  };
}
