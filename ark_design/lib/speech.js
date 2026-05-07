const fs = require('fs');
const path = require('path');
const api = require('./api.js');
const engine = require('./engine.js');
const promptLoader = require('./prompt-loader.js');
const { extractVariables } = require('./bridge.js');

const SECTION_NAMES = {
  1: '项目概况', 2: '概念推演', 3: '空间叙事',
  4: '效果图展示', 5: '灯光与材质', 6: '风险与预算', 7: '总结与下一步',
};

// ==================== 演讲稿生成 ====================

async function generateSpeech(project, debateLog, narratorOutput, opts = {}) {
  const typeLabel = engine.SPACE_TYPES[project.spaceType]?.label || '私宅';
  const apiOpts = opts.apiOpts || {};
  const narrative = narratorOutput?.narrative || '';
  const pages = narratorOutput?.pages || [];

  // Extract info from debate
  const visualContent = (debateLog.find(e => e.agent === 'visual-expert')?.content || '');
  const costContent = (debateLog.find(e => e.agent === 'cost-controller')?.content || '');
  const clientContent = (debateLog.find(e => e.agent === 'virtual-client')?.content || '');
  const constructionContent = (debateLog.find(e => e.agent === 'construction-mgr')?.content || '');
  const objections = extractObjections(clientContent);
  const budgetHighlights = extractBudgetHighlights(costContent);
  const constructionHighlights = extractConstructionHighlights(constructionContent);

  // AI generation with page context
  if (opts.useAI !== false && apiOpts.apiKey) {
    try {
      return await aiGenerateSpeech(project, debateLog, narrative, pages, objections, budgetHighlights, constructionHighlights, typeLabel, apiOpts);
    } catch (e) {
      // Fallback to template
      return templateSpeech(project, pages, narrative, objections, budgetHighlights, constructionHighlights, typeLabel);
    }
  }

  return templateSpeech(project, pages, narrative, objections, budgetHighlights, constructionHighlights, typeLabel);
}

// ==================== AI 生成演讲稿 ====================

async function aiGenerateSpeech(project, debateLog, narrative, pages, objections, budgetHighlights, constructionHighlights, typeLabel, apiOpts) {
  const systemPrompt = promptLoader.load('speech-system.md');

  const debateSummary = debateLog.map(e => {
    const label = engine.AGENT_LABELS[e.agent] || e.agent;
    return '【' + label + '】\n' + (e.content || '').slice(0, 800);
  }).join('\n\n---\n\n');

  // Build page reference summary
  const pageSummary = pages.length > 0 ? pages.map((p, i) =>
    `第${i + 1}页 [section ${p.section}] ${p.pageType}: ${p.title}`
  ).join('\n') : '';

  const userContent = promptLoader.load('speech-user.md', {
    PROJECT_NAME: project.name || '未命名',
    TYPE_LABEL: typeLabel,
    BUDGET: engine.fmt(project.budget || 0),
    CITY_LINE: project.city ? '地点：' + project.city : '',
    REGION_LINE: project.regionFeatures ? '地域特征：' + project.regionFeatures : '',
    CLIENT_TAGS: (project.clientTags || []).join('、'),
    USER_HABITS: (project.userHabits || []).join('、'),
    NARRATIVE: narrative || '（未生成）',
    PAGE_SUMMARY: pageSummary || '（无页面数据）',
    OBJECTIONS: objections.length ? objections.map((o, i) => `${i+1}. ${o}`).join('\n') : '（无明显反对意见）',
    BUDGET_HIGHLIGHTS: budgetHighlights.length ? budgetHighlights.join('\n') : '（待补充）',
    CONSTRUCTION_HIGHLIGHTS: constructionHighlights.length ? constructionHighlights.join('\n') : '（待补充）',
    DEBATE_SUMMARY: debateSummary,
  });

  // Override speech-user.md vars to include pages
  const finalContent = userContent
    .replace('{{PAGE_SUMMARY}}', pageSummary || '（无页面数据）');

  let fullText = '';
  await api.stream(
    [{ role: 'system', content: systemPrompt }, { role: 'user', content: finalContent }],
    (chunk) => { fullText += chunk; },
    { ...apiOpts, temperature: 0.7, maxTokens: 8192 }
  );
  return fullText;
}

// ==================== 模板生成演讲稿（包含页面引用） ====================

function templateSpeech(project, pages, narrative, objections, budgetHighlights, constructionHighlights, typeLabel) {
  const pf = extractVariables(project._profile);
  const parts = [];

  // Build per-section page index
  const sectionPages = {};
  if (pages.length > 0) {
    for (let i = 0; i < pages.length; i++) {
      const sec = pages[i].section;
      if (!sectionPages[sec]) sectionPages[sec] = [];
      sectionPages[sec].push(i + 1);
    }
  }

  function pg(sec) {
    const nums = sectionPages[sec];
    return nums ? `（请翻至第 ${nums.join('、')} 页）` : '';
  }

  function q(s) { return '"' + s + '"'; }

  parts.push(
    '# ' + (project.name || '本案') + ' · 提案演讲稿\n',
    '> 总时长约 10-12 分钟 | 语速建议：中速偏慢，关键数据稍作停顿\n',
    '---\n',
    '## 一、开场白（约30秒）\n',
    '**【演讲要点】** 快速建立信任，表明你理解他的项目\n',
    q((project.name ? project.name + '的' : '') + '各位好。今天我们带来的不是一套"效果图"，而是一套完整的解决方案。') + '\n\n' +
    '在接手这个项目之后，我们团队做了三件事：\n' +
    '**第一**，深度分析了项目的条件和限制；\n' +
    '**第二**，内部做了四轮不同视角的专业博弈——审美、施工、成本、运营；\n' +
    '**第三**，把吵出来的结果，变成了一套"能做出来、花得值、效果好"的方案。\n\n' +
    q('接下来大约十分钟，我会带大家走一遍我们的思考过程。') + '\n' +
    pg(1) + '\n',
    '---\n',
    '## 二、项目概况与设计背景（约1分钟）\n',
    '**【演讲要点】** 简述项目基本信息和核心诉求\n' + pg(1),
    project.brief ? '\n' + q(project.brief) + '\n\n' : '',
    q('这个项目的关键挑战在于——') + '\n',
    project.regionFeatures
      ? q(project.regionFeatures + '——这是我们做方案时一直在脑子里绷着的一根弦。') + '\n'
      : q('如何在有限的预算内，实现最大的空间价值。') + '\n',
    '**【过渡】** ' + q('那理解了问题之后，我们是怎么破题的？') + '\n' + pg(2),
    '---\n',
    '## 三、概念推演 · 设计逻辑（约2分钟）\n',
    '**【演讲要点】** 讲设计逻辑而非设计本身，解释"为什么这样做"\n' + pg(2),
    q('我们的设计逻辑其实很简单：每一个空间决策，背后都有一个明确的理由。') + '\n\n',
    q('我重点讲两个核心决策：空间组织逻辑和材质选择逻辑。') + '\n\n',
    budgetHighlights.length
      ? budgetHighlights.map(function(h) { return '*（设计提示：可以强调「' + h + '」这一价值点）*'; }).join('\n') + '\n'
      : '',
    '**【过渡】** ' + q('有了设计方向之后，我们来看具体的空间叙事。') + '\n' + pg(3),
    '---\n',
    '## 四、空间叙事 · 体验设计（约2分钟）\n',
    '**【演讲要点】** 带客户走过每个核心空间，描述体验场景\n' + pg(3),
    q('这个空间最核心的体验逻辑是这样的——') + '\n\n',
    q('我们不只是设计一个个房间，而是设计一个完整的情感动线。从进门的那一刻开始，到离开的最后一秒，每个节点都有它存在的理由。') + '\n\n',
    constructionHighlights.length
      ? q('在施工端，我们特别关注了几个节点：') + '\n' + constructionHighlights.map(h => '  • ' + h).join('\n') + '\n\n'
      : '',
    objections.length
      ? '\n**【客户可能会问】** \n' + objections.map(o => '• ' + q(o)).join('\n') + '\n'
      : '',
    '**【过渡】** ' + q('那这些空间最终呈现出来是什么样？我们来看效果图。') + '\n' + pg(4),
    '---\n',
    '## 五、效果图与灯光系统（约1.5分钟）\n',
    '**【演讲要点】** 展示效果图时不要说"好看"，要说"这个设计解决了什么问题"\n' + pg(4),
    (pages.length > 0
      ? q('请大家看这几页效果图——注意，这不是最终效果，而是设计意图的呈现。') + '\n\n'
      : ''),
    q('我们特别关注灯光系统的设计。好的灯光不是"亮"，而是"该亮的地方亮，该暗的地方暗"。') + '\n' + pg(5),
    q('不同的使用场景对应不同的灯光模式——这一点我们在方案里有详细的规划。') + '\n',
    '**【过渡】** ' + q('方案聊完了，我们聊聊大家最关心的问题——预算。') + '\n' + pg(6),
    '---\n',
    '## 六、风险控制与预算分配（约2分钟）\n',
    '**【演讲要点】** 把"花多少钱"翻译成"获得多少价值"\n' + pg(6),
    project.budget
      ? q('整个项目的总投资是 **¥' + engine.fmt(project.budget) + '**。') + '\n\n'
      : '',
    q('但我希望各位把这个数字看成投资，而不是花费。因为这笔钱买的不是一堆材料，而是：') + '\n\n' +
    '"- **一个经过论证的方案**——不是拍脑袋想的"\n' +
    '"- **一份精确的执行蓝图**——不会在施工过程中反复改"\n' +
    '"- **一套风险排查的结果**——不会做到一半发现做不下去"\n' +
    (project.spaceType !== 'residential'
      ? '"- **一个可预期的投资回报**——每一平米都在创造价值"\n'
      : '"- **一个未来多年的生活空间**——摊到每天，成本远比你想的低"\n') + '\n',
    q('具体来说，我们的资金是这样分配的——（简述预算分配逻辑）') + '\n\n',
    q('在你看得见的地方，我们用了最好的；在你看不见但重要的地方，我们也坚持了标准；在可以后期升级的地方，我们做了留白。') + '\n\n',
    '**【客户可能打断】** 如果客户质疑某项费用，回答："这项费用的背后是XX和XX两个价值点，如果这里降级，影响的是XX和XX。我们可以给您看A/B方案的对比。"\n',
    '**【过渡】** ' + q('以上就是整个方案的核心内容。最后，我想用一句话来总结。') + '\n' + pg(7),
    '---\n',
    '## 七、总结与下一步行动（约30秒）\n',
    '**【演讲要点】** 强有力的收尾 + 明确的行动号召\n' + pg(7),
    q('最后，我想用一句话总结我们的提案：') + '\n\n',
    (function() {
      switch (typeLabel) {
        case '私宅': return '**设计不仅是视觉的博弈，更是对生活琐碎的温柔回击。**';
        case '餐饮': return '**好的设计不是最贵的，而是每一平米都在帮你赚钱。**';
        case '酒店民宿': return '**好的民宿设计，是让客人想订房、想发朋友圈、想再来。**';
        case '展厅': return '**好的展厅设计，是让参观者走出去之后还能记住。**';
        default: return '**好的门店设计，是让路过的人想进来，进来的人想买单。**';
      }
    })() + '\n\n',
    q('我们准备好了详细的方案文本和施工图纸。如果今天的方向没问题，下一步我们可以——') + '\n\n' +
    '**第一**，确认方案方向，进入深化设计阶段；\n' +
    '**第二**，同步启动材料选型和供应商对接；\n' +
    '**第三**，根据您的资金节奏，制定分期施工计划。\n\n' +
    q('各位有什么问题，我们随时可以深入聊。') + '\n',
    '---\n',
    '## 附录：反对意见应答手册\n',
    objections.length
      ? objections.map(function(o, i) {
          return '### 场景 ' + (i+1) + '：' + o + '\n\n' +
            '**应对策略：**\n' +
            '- 承认问题的合理性（"您说得对，这个问题我们内部也讨论过……"）\n' +
            '- 给出专业判断（"最后我们选择这个方案的原因是……"）\n' +
            '- 提供替代选项（"如果您实在不放心，我们可以做A/B方案对比"）\n\n';
        }).join('')
      : '（本项目中未识别到明显的反对意见场景，可根据实际提案情况补充）\n',
    '---\n',
    '\n*本演讲稿由 ' + pf.COMPANY_NAME + ' 自动生成 · 建议提案前通读一遍，标注重点数据*\n'
  );

  return parts.join('');
}

// ==================== 辅助函数 ====================

function extractObjections(clientContent) {
  if (!clientContent) return [];
  return clientContent.split('\n')
    .filter(l => l.includes('？') || l.includes('?') || l.includes('质疑') || l.includes('问题'))
    .filter(l => l.trim().length > 5)
    .map(l => l.replace(/^[\d\s.、-]+/, '').trim())
    .slice(0, 5);
}

function extractBudgetHighlights(costContent) {
  if (!costContent) return [];
  const highlights = [];
  const lines = costContent.split('\n');
  for (const line of lines) {
    const t = line.trim();
    if (t.includes('核心') || t.includes('保级') || t.includes('价值') || t.includes('投资') || t.includes('回收') || t.includes('回报')) {
      highlights.push(t);
    }
  }
  return highlights.slice(0, 5);
}

function extractConstructionHighlights(constructionContent) {
  if (!constructionContent) return [];
  const highlights = [];
  const lines = constructionContent.split('\n');
  for (const line of lines) {
    const t = line.trim();
    if (t.includes('收口') || t.includes('防水') || t.includes('隔音') || t.includes('工艺') || t.includes('节点')) {
      highlights.push(t);
    }
  }
  return highlights.slice(0, 5);
}

// ==================== 保存 ====================

function saveSpeech(text, outputPath) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, text, 'utf-8');
}

module.exports = {
  generateSpeech,
  saveSpeech,
};
