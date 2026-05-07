const fs = require('fs');
const path = require('path');

const PROMPTS_DIR = path.join(__dirname, '..', 'prompts');

function load(name, vars = {}) {
  const filePath = path.join(PROMPTS_DIR, name);
  let text = fs.readFileSync(filePath, 'utf-8');
  for (const [k, v] of Object.entries(vars)) {
    text = text.replaceAll(`{{${k}}}`, v != null ? String(v) : '');
  }
  return text;
}

function loadLines(name, vars = {}) {
  return load(name, vars).split('\n');
}

module.exports = { load, loadLines, PROMPTS_DIR };
