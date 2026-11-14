// Режим ?embed=1: карта в iframe на чужой странице (сайт на Тильде).
// Страница-хозяин: блок 600px, iframe с картой, блок 600px.
const { test, expect, devices } = require('@playwright/test');

async function openHost(page, baseURL, iframeHeight = '90vh') {
  // страница-хозяин подставляется рядом с картой (Chrome не даёт внешней странице встроить localhost)
  const HOST = new URL('__embed-host.html', baseURL).href;
  const src = new URL('./?embed=1', baseURL).href;
  await page.route(HOST, route => route.fulfill({
    contentType: 'text/html',
    body: `<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{margin:0}.blk{height:600px;background:#eee}</style>
<div class="blk" id="top">Блок сверху</div>
<iframe id="koleso" src="${src}" style="display:block;width:100%;height:${iframeHeight};border:0"></iframe>
<div class="blk" id="bottom">Блок снизу</div>`,
  }));
  await page.goto(HOST);
  const frame = page.frameLocator('#koleso');
  await expect(frame.locator('#list .item').first()).toBeVisible();
  await expect(frame.locator('#scheme svg').first()).toBeVisible({ timeout: 15000 });
  await page.waitForTimeout(800);
  const f = page.frames().find(x => /embed=1/.test(x.url()));
  return { frame, f };
}

// iframe ставится вверх окна: страница прокручена ровно на верхний блок
async function scrollHostTo(page, y) {
  await page.evaluate(y => window.scrollTo(0, y), y);
  await page.waitForTimeout(100);
}
const hostY = page => page.evaluate(() => window.scrollY);
const schemeSize = f => f.evaluate(() => { const r = document.querySelector('#scheme svg').getBoundingClientRect(); return Math.round(r.width); });
const schemeX = f => f.evaluate(() => Math.round(document.querySelector('#scheme svg').getBoundingClientRect().x));

async function box(page, frameLocator, sel) {
  const b = await frameLocator.locator(sel).first().boundingBox(); // уже в координатах окна
  return { x: b.x + b.width / 2, y: b.y + b.height / 2, b };
}

// касания через CDP (как настоящий палец: браузер сам решает, что прокручивать)
async function touches(cdp, page, from, to, steps = 10) {
  const at = k => from.map((p, i) => ({ x: Math.round(p.x + (to[i].x - p.x) * k), y: Math.round(p.y + (to[i].y - p.y) * k), id: i }));
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: at(0) });
  for (let i = 1; i <= steps; i++) {
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: at(i / steps) });
    await page.waitForTimeout(16);
  }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await page.waitForTimeout(400);
}
// свайп одним пальцем вверх на dy (= прокрутка вниз)
const swipe = (cdp, page, x, y, dy) => touches(cdp, page, [{ x, y }], [{ x, y: y - dy }]);
// два пальца раздвигаются вокруг точки
const pinch = (cdp, page, x, y) => touches(cdp, page, [{ x: x - 30, y }, { x: x + 30, y }], [{ x: x - 110, y }, { x: x + 110, y }], 12);

test.describe('embed: компьютер', () => {
  test.skip(() => test.info().project.name !== 'desktop', 'десктопный проект');

  test('у документа в iframe нет своей прокрутки, без embed — прежний вид', async ({ page, baseURL }) => {
    const { f } = await openHost(page, baseURL);
    const [sh, ch] = await f.evaluate(() => [document.documentElement.scrollHeight, document.documentElement.clientHeight]);
    expect(sh).toBeLessThanOrEqual(ch);
    expect(await f.evaluate(() => document.documentElement.classList.contains('embed'))).toBe(true);
    await page.goto(baseURL);
    expect(await page.evaluate(() => document.documentElement.classList.contains('embed'))).toBe(false);
  });

  test('колесо над схемой листает страницу, Ctrl + колесо и кнопки +/− меняют масштаб (п. 3)', async ({ page, baseURL }) => {
    const { frame, f } = await openHost(page, baseURL);
    await scrollHostTo(page, 300);
    const s0 = await schemeSize(f);
    const c = await box(page, frame, '#scheme');
    await page.mouse.move(c.x, c.y);
    await page.mouse.wheel(0, 400);
    await page.waitForTimeout(500);
    expect(await hostY(page)).toBeGreaterThan(300);
    expect(await schemeSize(f)).toBe(s0);
    await expect(frame.locator('#gesture-hint')).toHaveClass(/on/);

    const y1 = await hostY(page);
    const c2 = await box(page, frame, '#scheme');
    await page.mouse.move(c2.x, c2.y);
    await page.keyboard.down('Control');
    await page.mouse.wheel(0, -240);
    await page.keyboard.up('Control');
    await page.waitForTimeout(500);
    expect(await hostY(page)).toBe(y1);
    const s1 = await schemeSize(f);
    expect(s1).toBeGreaterThan(s0);

    await frame.locator('#sc-zoom [aria-label="Приблизить"]').click();
    await page.waitForTimeout(600);
    expect(await schemeSize(f)).toBeGreaterThan(s1);
    expect(await hostY(page)).toBe(y1);
  });

  test('выбор места не прокручивает окно: карточка открывается в панели (п. 4)', async ({ page, baseURL }) => {
    const { frame, f } = await openHost(page, baseURL);
    await scrollHostTo(page, 600);
    const item = frame.locator('#list .item').nth(12);
    await item.scrollIntoViewIfNeeded();
    const y0 = await hostY(page);
    await item.click();
    await expect(frame.locator('#detail')).toBeVisible();
    expect(await hostY(page)).toBe(y0);
    expect(await f.evaluate(() => window.scrollY)).toBe(0);
    expect(await f.evaluate(() => document.getElementById('detail').scrollTop)).toBe(0);
    await frame.locator('#detail .back').click();
    await expect(frame.locator('#list')).toBeVisible();
    expect(await hostY(page)).toBe(y0);
  });

  test('все внешние ссылки открываются в новой вкладке, в подвале — «Открыть на весь экран» (п. 5, 6)', async ({ page, baseURL }) => {
    const { frame, f } = await openHost(page, baseURL);
    const full = frame.locator('#foot a', { hasText: 'Открыть на весь экран' });
    await expect(full).toBeVisible();
    const href = await full.getAttribute('href');
    expect(href).not.toContain('embed');
    expect(new URL(href).pathname).toBe(new URL(baseURL).pathname);
    await expect(frame.locator('#foot a', { hasText: 'OpenStreetMap' })).toHaveAttribute('target', '_blank');

    await frame.locator('#list .item').first().click();
    await expect(frame.locator('#detail a').first()).toBeVisible();
    await frame.locator('#v-map').click();
    await expect(frame.locator('.leaflet-control-attribution a').first()).toBeAttached({ timeout: 15000 });
    const bad = await f.evaluate(() => [...document.querySelectorAll('a[href]')]
      .filter(a => /^https?:/i.test(a.getAttribute('href')) && a.target !== '_blank').map(a => a.outerHTML.slice(0, 120)));
    expect(bad).toEqual([]);
  });
});

test.describe('embed: iPhone 13', () => {
  test.skip(() => test.info().project.name !== 'mobile', 'мобильный проект');
  const { defaultBrowserType, ...iphone } = devices['iPhone 13'];
  test.use(iphone); // браузер — chromium из проекта mobile

  test('карта занимает высоту iframe: схема сверху ~45 %, поиск и фильтры закреплены, листается только список (п. 1)', async ({ page, baseURL }) => {
    const { frame, f } = await openHost(page, baseURL);
    const m = await f.evaluate(() => {
      const r = s => document.querySelector(s).getBoundingClientRect();
      const de = document.documentElement, l = document.getElementById('list');
      return { sh: de.scrollHeight, ch: de.clientHeight, ih: innerHeight, map: r('.map-wrap'), panel: r('.panel'), q: r('#q'),
        list: { sh: l.scrollHeight, ch: l.clientHeight }, head: getComputedStyle(document.querySelector('.head')).display };
    });
    expect(m.sh).toBeLessThanOrEqual(m.ch);
    expect(m.map.top).toBe(0);
    expect(m.map.height / m.ih).toBeGreaterThan(0.4);
    expect(m.map.height / m.ih).toBeLessThan(0.5);
    expect(Math.round(m.panel.bottom)).toBe(m.ih);
    expect(m.list.sh).toBeGreaterThan(m.list.ch + 100);
    expect(m.list.ch).toBeGreaterThan(80);

    // свайп по списку листает список, поиск остаётся на месте
    const cdp = await page.context().newCDPSession(page);
    await scrollHostTo(page, 600);
    const l = await box(page, frame, '#list');
    const q0 = (await frame.locator('#q').boundingBox()).y;
    await swipe(cdp, page, l.x, l.y + 40, 120);
    expect(await f.evaluate(() => document.getElementById('list').scrollTop)).toBeGreaterThan(50);
    expect((await frame.locator('#q').boundingBox()).y).toBe(q0);
    expect(await f.evaluate(() => window.scrollY)).toBe(0);
  });

  test('когда список долистан до конца, свайп листает родительскую страницу (п. 1)', async ({ page, baseURL }) => {
    const { frame, f } = await openHost(page, baseURL);
    const cdp = await page.context().newCDPSession(page);
    await scrollHostTo(page, 600);
    await f.evaluate(() => { const l = document.getElementById('list'); l.scrollTop = l.scrollHeight; });
    await page.waitForTimeout(100);
    const y0 = await hostY(page);
    const l = await box(page, frame, '#list');
    const vh = page.viewportSize().height;
    const y = Math.min(l.b.y + l.b.height - 20, vh - 20);
    expect(y).toBeGreaterThan(l.b.y + 20);
    await swipe(cdp, page, l.x, y, 150);
    expect(await hostY(page)).toBeGreaterThan(y0 + 50);
  });

  test('схема: одним пальцем листается страница и видна подсказка, двумя — двигается схема (п. 2)', async ({ page, baseURL }) => {
    const { frame, f } = await openHost(page, baseURL);
    const cdp = await page.context().newCDPSession(page);
    await scrollHostTo(page, 400);
    const y0 = await hostY(page);
    const x0 = await schemeX(f), s0 = await schemeSize(f);
    const c = await box(page, frame, '#scheme');
    await swipe(cdp, page, c.x, c.y + 40, 120);
    await expect(frame.locator('#gesture-hint')).toHaveClass(/on/);
    await expect(frame.locator('#gesture-hint')).toHaveText('Двигайте двумя пальцами');
    expect(await hostY(page)).toBeGreaterThan(y0 + 50);
    expect(await schemeX(f)).toBe(x0);
    expect(await schemeSize(f)).toBe(s0);

    // два пальца — масштаб схемы, страница на месте
    const y1 = await hostY(page);
    const c2 = await box(page, frame, '#scheme');
    await pinch(cdp, page, c2.x, c2.y);
    await page.waitForTimeout(500);
    expect(await schemeSize(f)).toBeGreaterThan(s0);
    expect(await hostY(page)).toBe(y1);
  });

  test('тап по станции на схеме открывает карточку в панели, окно не прокручивается (п. 2, 4)', async ({ page, baseURL }) => {
    const { frame, f } = await openHost(page, baseURL);
    await scrollHostTo(page, 600);
    const y0 = await hostY(page);
    // ближайшая к центру одиночная метка места на схеме
    const pt = await f.evaluate(() => {
      const s = document.getElementById('scheme').getBoundingClientRect();
      const cx = s.x + s.width / 2, cy = s.y + s.height / 2;
      let best = null, bd = 1e9;
      for (const p of document.querySelectorAll('.leaflet-marks-pane path.leaflet-interactive')) {
        const r = p.getBoundingClientRect();
        const x = r.x + r.width / 2, y = r.y + r.height / 2;
        if (x < s.x + 5 || x > s.right - 60 || y < s.y + 50 || y > s.bottom - 5) continue;
        const d = Math.hypot(x - cx, y - cy);
        if (d < bd) { bd = d; best = { x, y }; }
      }
      return best;
    });
    expect(pt, 'на схеме есть одиночная метка').not.toBeNull();
    const fb = await page.locator('#koleso').boundingBox();
    await page.touchscreen.tap(fb.x + pt.x, fb.y + pt.y);
    await expect(frame.locator('#panel.show-detail')).toHaveCount(1, { timeout: 3000 });
    await expect(frame.locator('#detail')).toBeVisible();
    expect(await hostY(page)).toBe(y0);
    expect(await f.evaluate(() => window.scrollY)).toBe(0);
  });

  test('тап по месту в списке открывает карточку внутри панели, окно не прокручивается (п. 4)', async ({ page, baseURL }) => {
    const { frame, f } = await openHost(page, baseURL);
    await scrollHostTo(page, 600);
    await f.evaluate(() => { document.getElementById('list').scrollTop = 400; });
    const y0 = await hostY(page);
    const items = frame.locator('#list .item');
    let idx = 0;
    for (let i = 0; i < await items.count(); i++) {
      const b = await items.nth(i).boundingBox();
      const l = await frame.locator('#list').boundingBox();
      if (b && b.y > l.y && b.y + b.height < l.y + l.height) { idx = i; break; }
    }
    const ib = await items.nth(idx).boundingBox();
    await page.touchscreen.tap(ib.x + ib.width / 2, ib.y + ib.height / 2);
    const d = frame.locator('#detail');
    await expect(d).toBeVisible();
    const db = await d.boundingBox(), fb = await page.locator('#koleso').boundingBox();
    expect(db.y).toBeGreaterThanOrEqual(fb.y);
    expect(db.y + 40).toBeLessThan(fb.y + fb.height);
    expect(await hostY(page)).toBe(y0);
    expect(await f.evaluate(() => window.scrollY)).toBe(0);
    await frame.locator('#detail .back').tap();
    await expect(items.nth(idx)).toBeVisible();
    expect(await f.evaluate(() => document.getElementById('list').scrollTop)).toBe(400);
  });

  test('карта города: одним пальцем листается страница, карта на месте (п. 2)', async ({ page, baseURL }) => {
    const { frame, f } = await openHost(page, baseURL);
    await frame.locator('#v-map').tap();
    await expect(frame.locator('#map.leaflet-container')).toBeVisible({ timeout: 15000 });
    await page.waitForTimeout(800);
    const cdp = await page.context().newCDPSession(page);
    await scrollHostTo(page, 400);
    const y0 = await hostY(page);
    const pane = () => f.evaluate(() => document.querySelector('#map .leaflet-map-pane').style.transform);
    const t0 = await pane();
    expect(await f.evaluate(() => getComputedStyle(document.getElementById('map')).touchAction)).toBe('pan-x pan-y');
    const c = await box(page, frame, '#map');
    await swipe(cdp, page, c.x, c.y + 40, 120);
    await expect(frame.locator('#gesture-hint')).toHaveClass(/on/);
    expect(await hostY(page)).toBeGreaterThan(y0 + 50);
    expect(await pane()).toBe(t0);
  });
});
