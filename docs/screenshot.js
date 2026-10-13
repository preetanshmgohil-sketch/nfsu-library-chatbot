const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 860 } });
  await page.goto('http://127.0.0.1:8000/demo', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);

  // 1. Closed state — trigger visible
  await page.screenshot({ path: 'docs/screenshot-1-trigger.png' });

  // 2. Open drawer — welcome + chips
  await page.click('[data-nfsu-chatbot] button.trigger');
  await page.waitForTimeout(700);
  await page.screenshot({ path: 'docs/screenshot-2-welcome.png' });

  // 3. Send a catalog search (live KOHA scrape can take a few seconds)
  await page.fill('[data-nfsu-chatbot] input', 'Find books on forensic DNA analysis');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(15000);
  await page.screenshot({ path: 'docs/screenshot-3-search.png' });

  // 4. FAQ
  await page.fill('[data-nfsu-chatbot] input', 'What are the library timings?');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'docs/screenshot-4-faq.png' });

  // 5. Dark mode
  const themeBtns = await page.$$('[data-nfsu-chatbot] .icon-btn');
  // theme button is the second icon-btn (lang is first with text, then theme)
  for (const btn of themeBtns) {
    const label = await btn.getAttribute('aria-label');
    if (label && label.toLowerCase().includes('dark')) { await btn.click(); break; }
  }
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'docs/screenshot-5-dark.png' });

  // 6. Mobile viewport
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'docs/screenshot-6-mobile.png' });

  await browser.close();
  console.log('screenshots written');
})().catch((e) => { console.error(e); process.exit(1); });
