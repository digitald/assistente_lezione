const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage();
    await page.goto('http://127.0.0.1:8877');
    await page.locator('#demo-banner').waitFor({ state: 'visible' });
    for (const legacy of [false, true]) {
      await page.locator('#profile-button').click();
      const name = legacy ? 'Docente recupero server precedente' : 'Docente recupero sessione';
      await page.locator('#teacher-name').fill(name);
      let attempts = 0;
      const payloads = [];
      await page.route('**/api/profile', async route => {
        if (route.request().method() !== 'POST') return route.continue();
        attempts++;
        payloads.push(route.request().postDataJSON());
        if (attempts === 1) {
          // Il vero server rifiuta il token, senza salvare il profilo.
          const rejected = await route.fetch({ headers: { ...route.request().headers(), 'x-local-token': 'expired' } });
          assert.equal(rejected.status(), 403);
          if (legacy) return route.fulfill({ status: 403, json: { error: 'Ricarica la pagina prima di continuare.' } });
          return route.fulfill({ response: rejected });
        }
        return route.continue();
      });
      await page.getByRole('button', { name: 'Salva profilo e continua' }).click();
      await page.locator('#profile-panel').waitFor({ state: 'hidden' });
      assert.equal(attempts, 2);
      assert.deepEqual(payloads[0], payloads[1]);
      assert.equal((await (await page.request.get('http://127.0.0.1:8877/api/profile')).json()).name, name);
      await page.unrouteAll();
      await page.locator('#cancel-create').click();
    }
    // Altri errori e problemi di rete non devono ripetere il comando.
    for (const failure of ['validation', 'forbidden', 'network', 'expired-twice']) {
      if (!await page.locator('#profile-panel').isVisible()) await page.locator('#profile-button').click();
      await page.locator('#teacher-name').fill('Bozza conservata ' + failure);
      let attempts = 0;
      await page.route('**/api/profile', async route => {
        if (route.request().method() !== 'POST') return route.continue();
        attempts++;
        if (failure === 'network') return route.abort('failed');
        return route.fulfill({ status: failure === 'validation' ? 400 : 403, json:
          failure === 'expired-twice' ? { code: 'local_token_expired', error: 'Sessione cambiata' } : { error: 'Errore di prova' } });
      });
      await page.getByRole('button', { name: 'Salva profilo e continua' }).click();
      await page.locator('#profile-error').waitFor({ state: 'visible' });
      assert.equal(attempts, failure === 'expired-twice' ? 2 : 1);
      assert.equal(await page.locator('#teacher-name').inputValue(), 'Bozza conservata ' + failure);
      assert.equal(await page.getByRole('button', { name: 'Salva profilo e continua' }).isEnabled(), true);
      await page.unrouteAll();
    }
    console.log('PASS: expired token and legacy server recover; original fields preserved; retries bounded; no retry for validation, generic 403 or network failures.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
