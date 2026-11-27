import { afterEach, expect, it, vi } from 'vitest';
import { logout } from '../../src/api/logout';

afterEach(() => vi.unstubAllGlobals());

it('sends only same-origin cookie POST without body/query/Authorization', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal('fetch', fetch);
  expect(await logout()).toEqual({ kind: 'closed' });
  const [url, init] = fetch.mock.calls[0];
  expect(url).toBe('/v1/auth/logout');
  expect(init.method).toBe('POST');
  expect(init.credentials).toBe('same-origin');
  expect(init.cache).toBe('no-store');
  expect(init.body).toBeUndefined();
  expect(init.headers).toEqual({ 'X-AnimeMap-Logout': '1' });
});

it.each([200, 201, 202, 403, 500])('does not treat %s as success', async status => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('bad json', { status })));
  expect(await logout()).toEqual({ kind: 'failure', reason: 'other' });
});
