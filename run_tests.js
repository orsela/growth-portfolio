const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const html = fs.readFileSync('./index.html', 'utf8');
const dom = new JSDOM(html, { runScripts: "outside-only", url: "http://localhost/" });

// Since the script runs immediately (including an init loop) it might complain about localStorage or fetch.
// Let's grab the specific function definitions and test them outside the full dom run,
// or define some mocks in the DOM before we load the scripts.

const scriptContent = Array.from(dom.window.document.querySelectorAll('script'))
  .map(s => s.textContent)
  .join('\n');

const testContext = new JSDOM(`<body></body>`, { runScripts: "dangerously" }).window;
testContext.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
  clear: () => {},
  key: () => null,
  length: 0
};
testContext.confirm = () => true;

testContext.eval(`
  let txSide = 'buy';
  function orVal(a, b) { return a ? a : b; }
  function numOrZero(v) { const n = parseFloat(v); return isNaN(n) ? 0 : n; }
  function qfmt(v) { return v.toFixed(4); }
  function usd(v) { return '$' + v.toFixed(2); }
  function px(v) { return '$' + v.toFixed(2); }

  // Re-declare the specific functions we want to test to avoid the UI baggage
  ${scriptContent.match(/function computeExactSMA[\s\S]*?\n\}/)[0]}

  ${scriptContent.match(/function validateTransactionInput[\s\S]*?\n\}/)[0]}

  ${scriptContent.match(/function parseRFC4180CSV[\s\S]*?\n\}/)[0]}

  ${scriptContent.match(/function runUnitTests[\s\S]*?\n\}/)[0]}

  runUnitTests();
`);
