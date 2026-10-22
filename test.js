const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(`file://${process.cwd()}/index.html`);
  const result = await page.evaluate(() => {
    return runUnitTests();
  });
  console.log("Tests passed:", result);
  await browser.close();
  if (!result) process.exit(1);
})();
