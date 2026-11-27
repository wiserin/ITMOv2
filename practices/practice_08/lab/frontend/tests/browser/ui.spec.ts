import { expectTokenContrast } from './contrast';
import { test, expect, type Page } from '@playwright/test';
import { join } from 'node:path';

async function fixture(page: Page) {
    const directory = process.env.UI_FIXTURE_DIR!;
    await page.route('https://fonts.googleapis.com/**', route =>
        route.fulfill({ contentType: 'text/css', body: '' }));
    await page.route('**/broken-avatar.png', route =>
        route.fulfill({ status: 404, body: '' }));
    await page.goto('/health');
    await page.setContent('<div id="root"></div>');
    await page.addStyleTag({ path: join(directory, 'fixture.css') });
    await page.addScriptTag({ path: join(directory, 'fixture.js') });
}

test.beforeEach(async ({ page }) => { await fixture(page); });

test('Button defaults, disabled and loading block clicks', async ({ page }) => {
    const normal = page.getByRole('button', { name: 'Обычная кнопка' });
    await expect(normal).toHaveAttribute('type', 'button');
    await normal.click();
    await expect(page.getByLabel('Число нажатий')).toHaveText('1');
    const disabled = page.getByRole('button', { name: 'Недоступная кнопка' });
    await expect(disabled).toBeDisabled();
    await disabled.evaluate(button => (button as HTMLButtonElement).click());
    await page.getByRole('button', { name: 'Переключить загрузку' }).click();
    const operation = page.getByRole('button', { name: 'Операция' });
    await expect(operation).toBeDisabled();
    await expect(operation).toHaveAttribute('aria-busy', 'true');
    await operation.evaluate(button => (button as HTMLButtonElement).click());
    await expect(page.getByLabel('Число нажатий')).toHaveText('1');
    await page.getByRole('button', { name: 'Переключить загрузку' }).click();
    await expect(operation).toBeEnabled();
    await operation.click();
    await expect(page.getByLabel('Число нажатий')).toHaveText('2');
});

test('TextField labels, ids, hint and error associations', async ({ page }) => {
    const name = page.getByRole('textbox', { name: 'Имя', exact: true });
    await expect(name).toHaveAttribute('id', 'custom-name');
    await expect(name).toHaveAttribute('name', 'name');
    await expect(name).toHaveAttribute('aria-invalid', 'true');
    await expect(name).toHaveAccessibleDescription(
        'Внешнее описание Публичное имя Имя уже занято');
    await page.getByText('Имя', { exact: true }).click();
    await expect(name).toBeFocused();
    const other = page.getByLabel('Дополнительное имя');
    await expect(other).toHaveAccessibleDescription('Необязательно');
    expect(await other.getAttribute('id')).not.toBe(
        await page.getByLabel('Ещё одно имя').getAttribute('id'));
    await expect(page.getByRole('alert')).toHaveText('Имя уже занято');
    // A plain HTML input does not receive library component styles.
    const ordinary = page.locator('aside input');
    expect(await ordinary.evaluate(input =>
        getComputedStyle(input).borderRadius)).toBe('0px');
});

test('SearchField accepts labels and limits, clears and restores focus', async ({ page }) => {
    const search = page.getByRole('searchbox', { name: 'Поиск книг' });
    await expect(search).toHaveAttribute('placeholder', 'Название книги');
    await search.fill('123456789');
    await expect(search).toHaveValue('12345');
    await page.getByRole('button', { name: 'Очистить книги' }).click();
    await expect(search).toHaveValue('');
    await expect(search).toBeFocused();
    await expect(page.getByRole('button', { name: 'Очистить книги' }))
        .toHaveCount(0);
});

test('Pagination uses supplied size, total and explicit boundaries', async ({ page }) => {
    const pages = page.getByRole('navigation', { name: 'Пагинация', exact: true });
    await expect(pages.getByRole('button', { name: 'Назад' })).toBeDisabled();
    await pages.getByRole('button', { name: 'Далее' }).click();
    await expect(pages).toContainText('Страница 2');
    await pages.getByRole('button', { name: 'Далее' }).click();
    await expect(pages).toContainText('Страница 3');
    await expect(pages.getByRole('button', { name: 'Далее' })).toBeDisabled();
    await pages.getByRole('button', { name: 'Назад' }).click();
    await expect(pages).toContainText('Страница 2');
    const last = page.getByRole('navigation', { name: 'Последняя страница' });
    await expect(last.getByRole('button', { name: 'Далее' })).toBeDisabled();
    await last.getByRole('button', { name: 'Назад' }).click();
    await expect(pages).toContainText('Страница 8');
});

test('Dialog supports focus trap, nested ids, Escape and close button', async ({ page }) => {
    const trigger = page.getByRole('button', { name: 'Открыть диалог' });
    await trigger.click();
    const first = page.getByRole('dialog', { name: 'Первый диалог' });
    const close = first.getByRole('button', { name: 'Закрыть диалог' });
    await expect(close).toBeFocused();
    await page.keyboard.press('Shift+Tab');
    await expect(first.getByRole('button', { name: 'Второй диалог' }))
        .toBeFocused();
    await page.keyboard.press('Tab');
    await expect(close).toBeFocused();
    await first.getByRole('button', { name: 'Второй диалог' }).click();
    const second = page.getByRole('dialog', { name: 'Второй диалог' });
    await expect(second).toBeVisible();
    const ids = await page.locator('dialog').evaluateAll(dialogs =>
        dialogs.map(dialog => dialog.getAttribute('aria-labelledby')));
    expect(new Set(ids).size).toBe(2);
    await page.keyboard.press('Escape');
    await expect(second).not.toBeVisible();
    await expect(first.getByRole('button', { name: 'Второй диалог' }))
        .toBeFocused();
    await close.click();
    await expect(first).not.toBeVisible();
    await expect(trigger).toBeFocused();
    await trigger.click();
    await page.keyboard.press('Escape');
    await expect(first).not.toBeVisible();
    await expect(trigger).toBeFocused();
});

test('Dialog backdrop closing is optional, interior does not close', async ({ page }) => {
    const trigger = page.getByRole('button', { name: 'Открыть диалог' });
    await trigger.click();
    const dialog = page.getByRole('dialog', { name: 'Первый диалог' });
    await dialog.getByRole('heading').click();
    await expect(dialog).toBeVisible();
    await page.mouse.click(1, 1);
    await expect(dialog).not.toBeVisible();
    await expect(trigger).toBeFocused();
    await page.getByRole('button', { name: 'Переключить закрытие по фону' })
        .click();
    await trigger.click();
    await page.mouse.click(1, 1);
    await expect(dialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(trigger).toBeFocused();
});

test('Avatar fallback, image and size; reduced motion', async ({ page }) => {
    await expect(page.getByRole('img', { name: 'Катя', exact: true }))
        .toHaveText('К');
    const large = page.getByRole('img', { name: 'Лена', exact: true });
    await expect(large).toHaveText('Л');
    expect(await large.evaluate(node => node.getBoundingClientRect().width))
        .toBe(64);
    await expect(page.getByRole('img', { name: 'Фото', exact: true })
        .locator('img')).toBeVisible();
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.getByRole('button', { name: 'Переключить загрузку' }).click();
    expect(await page.locator('.ui-spinner').evaluate(node =>
        getComputedStyle(node).animationName)).toBe('none');
});

test('UI text, placeholder, error and focus meet contrast thresholds', async ({ page }) => {
    await expectTokenContrast(page, [
        ['text', 'canvas', 4.5], ['text', 'surface', 4.5],
        ['muted', 'surface', 4.5], ['muted', 'canvas', 4.5],
        ['placeholder', 'surface', 4.5],
        ['placeholder', 'surface-soft', 4.5],
        ['error', 'surface', 4.5], ['error', 'canvas', 4.5],
        ['surface', 'primary', 4.5], ['surface', 'primary-hover', 4.5],
        ['text', 'success', 4.5], ['avatar-text', 'avatar', 4.5],
        ['focus', 'surface', 3], ['focus', 'canvas', 3],
        ['input-border', 'surface', 3],
    ]);
});
