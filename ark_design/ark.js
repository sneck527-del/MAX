#!/usr/bin/env node

const path = require('path');
const fs = require('fs');
const config = require('./lib/config.js');
const api = require('./lib/api.js');
const engine = require('./lib/engine.js');
const ppt = require('./lib/ppt.js');
const gz = require('./lib/guizangRenderer.js');
const speech = require('./lib/speech.js');
const render = require('./lib/render.js');

// ==================== 颜色输出 ====================
const C = {
  reset: '\x1b[0m', dim: '\x1b[2m', bold: '\x1b[1m',
  cyan: '\x1b[36m', green: '\x1b[32m', yellow: '\x1b[33m',
  red: '\x1b[31m', magenta: '\x1b[35m',
};

// ==================== 参数解析 ====================

function parseArgs(arr) {
  const out = { _: [] };
  for (let i = 0; i < arr.length; i++) {
    if (arr[i].startsWith('--')) {
      let key = arr[i].slice(2);
      let val;
      if (key.includes('=')) {
        [key, val] = key.split('=');
      } else if (i + 1 < arr.length && !arr[i + 1].startsWith('--')) {
        val = arr[++i];
      } else {
        val = true;
      }
      out[key] = val;
    } else {
      out._.push(arr[i]);
    }
  }
  return out;
}

// ==================== 主入口 ====================

async function main() {
  const raw = process.argv.slice(2);
  const cmd = raw[0];

  if (!cmd || cmd === '--help' || cmd === '-h') {
    return showHelp();
  }

  try {
    switch (cmd) {
      case 'config':    return handleConfig(parseArgs(raw.slice(1)));
      case 'debate':    return await handleDebate(parseArgs(raw.slice(1)));
      case 'ppt':       return await handlePpt(parseArgs(raw.slice(1)));
      case 'speech':    return await handleSpeech(parseArgs(raw.slice(1)));
      case 'render':    return await handleRender(parseArgs(raw.slice(1)));
      case 'all':       return await handleAll(parseArgs(raw.slice(1)));
      default:
        console.error(C.red + '未知命令: ' + cmd + C.reset);
        return showHelp();
    }
  } catch (e) {
    console.error(C.red + '\n✗ 错误: ' + e.message + C.reset);
    process.exit(1);
  }
}

// ==================== 帮助 ====================

function showHelp() {
  console.log(C.bold + 'ARK Design CLI — AI室内设计辩论引擎\n' + C.reset);
  console.log(C.dim + '用法:\n' + C.reset);
  console.log('  node ark.js config --key <api-key> [--provider <name>]');
  console.log('  node ark.js debate --name <项目名> --type <类型> [options]');
  console.log('  node ark.js ppt <项目目录> [--theme <主题>]');
  console.log('  node ark.js speech <项目目录> [options]');
  console.log('  node ark.js render <项目目录>    grsai 生图替换占位符');
  console.log('  node ark.js all --name ... --type ... [options]  一步完成全部\n');
  console.log(C.dim + 'config:\n' + C.reset);
  console.log('  --key <key>          API Key');
  console.log('  --provider <name>    提供商 (deepseek/openai/qwen/zhipu/doubao)');
  console.log('  --model <model>      模型名');
  console.log('  --url <url>          API地址\n');
  console.log(C.dim + 'debate:\n' + C.reset);
  console.log('  --name <name>        项目名称 (必填)');
  console.log('  --type <type>        类型: residential/restaurant/hotel/exhibition/retail');
  console.log('  --budget <amount>    预算金额 (必填)');
  console.log('  --city <city>        城市');
  console.log('  --region <text>      地域特征');
  console.log('  --area <sqm>        面积');
  console.log('  --brief <text>       简介');
  console.log('  --tags <tags>        客户标签 (逗号分隔)');
  console.log('  --habits <habits>    需求 (逗号分隔)');
  console.log('  --funding <a,b,c>    分期资金 (逗号分隔)');
  console.log('  --profile <path>     JSON profile 文件 (公司名/风格/禁用词等)');
  console.log('  --output <dir>       输出目录\n');
  console.log(C.dim + 'speech:\n' + C.reset);
  console.log('  node ark.js speech <目录>  从已有结果生成演讲稿');
  console.log('  --output <path>      输出路径 (默认: 项目目录/speech.md)');
  console.log('  --no-ai              只用模板生成（不调用AI）\n');
  console.log(C.dim + 'all:\n' + C.reset);
  console.log('  接受 debate 的所有参数 + 以下额外选项:');
  console.log('  --theme <主题>       ' + ppt.THEME_KEYS.join('/') + ' (默认: 沙丘)');
  console.log('  --style <style>      classic | guizang (默认: classic)');
  console.log('  --profile <path>     JSON profile 文件 (公司名/风格/禁用词等)');
  console.log('  --no-ai-speech       演讲稿只用模板生成\n');
}

// ==================== Config ====================

function handleConfig(o) {
  config.setAll({ apiKey: o.key, provider: o.provider, model: o.model, apiUrl: o.url });
  const c = config.load();
  console.log(C.green + '✓ 当前配置:' + C.reset);
  console.log('  提供商: ' + (c.provider || '未设置'));
  console.log('  模型: ' + (c.model || '未设置'));
  console.log('  API Key: ' + (c.apiKey ? c.apiKey.slice(0, 8) + '…' : '未设置'));
  if (!c.apiKey) console.log(C.yellow + '  ⚠ 设置: node ark.js config --key sk-xxxxx' + C.reset);
}

// ==================== Debate ====================

async function handleDebate(o) {
  const { project, projectDir, apiOpts } = validateDebateOpts(o);

  console.log('\n' + C.cyan + '╔' + '═'.repeat(48) + '╗' + C.reset);
  console.log(C.cyan + '║' + C.bold + '  ARK Design · AI室内设计辩论引擎' + C.reset + C.cyan + '    ║' + C.reset);
  console.log(C.cyan + '╚' + '═'.repeat(48) + '╝' + C.reset);
  console.log(C.dim + '  项目: ' + project.name);
  console.log('  类型: ' + (engine.SPACE_TYPES[project.spaceType]?.label || project.spaceType));
  if (project.city) console.log('  地点: ' + project.city);
  console.log('  预算: ¥' + engine.fmt(project.budget));
  console.log('  API: ' + apiOpts.provider + ' / ' + apiOpts.model + C.reset);
  console.log('  输出: ' + projectDir + '\n');

  fs.writeFileSync(path.join(projectDir, 'project.json'), JSON.stringify(project, null, 2), 'utf-8');

  let termBuf = '';
  const { debateLog, narrative, pages } = await engine.runDebate(project, (chunk) => {
    process.stdout.write(chunk);
    termBuf += chunk;
  }, apiOpts);

  const result = { project, debateLog, narrative, pages, generatedAt: new Date().toISOString() };
  fs.writeFileSync(path.join(projectDir, 'result.json'), JSON.stringify(result, null, 2), 'utf-8');
  fs.writeFileSync(path.join(projectDir, 'debate.log'), termBuf, 'utf-8');

  console.log(C.green + '\n✓ 辩论完成！' + C.reset);
  console.log(C.dim + '  结果: ' + projectDir + C.reset + '\n');

  // 自动生成PPT
  const style = o.style || 'classic';
  console.log(C.cyan + '▶ 生成PPT... 风格: ' + style + '\n' + C.reset);
  const pptPath = path.join(projectDir, 'proposal.html');
  try {
    const html = style === 'guizang'
      ? await gz.generatePpt(project, debateLog, { narrative, pages })
      : await ppt.generatePpt(project, debateLog, { narrative, pages }, '沙丘');
    (style === 'guizang' ? saveHtml : ppt.savePpt)(html, pptPath);
    console.log(C.green + '  ✓ PPT: ' + pptPath + C.reset);
  } catch (e) {
    console.log(C.yellow + '  ⚠ PPT生成跳过: ' + e.message + C.reset);
  }

  // 自动生成演讲稿
  console.log(C.cyan + '\n▶ 生成演讲稿...\n' + C.reset);
  const speechPath = path.join(projectDir, 'speech.md');
  try {
    const script = await speech.generateSpeech(project, debateLog, { narrative, pages }, { apiOpts });
    speech.saveSpeech(script, speechPath);
    console.log(C.green + '  ✓ 演讲稿: ' + speechPath + C.reset);
  } catch (e) {
    console.log(C.yellow + '  ⚠ 演讲稿生成跳过: ' + e.message + C.reset);
  }

  console.log(C.dim + '\n所有文件: ' + projectDir + C.reset);
}

// ==================== PPT ====================

function saveHtml(html, outputPath) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, html, 'utf-8');
}

async function handlePpt(o) {
  const dir = o._[0];
  if (!dir) throw new Error('请指定项目目录: node ark.js ppt <目录>');
  const { project, debateLog, narrative, pages } = loadProject(dir);

  const theme = o.theme || '沙丘';
  const style = o.style || 'classic';

  const outputPath = o.output || path.join(dir, 'proposal.html');
  console.log(C.cyan + '▶ 生成PPT... 风格: ' + style + (style === 'classic' ? ' 主题: ' + theme : '') + C.reset);

  const html = style === 'guizang'
    ? await gz.generatePpt(project, debateLog, { narrative, pages })
    : (() => { if (!ppt.THEMES[theme]) throw new Error('无效主题: ' + theme + '，可选: ' + ppt.THEME_KEYS.join(', ')); return ppt.generatePpt(project, debateLog, { narrative, pages }, theme); })();
  (style === 'guizang' ? saveHtml : ppt.savePpt)(html, outputPath);
  console.log(C.green + '  ✓ PPT: ' + path.resolve(outputPath) + C.reset);
  console.log(C.dim + '  请在浏览器中打开查看' + C.reset);
}

// ==================== Speech ====================

async function handleSpeech(o) {
  const dir = o._[0];
  if (!dir) throw new Error('请指定项目目录: node ark.js speech <目录>');

  const { project, debateLog, narrative, pages } = loadProject(dir);
  const outputPath = o.output || path.join(dir, 'speech.md');

  const cfg = config.load();
  const apiOpts = {
    provider: cfg.provider || 'deepseek',
    apiUrl: cfg.apiUrl || api.PROVIDER_PRESETS[cfg.provider]?.url || 'https://api.deepseek.com',
    apiKey: cfg.apiKey,
    model: cfg.model || api.PROVIDER_PRESETS[cfg.provider]?.model || 'deepseek-chat',
  };

  const useAI = o['no-ai'] ? false : (cfg.apiKey ? true : false);

  console.log(C.magenta + '▶ 生成演讲稿...' + (useAI ? ' (AI润色)' : ' (模板)') + C.reset);

  const script = await speech.generateSpeech(project, debateLog, { narrative, pages }, {
    apiOpts: useAI ? apiOpts : null,
    useAI,
  });
  speech.saveSpeech(script, outputPath);

  console.log(C.green + '  ✓ 演讲稿: ' + path.resolve(outputPath) + C.reset);
  console.log(C.dim + '  可以直接用于提案演示' + C.reset);
}

// ==================== Render (grsai 生图) ====================

async function handleRender(o) {
  const dir = o._[0];
  if (!dir) throw new Error('请指定项目目录: node ark.js render <目录>');
  if (!process.env.GRSAI_API_KEY) {
    throw new Error('请设置 GRSAI_API_KEY 环境变量');
  }

  console.log(C.cyan + '▶ 生图渲染: ' + dir + C.reset);
  const result = await render.renderProject(dir, (msg) => {
    console.log(msg);
  });
  console.log(C.green + '\n✓ 渲染完成！' + C.reset);
  return result;
}

// ==================== All-in-one ====================

async function handleAll(o) {
  const { project, projectDir, apiOpts } = validateDebateOpts(o);
  const theme = o.theme || '沙丘';
  const useAISpeech = !o['no-ai-speech'];

  console.log('\n' + C.bold + '══════════════════════════════════════' + C.reset);
  console.log(C.bold + '  ARK Design · 一步生成完整提案' + C.reset);
  console.log(C.bold + '══════════════════════════════════════' + C.reset);
  console.log('  项目: ' + project.name + '  (' + (engine.SPACE_TYPES[project.spaceType]?.label || project.spaceType) + ')');
  if (project.city) console.log('  地点: ' + project.city);
  console.log('  预算: ¥' + engine.fmt(project.budget));
  console.log('  输出: ' + projectDir + '\n');

  fs.writeFileSync(path.join(projectDir, 'project.json'), JSON.stringify(project, null, 2), 'utf-8');

  // 辩论
  console.log(C.cyan + '【1/4】AI辩论引擎启动...\n' + C.reset);
  let termBuf = '';
  const { debateLog, narrative, pages } = await engine.runDebate(project, (chunk) => {
    process.stdout.write(chunk);
    termBuf += chunk;
  }, apiOpts);
  fs.writeFileSync(path.join(projectDir, 'debate.log'), termBuf, 'utf-8');

  // 叙事
  console.log(C.cyan + '\n【2/4】叙事大纲生成完成\n' + C.reset);

  // 保存结果
  const result = { project, debateLog, narrative, pages, generatedAt: new Date().toISOString() };
  fs.writeFileSync(path.join(projectDir, 'result.json'), JSON.stringify(result, null, 2), 'utf-8');

  // PPT
  const style = o.style || 'classic';
  console.log(C.cyan + '【3/4】生成PPT... 风格: ' + style + '\n' + C.reset);
  const pptPath = path.join(projectDir, 'proposal.html');
  try {
    const html = style === 'guizang'
      ? await gz.generatePpt(project, debateLog, { narrative, pages })
      : await ppt.generatePpt(project, debateLog, { narrative, pages }, theme);
    (style === 'guizang' ? saveHtml : ppt.savePpt)(html, pptPath);
    console.log(C.green + '  ✓ PPT: ' + pptPath + C.reset);
  } catch (e) {
    console.log(C.yellow + '  ⚠ PPT生成跳过: ' + e.message + C.reset);
  }

  // 演讲稿
  console.log(C.cyan + '\n【4/4】生成演讲稿...' + (useAISpeech ? ' (AI润色)' : ' (模板)') + C.reset);
  const speechPath = path.join(projectDir, 'speech.md');
  try {
    const script = await speech.generateSpeech(project, debateLog, { narrative, pages }, {
      apiOpts: useAISpeech ? apiOpts : null,
      useAI: useAISpeech,
    });
    speech.saveSpeech(script, speechPath);
    console.log(C.green + '  ✓ 演讲稿: ' + speechPath + C.reset);
  } catch (e) {
    console.log(C.yellow + '  ⚠ 演讲稿生成跳过: ' + e.message + C.reset);
  }

  console.log(C.green + '\n✓ 全部完成！' + C.reset);
  console.log(C.dim + '  项目文件: ' + projectDir + C.reset);
  console.log(C.dim + '  PPT: proposal.html  |  演讲稿: speech.md  |  数据: result.json' + C.reset);
}

// ==================== 公共工具 ====================

function validateDebateOpts(o) {
  if (!o.name) throw new Error('请指定项目名称: --name "项目名"');
  if (!o.type) throw new Error('请指定空间类型: --type residential/restaurant/hotel/exhibition/retail');
  const validTypes = ['residential','restaurant','hotel','exhibition','retail'];
  if (!validTypes.includes(o.type)) throw new Error('无效类型: ' + o.type);

  const project = {
    name: o.name,
    spaceType: o.type,
    budget: parseAmount(o.budget) || 0,
    city: o.city || '',
    regionFeatures: o.region || '',
    area: parseInt(o.area) || 0,
    brief: o.brief || '',
    clientTags: (o.tags || '').split(',').map(s=>s.trim()).filter(Boolean),
    userHabits: (o.habits || '').split(',').map(s=>s.trim()).filter(Boolean),
    fundingPhases: (o.funding || '').split(',').map(s=>parseAmount(s.trim())).filter(Boolean),
  };

  // Load profile from JSON file if --profile is specified
  if (o.profile && typeof o.profile === 'string') {
    try {
      const profilePath = path.resolve(o.profile);
      if (fs.existsSync(profilePath)) {
        const data = JSON.parse(fs.readFileSync(profilePath, 'utf-8'));
        // Support both raw profile dicts and project.json files (extract _profile)
        project._profile = data._profile || data;
      } else {
        console.warn('  ⚠ profile 文件不存在: ' + profilePath);
      }
    } catch (e) {
      console.warn('  ⚠ profile 文件解析失败: ' + e.message);
    }
  }

  const cfg = config.load();
  const apiOpts = {
    provider: cfg.provider || 'deepseek',
    apiUrl: cfg.apiUrl || api.PROVIDER_PRESETS[cfg.provider]?.url || 'https://api.deepseek.com',
    apiKey: cfg.apiKey,
    model: cfg.model || api.PROVIDER_PRESETS[cfg.provider]?.model || 'deepseek-chat',
  };
  if (!apiOpts.apiKey) throw new Error('请先配置 API Key: node ark.js config --key sk-xxxxx');

  const projectDir = path.resolve(o.output || path.join(__dirname, 'projects', project.name));
  fs.mkdirSync(projectDir, { recursive: true });

  return { project, projectDir, apiOpts };
}

function loadProject(dir) {
  const resultPath = path.resolve(dir, 'result.json');
  const projectPath = path.resolve(dir, 'project.json');

  if (!fs.existsSync(resultPath)) {
    throw new Error('未找到辩论结果: ' + resultPath + '\n请先运行: node ark.js debate ...');
  }
  const result = JSON.parse(fs.readFileSync(resultPath, 'utf-8'));
  const project = result.project || JSON.parse(fs.readFileSync(projectPath, 'utf-8'));
  return {
    project,
    debateLog: result.debateLog || [],
    narrative: result.narrative || '',
    pages: result.pages || [],
  };
}

// ==================== 工具 ====================

function parseAmount(str) {
  if (!str) return 0;
  const s = String(str).trim();
  if (s.endsWith('万')) return parseFloat(s) * 10000;
  return parseFloat(s.replace(/,/g, '')) || 0;
}

// ==================== 启动 ====================

main();
