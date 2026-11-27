import { test, expect, type Page } from '@playwright/test';

const account = {
  id: '899f2a44-9842-4d1a-b951-03bc78d1e6e9',
  username: 'anime-fan',
  email: 'anime-fan@example.com',
  display_name: 'Anime Fan',
  role: 'user',
  is_active: true,
};

async function mockApi(page: Page, role = 'user', signedIn = true) {
  const calls: { path: string; body: any }[] = [];
  await page.route('**/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const body = request.postDataJSON();
    calls.push({ path, body });
    if (path === '/v1/auth/login') {
      signedIn = true;
      await route.fulfill({ json: {} });
    } else if (path === '/v1/auth/register') {
      await route.fulfill({ status: 201, json: { registered: true } });
    } else if (path === '/v1/account/me') {
      await route.fulfill({
        status: signedIn ? 200 : 401,
        json: signedIn ? { ...account, role } : {},
      });
    } else if (path.includes('/find/')) {
      const empty = path.endsWith('/nobody');
      await route.fulfill({ json: { accounts: empty ? [] : [
        account,
        { ...account, id: 'another-id', email: 'other@example.com' },
      ] } });
    }
  });
  return calls;
}

test('register, then login without automatic authentication', async ({ page }) => {
  const calls = await mockApi(page, 'user', false);
  await page.goto('/#/register');
  await page.getByLabel('Имя пользователя', { exact: true }).fill('fan');
  await page.getByLabel('Email', { exact: true }).fill('FAN@example.com');
  await page.getByLabel('Пароль', { exact: true }).fill('  password  ');
  await page.getByRole('button', { name: 'Создать аккаунт' }).click();
  await expect(page.getByRole('status')).toContainText('Аккаунт создан');
  expect(calls.some(call => call.path.endsWith('/login'))).toBe(false);
  expect(calls.find(call => call.path.endsWith('/register'))?.body)
    .toMatchObject({ email: 'fan@example.com', password: '  password  ' });
  await page.getByLabel('Пароль', { exact: true }).fill('  password  ');
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'AnimeMap.' })).toBeVisible();
});

test('user profile, back navigation and role guard', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'Меню аккаунта' }).hover();
  await expect(page.getByRole('link', { name: 'Admin Panel' })).toHaveCount(0);
  await page.getByRole('link', { name: 'Аккаунт', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Мой аккаунт' })).toBeVisible();
  await expect(page.locator('dd').filter({ hasText: account.email })).toBeVisible();
  await page.getByRole('link', { name: 'На главную' }).click();
  await expect(page.getByRole('heading', { name: 'AnimeMap.' })).toBeVisible();
  await page.goto('/#/admin');
  await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible();
});

for (const role of ['moderator', 'admin']) {
  test(`${role}: live search and accessible account dialog`, async ({ page }) => {
    const calls = await mockApi(page, role);
    await page.goto('/');
    await page.getByRole('button', { name: 'Меню аккаунта' }).hover();
    await page.getByRole('link', { name: 'Admin Panel' }).click();
    const search = page.getByLabel('Имя пользователя', { exact: true });
    await search.fill('ani');
    await expect(page.locator('.user-row')).toHaveCount(2);
    expect(calls.filter(call => call.path.includes('/find/'))).toHaveLength(1);
    await page.locator('.user-row').first().click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(account.email);
    await expect(dialog).toContainText(account.id);
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(page.locator('.user-row').first()).toBeFocused();
    await search.fill('nobody');
    await expect(page.getByRole('heading', { name: 'Пользователи не найдены' }))
      .toBeVisible();
    await page.getByRole('button', { name: 'Очистить поиск' }).click();
    await expect(page.getByRole('heading', { name: 'Кого будем искать?' }))
      .toBeVisible();
  });
}

test('expired session returns to login', async ({ page }) => {
  await mockApi(page, 'admin');
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'AnimeMap.' })).toBeVisible();
  await page.route('**/v1/account/find/**', route =>
    route.fulfill({ status: 401, json: {} }));
  await page.goto('/#/admin');
  await page.getByLabel('Имя пользователя', { exact: true }).fill('ani');
  await expect(page.getByRole('heading', { name: 'С возвращением' })).toBeVisible();
});

test('mobile navigation and logout placeholder', async ({ browser }) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
  });
  const page = await context.newPage();
  await mockApi(page, 'admin');
  await page.goto('http://127.0.0.1:3100/');
  await page.getByRole('button', { name: 'Меню аккаунта' }).tap();
  await page.getByRole('button', { name: 'Выйти' }).click();
  await expect(page.getByRole('status')).toContainText('сессия остаётся активной');
  expect(await page.evaluate(() =>
    document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await context.close();
});

test('service failure is displayed instead of empty search', async ({ page }) => {
  await mockApi(page, 'admin');
  await page.route('**/v1/account/find/**', route =>
    route.fulfill({ status: 503, json: {} }));
  await page.goto('/#/admin');
  await page.getByLabel('Имя пользователя', { exact: true }).fill('ani');
  await expect(page.getByRole('alert')).toContainText('временно недоступен');
  await expect(page.getByRole('heading', { name: 'Пользователи не найдены' }))
    .toHaveCount(0);
});
