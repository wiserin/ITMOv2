import { test, expect, deletionCookie } from './support/logoutFixtures';

test('real HTTPS proxy preserves secure HttpOnly deletion', async ({ context, page, apiAccount }) => {
  const origin = process.env.PUBLIC_ORIGIN || 'https://localhost:3443';
  if (!apiAccount) {
    await context.addCookies([{ ...deletionCookie, value: 'fixture',
      domain: 'localhost' }]);
  }
  const old = (await context.cookies()).find(c => c.name === 'session_token')!;
  let independent = '';
  if (apiAccount) {
    const login = await context.request.post('/v1/auth/login', {
      data: { email: apiAccount, password: 'logout-e2e-only-password' },
    });
    expect(login.status()).toBe(200);
    independent = (await context.cookies()).find(c => c.name === 'session_token')!.value;
    await context.addCookies([old]);
  }
  await page.goto('/');
  const request = await context.request.post('/v1/auth/logout', {
    headers: { 'X-AnimeMap-Logout': '1' },
  });
  expect(request.status()).toBe(204);
  expect((await request.body()).byteLength).toBe(0);
  const cookie = request.headers()['set-cookie'];
  for (const attr of ['session_token=', 'path=/', 'max-age=0',
    'expires=', 'secure', 'httponly', 'samesite=lax']) {
    expect(cookie.toLowerCase()).toContain(attr);
  }
  expect(cookie.toLowerCase()).not.toContain('domain=');
  expect(await context.cookies(origin)).not.toEqual(
    expect.arrayContaining([expect.objectContaining({ name: 'session_token' })]));
  expect(await page.evaluate(() => ({
    local: { ...localStorage }, session: { ...sessionStorage }, cookie: document.cookie,
  }))).toEqual({ local: {}, session: {}, cookie: '' });
  if (apiAccount) {
    expect((await context.request.get('/v1/account/me', {
      headers: { Cookie: `session_token=${old.value}` },
    })).status()).toBe(401);
    expect((await context.request.get('/v1/account/me', {
      headers: { Cookie: `session_token=${independent}` },
    })).status()).toBe(200);
  }
});

for (const status of [401, 400, 403, 405, 500, 502, 503, 504]) {
  test(`fixture actual ${status} cookie policy`, async ({ context }) => {
    test.skip(process.env.LOGOUT_E2E_MODE === 'api', 'Fixture status matrix');
    await context.request.post('/__fixture/status', { data: { status } });
    await context.addCookies([{ ...deletionCookie, value: 'fixture', domain: 'localhost' }]);
    const response = await context.request.post('/v1/auth/logout', {
      headers: { 'X-AnimeMap-Logout': '1' },
    });
    expect(response.status()).toBe(status);
    expect(response.headers()['cache-control']).toBe('no-store');
    const stored = (await context.cookies()).find(c => c.name === 'session_token');
    if (status === 401) {
      expect(response.headers()['set-cookie']).toContain('Max-Age=0');
      expect(stored).toBeUndefined();
    } else {
      expect(response.headers()['set-cookie']).toBeUndefined();
      expect(stored).toMatchObject({ value: 'fixture', secure: true, httpOnly: true,
        path: '/', sameSite: 'Lax' });
    }
    await context.request.post('/__fixture/status', { data: { status: 204 } });
  });
}
