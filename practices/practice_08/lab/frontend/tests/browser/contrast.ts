import { expect, type Page } from '@playwright/test';

export async function expectTokenContrast(
    page: Page, pairs: [string, string, number][],
) {
    const ratios = await page.evaluate(items => {
        const probe = document.createElement('span');
        document.body.append(probe);
        function luminance(token: string) {
            probe.style.color = `var(--color-${token})`;
            const channels = getComputedStyle(probe).color
                .match(/[\d.]+/g)!.slice(0, 3).map(Number)
                .map(value => {
                    const channel = value / 255;
                    return channel <= 0.04045 ? channel / 12.92
                        : ((channel + 0.055) / 1.055) ** 2.4;
                });
            return channels[0] * 0.2126 + channels[1] * 0.7152
                + channels[2] * 0.0722;
        }
        const results = items.map(([foreground, background]) => {
            const a = luminance(foreground);
            const b = luminance(background);
            return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
        });
        probe.remove();
        return results;
    }, pairs);
    pairs.forEach(([foreground, background, minimum], index) => {
        expect(ratios[index], `${foreground} on ${background}`)
            .toBeGreaterThanOrEqual(minimum);
    });
}
