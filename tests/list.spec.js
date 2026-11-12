const { test, expect } = require('@playwright/test');

// issue #14 — мотоплощадка в списке в том же формате, что остальные точки:
// станция + тег + адрес.
test.describe('список: мотоплощадки (#14)', () => {
  test.beforeEach(async ({ page }) => { await page.goto('./'); });

  test('мотоплощадка: станция, тег сезона, адрес', async ({ page }) => {
    await page.click('[data-kpp="moto"]');
    const item = page.locator('#list .item', { hasText: 'Люблино' });
    await expect(item).toHaveCount(1);
    await expect(item.locator('.t')).toHaveText('Люблино');          // станция, не «Мотоплощадка · …»
    await expect(item.locator('.chips .tag.mo')).toHaveText('Летняя площадка'); // тег
    await expect(item.locator('.s')).toContainText('Люблинская, д. 42');        // адрес
    await expect(item.locator('.s svg')).toHaveCount(1);              // значок дома, как у адреса станции
  });

  test('все мотоплощадки: тег и адрес есть, «Мотоплощадка ·» в заголовке нет', async ({ page }) => {
    await page.click('[data-kpp="moto"]');
    const items = page.locator('#list .item');
    expect(await items.count()).toBeGreaterThanOrEqual(10);
    for (const it of await items.all()) {
      await expect(it.locator('.t')).not.toContainText('Мотоплощадка');
      await expect(it.locator('.chips .tag.mo')).toHaveCount(1);
      await expect(it.locator('.s')).not.toBeEmpty();
    }
  });

  test('мотоплощадки отсортированы по станции', async ({ page }) => {
    await page.click('[data-kpp="moto"]');
    const names = await page.locator('#list .item .t').allTextContents();
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, 'ru')));
  });

  test('поиск по адресу находит мотоплощадку', async ({ page }) => {
    await page.click('[data-kpp="moto"]');
    await page.fill('#q', 'Люблинская');
    await expect(page.locator('#list .item')).toHaveCount(1);
  });
});
