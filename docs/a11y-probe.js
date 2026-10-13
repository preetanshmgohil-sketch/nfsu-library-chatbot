const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://127.0.0.1:8000/demo', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  const results = [];

  // 1. Trigger reachable by keyboard and opens on Enter
  // In shadow DOM, document.activeElement === host; inner focus lives on shadowRoot.activeElement.
  await page.evaluate(() => document.body.focus());
  let reached = false;
  for (let i = 0; i < 80; i++) {
    await page.keyboard.press('Tab');
    const info = await page.evaluate(() => {
      const host = document.querySelector('[data-nfsu-chatbot]');
      const btn = host && host.shadowRoot && host.shadowRoot.querySelector('button.trigger');
      const inner = host && host.shadowRoot && host.shadowRoot.activeElement;
      return { hostFocused: document.activeElement === host, innerIsTrigger: inner === btn };
    });
    if (info.innerIsTrigger) { reached = true; break; }
  }
  results.push(['trigger focusable by Tab', reached]);

  await page.keyboard.press('Enter');
  await page.waitForTimeout(500);
  const opened = await page.evaluate(() => {
    const host = document.querySelector('[data-nfsu-chatbot]');
    const drawer = host.shadowRoot.querySelector('.drawer');
    return drawer.classList.contains('open') && !drawer.hidden;
  });
  results.push(['Enter opens drawer', opened]);

  // 2. Focus lands in input
  const inputFocused = await page.evaluate(() => {
    const host = document.querySelector('[data-nfsu-chatbot]');
    const ae = host.shadowRoot.activeElement;
    return !!(ae && ae.tagName === 'INPUT');
  });
  results.push(['focus moves to input', inputFocused]);

  // 3. Esc closes and returns focus to trigger
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);
  const closed = await page.evaluate(() => {
    const host = document.querySelector('[data-nfsu-chatbot]');
    const drawer = host.shadowRoot.querySelector('.drawer');
    const trigger = host.shadowRoot.querySelector('button.trigger');
    return {
      closed: !drawer.classList.contains('open'),
      focusReturned: host.shadowRoot.activeElement === trigger
    };
  });
  results.push(['Escape closes drawer', closed.closed]);
  results.push(['focus returns to trigger', closed.focusReturned]);

  // 4. Live region present
  const live = await page.evaluate(() => {
    const host = document.querySelector('[data-nfsu-chatbot]');
    const thread = host.shadowRoot.querySelector('.thread');
    return thread.getAttribute('aria-live') === 'polite' && thread.getAttribute('role') === 'log';
  });
  results.push(['thread is aria-live log', live]);

  // 5. Dialog semantics
  const dialog = await page.evaluate(() => {
    const host = document.querySelector('[data-nfsu-chatbot]');
    const d = host.shadowRoot.querySelector('.drawer');
    return d.getAttribute('role') === 'dialog' && d.getAttribute('aria-modal') === 'true';
  });
  results.push(['drawer role=dialog aria-modal', dialog]);

  // 6. Reduced motion respected
  const rmPage = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  await rmPage.goto('http://127.0.0.1:8000/demo', { waitUntil: 'networkidle' });
  await rmPage.waitForTimeout(800);
  const rm = await rmPage.evaluate(() => {
    const host = document.querySelector('[data-nfsu-chatbot]');
    const pulse = host.shadowRoot.querySelector('.pulse');
    const style = getComputedStyle(pulse);
    return { anim: style.animationName, media: matchMedia('(prefers-reduced-motion: reduce)').matches };
  });
  results.push(['reduced-motion: pulse animation none', rm.media && rm.anim === 'none']);
  await rmPage.close();

  let fail = 0;
  for (const [name, ok] of results) {
    console.log((ok ? 'PASS' : 'FAIL') + '  ' + name);
    if (!ok) fail++;
  }
  await browser.close();
  console.log(fail === 0 ? '\nALL PASS' : '\n' + fail + ' FAILED');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
