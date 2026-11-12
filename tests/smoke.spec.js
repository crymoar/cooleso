const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

test.describe('smoke', () => {
  test('страница открывается без ошибок в консоли', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error' && !/404/.test(m.text())) errors.push(m.text()); });
    page.on('response', r => { if (r.status() >= 400 && !/favicon/.test(r.url())) errors.push(r.status() + ' ' + r.url()); });
    await page.goto('./');
    await expect(page.locator('#list .item').first()).toBeVisible();
    expect(errors).toEqual([]);
  });

  test('в списке есть станции и мотоплощадки, счётчик не нулевой', async ({ page }) => {
    await page.goto('./');
    await expect(page.locator('#n-all')).not.toHaveText('0');
    expect(await page.locator('#list .item').count()).toBeGreaterThan(50);
  });

  test('схема метро загружается', async ({ page }) => {
    await page.goto('./');
    await expect(page.locator('#scheme svg').first()).toBeVisible({ timeout: 15000 });
  });
});

// Только локально: map/index.html должен быть точной копией map/src/template.html.
test('index.html совпадает с src/template.html', async ({ baseURL }) => {
  test.skip(!/localhost/.test(baseURL), 'проверка исходников — только локально');
  const root = path.join(__dirname, '..', 'map');
  const a = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const b = fs.readFileSync(path.join(root, 'src', 'template.html'), 'utf8');
  expect(a === b, 'index.html не обновлён из src/template.html').toBe(true);
});
