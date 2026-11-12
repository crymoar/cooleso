const { test, expect } = require('@playwright/test');

const RING = { mt: '#f29900', at: '#1f6fe5', both: '#8a4fe0' };

async function openScheme(page) {
  await page.goto('./');
  await expect(page.locator('#scheme svg').first()).toBeVisible({ timeout: 15000 });
  await page.waitForTimeout(800);
}

// видимые в окне кластеры схемы
async function visibleClusters(page) {
  const out = [];
  const vp = page.viewportSize();
  const all = page.locator('.sc-cl');
  for (let i = 0; i < await all.count(); i++) {
    const b = await all.nth(i).boundingBox();
    if (b && b.x >= 0 && b.y >= 60 && b.x + b.width <= vp.width && b.y + b.height <= vp.height) out.push(i);
  }
  return out;
}

test.describe('схема: кластеры', () => {
  test.skip(({ isMobile }) => isMobile, 'клик по кластеру проверяем на десктопе');

  // issue #4 — цвет кластера по коробкам внутри
  test('кластеры окрашены по коробкам (МКПП / АКПП / обе) (#4)', async ({ page }) => {
    await openScheme(page);
    const colors = await page.locator('.sc-cl').evaluateAll(els => els.map(e => e.style.getPropertyValue('--rc').trim()));
    expect(colors.length).toBeGreaterThan(5);
    for (const c of colors) expect(Object.values(RING)).toContain(c);
    expect(new Set(colors).size).toBeGreaterThan(1);
  });

  // issue #6 — каждый кластер реагирует на щелчок (приближение или раскрытие)
  test('щелчок по любому кластеру приближает или раскрывает его (#6)', async ({ page }) => {
    await openScheme(page);
    const n = (await visibleClusters(page)).length;
    expect(n).toBeGreaterThan(3);
    const dead = [];
    for (let k = 0; k < n; k++) {
      await openScheme(page);
      const idx = (await visibleClusters(page))[k];
      if (idx === undefined) continue;
      const el = page.locator('.sc-cl').nth(idx);
      const label = await el.getAttribute('aria-label');
      const before = await page.evaluate(() => JSON.stringify([...document.querySelectorAll('.sc-cl')].map(e => e.getBoundingClientRect().x | 0)));
      await el.click();
      await page.waitForTimeout(900);
      const after = await page.evaluate(() => JSON.stringify([...document.querySelectorAll('.sc-cl')].map(e => e.getBoundingClientRect().x | 0)));
      if (before === after) dead.push(label + ' #' + idx);
    }
    expect(dead, 'кластеры без реакции на щелчок').toEqual([]);
  });
});

test.describe('схема: наведение', () => {
  test.skip(({ isMobile }) => isMobile, 'наведение — только десктоп');

  // issue #5 — подсвечивается линия станции, а не все линии того же цвета
  test('Новокосино подсвечивает свою линию, но не Солнцевскую того же цвета (#5)', async ({ page }) => {
    await openScheme(page);
    await page.fill('#q', 'Новокосино');
    await page.locator('#list .item').first().hover();
    await expect(page.locator('#scheme.hl-on')).toHaveCount(1, { timeout: 3000 });
    const lit = await page.locator('#hltop .lb').evaluateAll(els => els.map(e => e.textContent.replace(/\s+/g, ' ').trim()));
    expect(lit.length).toBeGreaterThan(5);
    expect(lit.join(' ')).toContain('Новокосино');
    expect(lit.join(' ')).not.toMatch(/Солнцево|Рассказовка|Новопеределкино/);
  });

  // issue #3 — наведение есть на метку/подпись и срабатывает с небольшим запасом
  test('наведение на станцию в списке включает подсветку и карточку (#3)', async ({ page }) => {
    await openScheme(page);
    await page.locator('#list .item').nth(3).hover();
    await expect(page.locator('#scheme.hl-on')).toHaveCount(1, { timeout: 3000 });
    await page.mouse.move(5, 5);
    await expect(page.locator('#scheme.hl-on')).toHaveCount(0, { timeout: 3000 });
  });
});

// issue #8 — на телефоне тап по точке сразу показывает карточку
test.describe('мобильная версия', () => {
  test.skip(({ isMobile }) => !isMobile, 'только мобильный проект');

  test('тап по элементу списка открывает карточку места в зоне видимости (#8)', async ({ page }) => {
    await page.goto('./');
    await page.fill('#q', 'ВДНХ');
    await expect(page.locator('#list .item')).toHaveCount(1);
    await page.locator('#list .item').first().tap();
    const card = page.locator('#detail');
    await expect(card).toContainText('ВДНХ');
    await expect(card).toBeVisible({ timeout: 5000 });
    const box = await card.boundingBox();
    const vp = page.viewportSize();
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.y).toBeLessThan(vp.height);
  });
});
