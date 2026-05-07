const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(require('os').homedir(), '.arkconfig.json');

function load() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
    }
  } catch (e) {}
  return {};
}

function save(config) {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf-8');
  console.log('  ✓ 配置已保存到', CONFIG_PATH);
}

function set(key, value) {
  const cfg = load();
  cfg[key] = value;
  save(cfg);
}

function setAll(kv) {
  const cfg = load();
  let changed = false;
  for (const k of Object.keys(kv)) {
    if (kv[k] !== undefined) { cfg[k] = kv[k]; changed = true; }
  }
  if (changed) save(cfg);
  return cfg;
}

function get(key) {
  return load()[key];
}

module.exports = { load, save, set, setAll, get, CONFIG_PATH };
