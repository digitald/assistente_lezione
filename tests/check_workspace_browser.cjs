const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8877');
    await page.locator('#demo-banner').waitFor({state:'visible'});
    await page.locator('#profile-button').click();
    await page.locator('#teacher-name').fill('Docente bozza persistente');
    await page.reload();
    await page.locator('#profile-panel').waitFor({state:'visible'});
    assert.equal(await page.locator('#teacher-name').inputValue(),'Docente bozza persistente');
    await page.getByRole('button',{name:'Salva profilo e continua'}).click();
    await page.locator('#create-panel').waitFor({state:'visible'});
    await page.locator('#title-input').fill('Lezione da riprendere');
    await page.reload();
    await page.locator('#new-button').click();
    assert.equal(await page.locator('#title-input').inputValue(),'Lezione da riprendere');
    // Focus stays within the dialog, including Shift+Tab and Escape.
    await page.locator('#cancel-create').focus();
    await page.keyboard.press('Shift+Tab');
    assert.equal(await page.evaluate(()=>document.activeElement.id),'create-submit');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#create-panel').isVisible(),false);
    await page.locator('[data-collection="archived"]').click();
    assert.equal(await page.locator('#page-title').textContent(),'Archiviate');
    await page.locator('[data-collection="active"]').click();
    // Upload an actual mono PCM16 WAV through the new application entry point.
    const wav=Buffer.alloc(44+32000);
    wav.write('RIFF',0);wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);
    wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);
    wav.writeUInt32LE(16000,24);wav.writeUInt32LE(32000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);
    wav.write('data',36);wav.writeUInt32LE(32000,40);
    await page.locator('#new-audio-file').setInputFiles({name:'Registrazione esportata.WAV',mimeType:'audio/wav',buffer:wav});
    await page.locator('#import-summary').waitFor({state:'visible'});
    assert.match(await page.locator('#import-summary').textContent(),/Registrazione esportata.WAV/);
    await page.locator('#title-input').fill('Audio importato dal registratore');
    await page.locator('#create-submit').click();
    await page.waitForFunction(()=>document.querySelector('#lesson-title').textContent==='Audio importato dal registratore'&&document.querySelector('#lesson-status').textContent==='Salvata');
    await page.locator('#export-menu summary').click();
    assert.equal(await page.locator('#download-audio').isVisible(),true);
    await page.keyboard.press('Escape');
    assert.match(await page.locator('#editor').inputValue(),/PROVA SIMULATA/);
    assert.equal(await page.evaluate(()=>localStorage.getItem('lesson-create-draft-v1')),null);
    await page.locator('#generate').click();
    await page.locator('#notes-preview h1').waitFor();
    await page.screenshot({path:'test-artifacts/saas-workspace.png',fullPage:true});
    await page.locator('#new-button').click();
    await page.screenshot({path:'test-artifacts/saas-new-lesson.png',fullPage:true});
    await page.locator('#cancel-create').click();
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:'test-artifacts/saas-mobile.png',fullPage:true});
    assert.deepEqual(errors,[]);
    // Browser storage restrictions must not prevent loading the saved profile.
    const limited=await browser.newPage();
    await limited.addInitScript(()=>{Storage.prototype.getItem=()=>{throw new DOMException('Blocked','SecurityError')};Storage.prototype.setItem=()=>{throw new DOMException('Blocked','SecurityError')};});
    await limited.goto('http://127.0.0.1:8877');
    await limited.waitForFunction(()=>document.querySelector('#course-choice').options.length>0);
    await limited.locator('#new-button').click();
    assert.equal(await limited.locator('#create-panel').isVisible(),true);
    console.log('PASS: profile and lesson drafts survive reload, dialogs and navigation, actual WAV upload in demo, notes flow, desktop/mobile and unavailable browser storage.');
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
