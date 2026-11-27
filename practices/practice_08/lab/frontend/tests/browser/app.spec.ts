import { expectTokenContrast } from './contrast';
import { test, expect, type Page } from '@playwright/test';

test.beforeEach(async ({ page }) => {
    await page.route('https://fonts.googleapis.com/**', route =>
        route.fulfill({ contentType: 'text/css', body: '' }));
});

const account = {
    id: '899f2a44-9842-4d1a-b951-03bc78d1e6e9',
    username: 'anime-fan',
    email: 'anime-fan@example.com',
    display_name: 'Anime Fan',
    role: 'user',
    is_active: true,
};

async function mockApi(page: Page, role = 'user', signedIn = true) {
    const calls: { path: string; body: unknown }[] = [];
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
        await expect(page.locator('.am-user-row')).toHaveCount(2);
        expect(calls.filter(call => call.path.includes('/find/'))).toHaveLength(1);
        await page.locator('.am-user-row').first().click();
        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible();
        await expect(dialog).toContainText(account.email);
        await expect(dialog).toContainText(account.id);
        await page.keyboard.press('Escape');
        await expect(dialog).toHaveCount(0);
        await expect(page.locator('.am-user-row').first()).toBeFocused();
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
    await context.route('https://fonts.googleapis.com/**', route =>
        route.fulfill({ contentType: 'text/css', body: '' }));
    const page = await context.newPage();
    await mockApi(page, 'admin');
    await page.goto('http://127.0.0.1:3100/');
    const trigger = page.getByRole('button', { name: 'Меню аккаунта' });
    await trigger.tap();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
    await trigger.tap();
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
    await trigger.tap();
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

test('pagination and clearing search reset the offset', async ({ page }) => {
    await mockApi(page, 'admin');
    const offsets: number[] = [];
    await page.route('**/v1/account/find/**', async route => {
        const url = new URL(route.request().url());
        const offset = Number(url.searchParams.get('offset'));
        offsets.push(offset);
        const accounts = Array.from({ length: offset ? 1 : 20 },
            (_, index) => ({ ...account, id: `account-${offset + index}` }));
        await route.fulfill({ json: { accounts } });
    });
    await page.goto('/#/admin');
    const search = page.getByLabel('Имя пользователя', { exact: true });
    await search.fill('ani');
    await expect(page.locator('.am-user-row')).toHaveCount(20);
    await expect(page.getByRole('button', { name: 'Назад' }))
        .toBeDisabled();
    await page.getByRole('button', { name: 'Далее' }).click();
    await expect(page.locator('.am-user-row')).toHaveCount(1);
    await expect(page.getByText('Страница 2', { exact: true }))
        .toBeVisible();
    await expect(page.getByRole('button', { name: 'Далее' }))
        .toBeDisabled();
    await page.getByRole('button', { name: 'Очистить поиск' }).click();
    await expect(page.locator('.ui-pagination')).toHaveCount(0);
    await search.fill('ani');
    await expect(page.locator('.am-user-row')).toHaveCount(20);
    expect(offsets).toEqual([0, 20, 0]);
});

test('library fields and submit button disable during login', async ({ page }) => {
    await mockApi(page, 'user', false);
    let release!: () => void;
    const pending = new Promise<void>(resolve => { release = resolve; });
    await page.route('**/v1/auth/login', async route => {
        await pending;
        await route.fulfill({ status: 401, json: {} });
    });
    await page.goto('/#/login');
    const email = page.getByLabel('Email', { exact: true });
    const password = page.getByLabel('Пароль', { exact: true });
    await email.fill('fan@example.com');
    await password.fill('password');
    await page.getByRole('button', { name: 'Войти', exact: true }).click();
    await expect(email).toBeDisabled();
    await expect(password).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Подождите…' }))
        .toBeDisabled();
    release();
    await expect(page.getByRole('alert')).toContainText('Неверный email');
    await expect(email).toBeEnabled();
    await expect(password).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Войти', exact: true }))
        .toBeEnabled();
});


for (const register of [false, true]) {
    for (const interaction of ['double click', 'Enter']) {
        test(`${register ? 'register' : 'login'}: one HTTP request with ${interaction}, retry after failure`, async ({ page }) => {
            const calls = await mockApi(page, 'user', false);
            let requests = 0;
            let release!: () => void;
            const pending = new Promise<void>(resolve => { release = resolve; });
            const path = register ? 'register' : 'login';
            await page.route(`**/v1/auth/${path}`, async route => {
                requests += 1;
                if (requests === 1) await pending;
                await route.fulfill({ status: 503, json: {} });
            });
            await page.goto(`/#/${path}`);
            if (register) {
                await page.getByLabel('Имя пользователя', { exact: true })
                    .fill('anime-fan');
            }
            await page.getByLabel('Email', { exact: true })
                .fill('fan@example.com');
            const password = page.getByLabel('Пароль', { exact: true });
            await password.fill('password');
            const submit = page.getByRole('button', {
                name: register ? 'Создать аккаунт' : 'Войти', exact: true,
            });
            if (interaction === 'double click') await submit.dblclick();
            else await password.press('Enter');
            await expect.poll(() => requests).toBe(1);
            await page.keyboard.press('Enter');
            await page.keyboard.press('Enter');
            release();
            await expect(page.getByRole('alert'))
                .toContainText('временно недоступен');
            expect(requests).toBe(1);
            await expect(submit).toBeEnabled();
            // Two submissions in the same JS turn bypass disabled HTML.
            // The synchronous ref must also guard this path.
            await page.locator('form').evaluate(form => {
                form.dispatchEvent(new Event('submit', {
                    bubbles: true, cancelable: true,
                }));
                form.dispatchEvent(new Event('submit', {
                    bubbles: true, cancelable: true,
                }));
            });
            await expect.poll(() => requests).toBe(2);
            await expect(submit).toBeEnabled();
            expect(calls.filter(call => call.path.includes('/auth/')))
                .toHaveLength(0);
        });
    }
}

test('required fields and invalid email prevent HTTP submissions', async ({ page }) => {
    const calls = await mockApi(page, 'user', false);
    await page.goto('/#/register');
    const submit = page.getByRole('button', { name: 'Создать аккаунт' });
    await submit.click();
    await expect(page.getByLabel('Имя пользователя', { exact: true }))
        .toBeFocused();
    await page.getByLabel('Имя пользователя', { exact: true }).fill('fan');
    await page.getByLabel('Email', { exact: true }).fill('invalid');
    await page.getByLabel('Пароль', { exact: true }).fill('password');
    await submit.click();
    expect(await page.getByLabel('Email', { exact: true }).evaluate(input =>
        (input as HTMLInputElement).validity.typeMismatch)).toBe(true);
    await page.getByLabel('Email', { exact: true }).fill('fan@example.com');
    await page.getByLabel('Пароль', { exact: true }).fill('');
    await submit.click();
    await expect(page.getByLabel('Пароль', { exact: true })).toBeFocused();
    expect(calls.filter(call => call.path.includes('/auth/'))).toHaveLength(0);
});

test('account menu hover, click pinning, keyboard and outside close', async ({ page }) => {
    await mockApi(page, 'admin');
    await page.goto('/');
    const trigger = page.getByRole('button', { name: 'Меню аккаунта' });
    const navigation = page.getByRole('navigation', { name: 'Аккаунт', exact: true });
    await trigger.hover();
    await expect(navigation).toBeVisible();
    await page.mouse.move(1, 1);
    await expect(navigation).toHaveCount(0);
    await trigger.hover();
    await trigger.click();
    await expect(navigation).toBeVisible();
    await page.mouse.move(1, 1);
    await expect(navigation).toBeVisible();
    await trigger.click();
    await expect(navigation).toHaveCount(0);
    await page.mouse.move(1, 1);
    await trigger.focus();
    await page.keyboard.press('Enter');
    await expect(navigation).toBeVisible();
    await page.keyboard.press('Tab');
    await expect(navigation.getByRole('link', { name: 'Аккаунт', exact: true }))
        .toBeFocused();
    await page.keyboard.press('Escape');
    await expect(navigation).toHaveCount(0);
    await expect(trigger).toBeFocused();
    await page.keyboard.press('Space');
    await expect(navigation).toBeVisible();
    await page.getByRole('heading', { name: 'AnimeMap.' }).click();
    await expect(navigation).toHaveCount(0);
    await expect(trigger).toBeFocused();
});

test('search loading and profile failure can recover', async ({ page }) => {
    await mockApi(page, 'admin');
    let release!: () => void;
    const pending = new Promise<void>(resolve => { release = resolve; });
    await page.route('**/v1/account/find/**', async route => {
        await pending;
        await route.fulfill({ json: { accounts: [account] } });
    });
    await page.goto('/#/admin');
    await page.getByLabel('Имя пользователя', { exact: true }).fill('ani');
    await expect(page.getByRole('status')).toContainText('Ищем пользователей');
    release();
    await expect(page.locator('.am-user-row')).toHaveCount(1);
    let fail = true;
    await page.route('**/v1/account/me', route => route.fulfill({
        status: fail ? 503 : 200, json: fail ? {} : account,
    }));
    await page.goto('/#/account');
    await expect(page.getByRole('alert')).toContainText('временно недоступен');
    fail = false;
    await page.getByRole('button', { name: 'Повторить' }).click();
    await expect(page.locator('dd').filter({ hasText: account.email }))
        .toBeVisible();
});

test('application text and badges meet contrast thresholds', async ({ page }) => {
    await mockApi(page, 'admin');
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'AnimeMap.' })).toBeVisible();
    await expectTokenContrast(page, [
        ['story-copy', 'story', 4.5], ['story-label', 'story', 4.5],
        ['home-copy', 'canvas', 4.5], ['home-note', 'canvas', 4.5],
        ['footer', 'canvas', 4.5], ['copyright', 'canvas', 4.5],
        ['header-caption', 'surface-soft', 4.5],
        ['role-text', 'role', 4.5], ['role-admin-text', 'role-admin', 4.5],
        ['role-moderator-text', 'role-moderator', 4.5],
        ['status-text', 'status', 4.5], ['access-text', 'access', 4.5],
        ['row-meta', 'surface', 4.5], ['search-hint', 'surface', 4.5],
    ]);
});

for (const signedIn of [false, true]) {
    test(`${signedIn ? 'protected' : 'auth'} layouts fit desktop and mobile`, async ({ page }) => {
        await mockApi(page, 'admin', signedIn);
        for (const width of [1440, 390]) {
            await page.setViewportSize({ width, height: 900 });
            for (const route of signedIn
                ? ['/', '/account', '/admin'] : ['/login', '/register']) {
                await page.goto(`/#${route}`);
                await expect(page.locator('main')).toBeVisible();
                if (signedIn) {
                    await expect(page.getByRole('button', { name: 'Меню аккаунта' }))
                        .toBeVisible();
                } else {
                    await expect(page.getByLabel('Email', { exact: true }))
                        .toBeVisible();
                }
                expect(await page.evaluate(() =>
                    document.documentElement.scrollWidth <= innerWidth))
                    .toBe(true);
                await page.screenshot({
                    path: test.info().outputPath(
                        `${route.replaceAll('/', '') || 'home'}-${width}.png`
                    ), fullPage: true,
                });
            }
        }
    });
}
