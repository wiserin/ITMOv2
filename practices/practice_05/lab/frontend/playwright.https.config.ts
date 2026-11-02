import { defineConfig } from '@playwright/test';

if (!process.env.TLS_CERT || !process.env.TLS_KEY) {
  throw new Error('HTTPS tests require TLS_CERT and TLS_KEY');
}
export default defineConfig({
  testDir: './tests/browser',
  testMatch: '**/*.https.spec.ts',
  timeout: 45000,
  use: {
    baseURL: process.env.PUBLIC_ORIGIN || 'https://localhost:3443',
    browserName: 'chromium',
    ignoreHTTPSErrors: false,
    launchOptions: {
      args: process.env.TLS_SPKI
        ? [`--ignore-certificate-errors-spki-list=${process.env.TLS_SPKI}`]
        : [],
    },
    trace: 'off',
  },
  webServer: {
    command: 'node tests/browser/support/logoutHttps.mjs',
    url: `${process.env.PUBLIC_ORIGIN || 'https://localhost:3443'}/health`,
    reuseExistingServer: false,
  },
});
