import { test as base, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';

export const test = base.extend<{ apiAccount: string }>({
  apiAccount: async ({ context }, use) => {
    if (process.env.LOGOUT_E2E_MODE !== 'api') {
      await use('');
      return;
    }
    if (!process.env.TEST_DATABASE_URL?.includes('animemap_logout_test')) {
      throw new Error('API fixtures require disposable TEST_DATABASE_URL');
    }
    const email = `${randomUUID()}@example.com`;
    const password = 'logout-e2e-only-password';
    try {
      const registration = await context.request.post('/v1/auth/register', {
        data: { email, username: 'logout-e2e', password },
      });
      expect(registration.status()).toBe(201);
      const login = await context.request.post('/v1/auth/login', {
        data: { email, password },
      });
      expect(login.status()).toBe(200);
      await use(email);
    } finally {
      execFileSync('uv', ['run', '--group', 'tests', 'python',
        'tests/integration/database/logout_support.py', 'cleanup-email', email],
      { cwd: '../backend', stdio: 'pipe',
        env: { ...process.env, PYTHONPATH: '.' } });
    }
  },
});
export { expect };

// Tokens may be handled by the test harness, never by application scripts.
export const deletionCookie = {
  name: 'session_token', path: '/', secure: true,
  httpOnly: true, sameSite: 'Lax' as const,
};
