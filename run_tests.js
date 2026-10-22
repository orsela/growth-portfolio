const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const html = fs.readFileSync('./index.html', 'utf8');

// We should NOT run the scripts when loading the HTML just to extract them,
// otherwise the first JSDOM instance throws the opaque origin error
const dom = new JSDOM(html);

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

  ${scriptContent.match(/function toBase64Utf8[\s\S]*?\n\}/)[0]}

  ${scriptContent.match(/function runUnitTests[\s\S]*?\n\}/)[0]}

  runUnitTests();
`);
