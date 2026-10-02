const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const base = process.env.LESSON_TEST_URL || 'http://127.0.0.1:8877';
    await page.goto(base);
    await page.locator('#demo-banner').waitFor({ state: 'visible' });
    await page.getByRole('button', { name: '01 - Introduzione al progetto', exact: false }).click();
    await page.locator('#editor').waitFor({ state: 'visible' });
    const originalId = await page.locator('.lesson-item.selected').getAttribute('data-lesson-id');
    assert.equal(await page.locator('#record-panel').isVisible(), false);
    // Idle refresh must retain the focused DOM item and avoid detail downloads.
    let detailRequests = 0;
    page.on('request', request => {
      if (request.method() === 'GET' && /\/api\/lessons\/[a-f0-9]{32}$/.test(request.url())) detailRequests++;
    });
    await page.locator('.lesson-item.selected').focus();
    await page.evaluate(() => { window.testArchiveNode = document.activeElement; });
    await page.waitForResponse(response => response.url().endsWith('/api/state'));
    assert.equal(await page.evaluate(() => document.activeElement === window.testArchiveNode && window.testArchiveNode.isConnected), true);
    assert.equal(detailRequests, 0);
    await page.locator('#new-button').click();
    await page.locator('#title-input').fill('02 - Verifica interfaccia');
    await page.getByRole('button', { name: 'Crea lezione' }).click();
    await page.waitForFunction(() => document.querySelector('#lesson-title').textContent === '02 - Verifica interfaccia');
    const secondId = await page.locator('.lesson-item.selected').getAttribute('data-lesson-id');
    // Simulate an old response arriving after a newer selection.
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    let entered;
    const enteredGate = new Promise(resolve => { entered = resolve; });
    await page.route(base + '/api/lessons/' + originalId, async route => {
      const response = await route.fetch();
      entered();
      await gate;
      await route.fulfill({ response });
    });
    await page.locator(`[data-lesson-id="${originalId}"]`).click();
    await enteredGate;
    await page.locator(`[data-lesson-id="${secondId}"]`).click();
    await page.waitForFunction(() => document.querySelector('#lesson-title').textContent === '02 - Verifica interfaccia' && !document.querySelector('#lesson-detail').hidden);
    release();
    await page.unrouteAll({ behavior: 'wait' });
    assert.equal(await page.locator('#lesson-title').textContent(), '02 - Verifica interfaccia');
    await page.locator('#start').click();
    await page.locator('#recording-banner').waitFor({ state: 'visible' });
    await page.locator('#pause').click();
    await page.waitForFunction(() => document.querySelector('#pause').textContent === 'Riprendi');
    await page.locator(`[data-lesson-id="${originalId}"]`).click();
    await page.locator('#show-recording').click();
    await page.locator('#stop').click();
    await page.waitForFunction(() => document.querySelector('#lesson-status').textContent === 'Salvata');
    await page.locator('#editor').fill('Testo revisionato e salvato con tastiera.');
    await page.locator('#editor').press('Control+s');
    await page.locator('#dirty').waitFor({ state: 'hidden' });
    await page.reload();
    await page.locator(`[data-lesson-id="${secondId}"]`).click();
    await page.waitForFunction(() => document.querySelector('#editor').value === 'Testo revisionato e salvato con tastiera.');
    await page.locator('#generate').click();
    await page.waitForFunction(() => document.querySelector('#notes-tab').getAttribute('aria-selected') === 'true' && document.querySelector('#lesson-status').textContent === 'Salvata');
    await page.locator('#archive-lesson').click();
    await page.locator('#restore-lesson').waitFor({ state: 'visible' });
    assert.equal(await page.locator('#editor').isDisabled(), true);
    await page.locator('#restore-lesson').click();
    await page.locator('#archive-lesson').waitFor({ state: 'visible' });
    await page.locator('#toast').waitFor({ state: 'hidden' });
    await page.screenshot({ path: 'test-artifacts/optimized-desktop.png', fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await page.screenshot({ path: 'test-artifacts/optimized-mobile.png', fullPage: true });
    assert.deepEqual(errors, []);
    console.log('PASS: idle polling, focus, response race, recording/pause/stop, save/reload, notes, archive/restore, mobile width; no browser errors.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
