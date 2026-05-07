const api = require('./api.js');
const promptLoader = require('./prompt-loader.js');
const { applyProfile, extractVariables } = require('./bridge.js');

// ==================== Constants ====================
const DEBATE_DELAY_MS = 300;
const AGENT_TRUNCATE = 1200;

// ==================== 项目类型映射 ====================
const SPACE_TYPES = {
  residential: { label: '私宅', icon: '🏠' },
  restaurant:  { label: '餐饮', icon: '🍽️' },
  hotel:       { label: '酒店民宿', icon: '🏨' },
  exhibition:  { label: '展厅', icon: '🎨' },
  retail:      { label: '服务门店', icon: '🏪' },
};

// ==================== Agent Prompts ====================

function visualExpertPrompt(project) {
  const type = project.spaceType || 'residential';
  const parts = [promptLoader.load('visual-expert.md')];
  parts.push('', promptLoader.load(`visual-expert-${type}.md`));
  if (project.city || project.regionFeatures) {
    parts.push('', promptLoader.load('region-rules.md', {
      CITY: project.city || '',
      REGION_FEATURES: project.regionFeatures || '',
    }));
  }
  let prompt = parts.join('\n');
  prompt = applyProfile(prompt, project._profile);
  return prompt;
}

function constructionMgrPrompt(project) {
  const type = project.spaceType || 'residential';
  const parts = [promptLoader.load('construction-mgr.md')];
  parts.push('', promptLoader.load('construction-mgr-' + type + '.md'));
  if (project.regionFeatures) {
    parts.push('', promptLoader.load('construction-mgr-region.md'));
  }
  let prompt = parts.join('\n');
  prompt = applyProfile(prompt, project._profile);
  return prompt;
}

function costControllerPrompt(project) {
  const type = project.spaceType || 'residential';
  const parts = [promptLoader.load('cost-controller.md')];
  parts.push('', promptLoader.load('cost-controller-' + type + '.md'));

  // 资金节奏
  if (project.fundingPhases?.length) {
    const phases = project.fundingPhases.map((v, i) => `第${i+1}期：¥${fmt(v)}`).join('\n');
    parts.push('', promptLoader.load('cost-controller-funding.md', {
      FUNDING_PHASES: phases,
    }));
  }

  // 地域成本
  if (project.city) {
    const tier1Cities = ['北京', '上海', '广州', '深圳', '杭州'];
    const isTier1 = tier1Cities.some(c => project.city.includes(c));
    const adjustment = isTier1
      ? '- 一线城市：人工成本上浮20-30%，但工种齐全'
      : '- 非一线城市：人工相对低，但要避免复杂工艺';
    parts.push('', promptLoader.load('cost-controller-region.md', { COST_ADJUSTMENT: adjustment }));
  }

  // 商业附加
  if (type !== 'residential') {
    parts.push('', promptLoader.load('cost-controller-commercial.md'));
  }

  let prompt = parts.join('\n');
  prompt = applyProfile(prompt, project._profile);
  return prompt;
}

function virtualClientPrompt(project) {
  const isCommercial = project.spaceType && project.spaceType !== 'residential';
  let prompt = promptLoader.load(isCommercial ? 'virtual-client-commercial.md' : 'virtual-client-residential.md');
  prompt = applyProfile(prompt, project._profile);
  return prompt;
}

function narratorPrompt(project) {
  const type = project.spaceType || 'residential';
  let prompt = promptLoader.load('narrator-' + type + '.md');
  prompt = applyProfile(prompt, project._profile);
  return prompt;
}

// ==================== 辩论步骤 ====================

function getDebateSteps(spaceType) {
  const steps = {
    residential: ['visual-expert', 'construction-mgr', 'cost-controller', 'virtual-client'],
    restaurant:  ['construction-mgr', 'cost-controller', 'visual-expert', 'virtual-client'],
    hotel:       ['visual-expert', 'construction-mgr', 'cost-controller', 'virtual-client'],
    exhibition:  ['visual-expert', 'cost-controller', 'construction-mgr', 'virtual-client'],
    retail:      ['cost-controller', 'visual-expert', 'construction-mgr', 'virtual-client'],
  };
  return steps[spaceType] || steps.residential;
}

const AGENT_LABELS = {
  'visual-expert': '审美专家',
  'construction-mgr': '硬核执行官',
  'cost-controller': '精算专家',
  'virtual-client': '虚拟客户',
  'narrator': '叙事架构师',
};

// ==================== Profile Profile Context ====================

function profileContext(project) {
  const pf = project._profile;
  if (!pf) return '';
  const vars = extractVariables(pf);
  const lines = [];
  if (vars.COMPANY_NAME) lines.push('事务所：' + vars.COMPANY_NAME);
  if (vars.DESIGN_STYLE) lines.push('设计风格偏好：' + vars.DESIGN_STYLE);
  if (vars.PRICE_RANGE) lines.push('价格定位：' + vars.PRICE_RANGE);
  if (vars.TARGET_CLIENT) lines.push('目标客群：' + vars.TARGET_CLIENT);
  if (vars.CITY) lines.push('所在城市：' + vars.CITY);
  return lines.length > 0 ? '## 事务所信息\n' + lines.join('\n') + '\n\n' : '';
}

// ==================== 运行辩论 ====================

async function runAgent(agentType, project, previousLog, onChunk, apiOpts) {
  const label = AGENT_LABELS[agentType] || agentType;
  const typeLabel = SPACE_TYPES[project.spaceType]?.label || '私宅';

  let systemPrompt;
  let userContent;

  switch (agentType) {
    case 'visual-expert': {
      systemPrompt = visualExpertPrompt(project);
      userContent = [
        '## 项目信息',
        '名称：' + (project.name || '未命名'),
        '类型：' + typeLabel,
        '预算：¥' + fmt(project.budget || 0),
        project.city ? '地点：' + project.city : '',
        project.regionFeatures ? '地域：' + project.regionFeatures : '',
        '客户标签：' + (project.clientTags || []).join('、'),
        '习惯：' + (project.userHabits || []).join('、'),
        project.brief ? '简介：' + project.brief : '',
        '',
        profileContext(project),
        '请根据项目类型和地域特征，输出完整的空间设计方案。',
        '如果你的事务所有特定的设计风格倾向，请在方案中体现这种设计基因。',
        '包含：情绪关键词、材质搭配方案、光影策略、空间布局建议。',
        '如果已有辩论记录，请参考前面专家的意见。',
      ].filter(Boolean).join('\n');
      break;
    }
    case 'construction-mgr': {
      const visualOutput = (previousLog.find(e => e.agent === 'visual-expert')?.content || '').slice(0, AGENT_TRUNCATE);
      systemPrompt = constructionMgrPrompt(project);
      userContent = [
        '## 项目信息',
        '名称：' + (project.name || '未命名'),
        '类型：' + typeLabel,
        project.city ? '地点：' + project.city : '',
        project.regionFeatures ? '地域：' + project.regionFeatures : '',
        '',
        '## 审美专家方案',
        visualOutput,
        '',
        '请审核上述方案的施工可行性，输出红/黄/绿评级和风险评估。',
        '特别注意地域施工条件限制。',
      ].filter(Boolean).join('\n');
      break;
    }
    case 'cost-controller': {
      const visualOutput = (previousLog.find(e => e.agent === 'visual-expert')?.content || '').slice(0, AGENT_TRUNCATE);
      const realistOutput = (previousLog.find(e => e.agent === 'construction-mgr')?.content || '').slice(0, AGENT_TRUNCATE);
      systemPrompt = costControllerPrompt(project);
      userContent = [
        '## 项目信息',
        '名称：' + (project.name || '未命名'),
        '类型：' + typeLabel,
        '预算：¥' + fmt(project.budget || 0),
        project.city ? '地点：' + project.city : '',
        project.regionFeatures ? '地域：' + project.regionFeatures : '',
        '客户标签：' + (project.clientTags || []).join('、'),
        '',
        profileContext(project),
        '## 审美专家方案',
        visualOutput,
        '',
        '## 施工经理风险清单',
        realistOutput,
        '',
        ...(project.fundingPhases?.length ? ['',
          '## 资金分期计划',
          ...project.fundingPhases.map((v, i) => `第${i+1}期：¥${fmt(v)}`),
          '请根据资金到位节奏输出分期投入计划。',
        ] : []),
        '',
        ...(project.spaceType !== 'residential' ? [
          '请同时计算投资回收期和全生命周期成本。',
        ] : []),
      ].filter(Boolean).join('\n');
      break;
    }
    case 'virtual-client': {
      const visualOutput = (previousLog.find(e => e.agent === 'visual-expert')?.content || '').slice(0, AGENT_TRUNCATE);
      const costOutput = (previousLog.find(e => e.agent === 'cost-controller')?.content || '').slice(0, AGENT_TRUNCATE);
      systemPrompt = virtualClientPrompt(project);
      userContent = [
        '## 项目信息',
        '名称：' + (project.name || '未命名'),
        '类型：' + typeLabel,
        project.city ? '地点：' + project.city : '',
        project.regionFeatures ? '地域特征：' + project.regionFeatures : '',
        '客户标签：' + (project.clientTags || []).join('、'),
        '习惯：' + (project.userHabits || []).join('、'),
        '',
        profileContext(project),
        '## 审美专家方案',
        visualOutput,
        '',
        '## 预算方案',
        costOutput,
        '',
        project.spaceType === 'residential'
          ? '请以业主身份，对以上方案发起场景化压力测试，提出3-5个最刁钻的生活逻辑问题。'
          : '请以商业客户身份，对以上方案发起经营逻辑压力测试，提出3-5个最尖锐的运营和投资问题。',
      ].filter(Boolean).join('\n');
      break;
    }
  }

  onChunk('\n  ' + '━'.repeat(50) + '\n');
  onChunk(`  【${label}】开始...\n`);
  onChunk('  ' + '━'.repeat(50) + '\n\n');

  const startTime = Date.now();
  const fullText = await api.stream(
    [{ role: 'system', content: systemPrompt }, { role: 'user', content: userContent }],
    (chunk) => { onChunk(chunk); },
    apiOpts
  );
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

  onChunk('\n\n  ─── ["' + label + '" 完成，耗时 ' + elapsed + 's] ───\n\n');

  return fullText;
}

async function generateNarrative(project, debateLog, onChunk, apiOpts) {
  const label = AGENT_LABELS.narrator;
  onChunk('\n  ' + '━'.repeat(50) + '\n');
  onChunk(`  【${label}】生成提案页面定义...\n`);
  onChunk('  ' + '━'.repeat(50) + '\n\n');

  const debateSummary = debateLog.map(e => {
    const label = AGENT_LABELS[e.agent] || e.agent;
    return '【' + label + '】\n' + (e.content || '').slice(0, AGENT_TRUNCATE);
  }).join('\n\n---\n\n');

  const typeLabel = SPACE_TYPES[project.spaceType]?.label || '私宅';
  const systemPrompt = narratorPrompt(project);
  const userContent = [
    '## 项目：' + (project.name || '未命名'),
    '## 类型：' + typeLabel,
    project.city ? '## 地点：' + project.city : '',
    project.regionFeatures ? '## 地域特征：' + project.regionFeatures : '',
    '',
    '## 博弈记录摘要',
    debateSummary,
    '',
    '请严格按照系统指令中的JSON格式输出完整的页面定义数组。',
    '确保 output 是包裹在 ```json 代码块中的合法 JSON 数组。',
    '不要输出任何多余的说明文字。',
    '每页必须包含 id, section, pageType, title, liNote 字段。',
  ].filter(Boolean).join('\n');

  const startTime = Date.now();
  const rawText = await api.stream(
    [{ role: 'system', content: systemPrompt }, { role: 'user', content: userContent }],
    (chunk) => { onChunk(chunk); },
    apiOpts
  );
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  onChunk('\n\n  ─── ["' + label + '" 完成，耗时 ' + elapsed + 's] ───\n\n');

  // Parse JSON from response
  let pages = parseNarrativeJSON(rawText);
  if (pages.length === 0) {
    onChunk('  ⚠ JSON解析失败，原始输出将保存为文本\n');
  }

  // Enforce page count limits
  const clamped = enforcePageCount(pages, project.spaceType);
  if (clamped.adjustment) {
    onChunk('  ' + clamped.adjustment + '\n');
  }

  return { narrative: rawText, pages: clamped.pages };
}

function parseNarrativeJSON(rawText) {
  // Extract JSON from markdown code block ```json ... ```
  const jsonMatch = rawText.match(/```(?:json)?\s*\n?([\s\S]*?)```/);
  const jsonStr = jsonMatch ? jsonMatch[1].trim() : rawText.trim();

  try {
    const parsed = JSON.parse(jsonStr);
    const pages = Array.isArray(parsed) ? parsed : (parsed.pages || []);
    // Validate each page has required fields
    return pages.filter(p => {
      if (!p.id || !p.section || !p.pageType || !p.title) {
        console.warn('  ⚠ 跳过无效页 (缺少必填字段):', p.id || 'unknown');
        return false;
      }
      return true;
    });
  } catch (e) {
    console.warn('  ⚠ JSON解析失败: ' + e.message.substring(0, 80));
    return [];
  }
}

function enforcePageCount(pages, spaceType) {
  const limits = {
    residential: { min: 35, max: 50 },
    restaurant:  { min: 40, max: 55 },
    hotel:       { min: 45, max: 62 },
    exhibition:  { min: 35, max: 50 },
    retail:      { min: 35, max: 45 },
  };
  const lim = limits[spaceType] || { min: 35, max: 50 };
  const result = { pages: [...pages], adjustment: null };

  if (result.pages.length > lim.max) {
    // Remove lowest-priority sections (5: lighting, 7: summary) first
    const keep = result.pages.filter(p => p.section !== 5 && p.section !== 7);
    const excess = result.pages.length - lim.max;
    result.pages = keep.slice(0, keep.length - Math.min(excess, keep.length));
    if (result.pages.length < 10) result.pages = keep.slice(0, lim.max / 2);
    result.adjustment = '超出上限' + lim.max + '页，裁剪至' + result.pages.length + '页';
  } else if (result.pages.length < lim.min && result.pages.length > 0) {
    // Pad with copies of key pages
    const fillPages = result.pages.filter(p =>
      p.pageType === 'deepInsight' || p.pageType === 'spaceNarrative' || p.pageType === 'coreRendering'
    );
    if (fillPages.length > 0) {
      while (result.pages.length < lim.min) {
        const src = fillPages[(result.pages.length - fillPages.length) % fillPages.length];
        result.pages.push({ ...src, id: src.id + '-dup' });
      }
      result.adjustment = '不足下限' + lim.min + '页，补至' + result.pages.length + '页';
    }
  }

  return result;
}

async function runDebate(project, onChunk, apiOpts) {
  const steps = getDebateSteps(project.spaceType);
  const debateLog = [];

  const brand = (project._profile?.company_name || 'ARK Design');
  onChunk('\n╔' + '═'.repeat(48) + '╗\n');
  onChunk(`║  ${brand} · 设计辩论引擎启动          ║\n`);
  onChunk(`║  项目：${(project.name || '').padEnd(30)}║\n`);
  onChunk(`║  类型：${(SPACE_TYPES[project.spaceType]?.label || '').padEnd(30)}║\n`);
  if (project.city) onChunk(`║  地点：${project.city.padEnd(30)}║\n`);
  onChunk('╚' + '═'.repeat(48) + '╝\n\n');

  // 运行各agent
  for (const agentType of steps) {
    onChunk(`▶ 第${steps.indexOf(agentType) + 1}步：${AGENT_LABELS[agentType]}...\n`);
    const content = await runAgent(agentType, project, debateLog, onChunk, apiOpts);
    debateLog.push({ agent: agentType, content, timestamp: Date.now() });
    // 短暂停顿避免API限流
    await new Promise(r => setTimeout(r, DEBATE_DELAY_MS));
  }

  // 生成叙事
  onChunk('▶ 第5步：叙事架构师生成提案...\n');
  const { narrative, pages } = await generateNarrative(project, debateLog, onChunk, apiOpts);

  return { debateLog, narrative, pages };
}

function fmt(n) {
  return Number(n || 0).toLocaleString('zh-CN');
}

module.exports = {
  runDebate,
  runAgent,
  generateNarrative,
  parseNarrativeJSON,
  enforcePageCount,
  SPACE_TYPES,
  AGENT_LABELS,
  fmt,
};
