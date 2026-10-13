const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on("pageerror", (e) => console.log("PAGEERROR", e.message));
  page.on("console", (m) => {
    if (m.type() === "error") console.log("CONSOLE", m.text());
  });
  await page.goto("http://127.0.0.1:8000/demo", {
    waitUntil: "networkidle",
    timeout: 30000,
  });
  await page.waitForTimeout(1200);
  console.log("title:", await page.title());

  const opened = await page.evaluate(() => {
    const hosts = [...document.querySelectorAll("*")].filter((el) => el.shadowRoot);
    for (const h of hosts) {
      const b = h.shadowRoot.querySelector("button");
      if (b) {
        b.click();
        return true;
      }
    }
    return false;
  });
  console.log("widget opened:", opened);
  await page.waitForTimeout(600);

  await page.screenshot({
    path:
      "C:/Users/PREETANSH GOHIL/Desktop/New folder (8)/docs/screenshot-demo-opac.png",
  });
  console.log("screenshot saved");

  const body = await page.evaluate(() => document.body.innerText);
  for (const bad of [
    "This page simulates",
    "uvicorn",
    "Ignore previous instructions",
  ]) {
    console.log(body.includes(bad) ? "LEAK " + bad : "clean " + bad);
  }
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
