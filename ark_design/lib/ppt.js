const fs = require('fs');
const path = require('path');
const { smartMatchImage } = require('./imageSearch');
const { extractVariables } = require('./bridge.js');

let _pf = { COMPANY_NAME: 'ARK Design', DESIGNER_SHORT: '设计师' };

// ==================== 主题色预设 ====================
const THEMES = {
  墨水经典: {
    ink: '#0a0a0b', inkRGB: '10,10,11',
    paper: '#f1efea', paperRGB: '241,239,234',
    paperTint: '#e8e5de', inkTint: '#18181a',
    label: '墨水经典',
  },
  靛蓝瓷: {
    ink: '#0a1f3d', inkRGB: '10,31,61',
    paper: '#f1f3f5', paperRGB: '241,243,245',
    paperTint: '#e4e8ec', inkTint: '#152a4a',
    label: '靛蓝瓷',
  },
  森林墨: {
    ink: '#1a2e1f', inkRGB: '26,46,31',
    paper: '#f5f1e8', paperRGB: '245,241,232',
    paperTint: '#ece7da', inkTint: '#253d2c',
    label: '森林墨',
  },
  牛皮纸: {
    ink: '#2a1e13', inkRGB: '42,30,19',
    paper: '#eedfc7', paperRGB: '238,223,199',
    paperTint: '#e0d0b6', inkTint: '#3a2a1d',
    label: '牛皮纸',
  },
  沙丘: {
    ink: '#1f1a14', inkRGB: '31,26,20',
    paper: '#f0e6d2', paperRGB: '240,230,210',
    paperTint: '#e3d7bf', inkTint: '#2d2620',
    label: '沙丘',
  },
};

const THEME_KEYS = Object.keys(THEMES);

const SECTION_NAMES = {
  1: '项目概况', 2: '概念推演', 3: '空间叙事',
  4: '效果图', 5: '灯光材质', 6: '风险预算', 7: '总结后续',
};

const PAGE_KICKERS = {
  cover: 'Cover', valueDirectory: 'Contents', deepInsight: 'Deep Insight',
  logicBoard: 'Material Logic', visualNodes: 'Visual Nodes',
  extremeScenario: 'Extreme Scenario', spaceNarrative: 'Space Narrative',
  coreRendering: 'Core Rendering', lightingScenario: 'Lighting',
  riskItem: 'Risk Assessment', investmentModel: 'Investment',
  nextStep: 'Next Steps', closing: 'Closing',
};

// ==================== 模板路径 ====================
const TEMPLATE_PATH = path.join(__dirname, 'template.html');

// ==================== 主生成器 ====================

async function generatePpt(project, debateLog, narratorOutput, themeName) {
  const theme = THEMES[themeName] || THEMES['沙丘'];
  const pages = narratorOutput.pages || [];
  const narrative = narratorOutput.narrative || '';
  _pf = extractVariables(project._profile);

  let template = fs.readFileSync(TEMPLATE_PATH, 'utf-8');

  // 替换主题色
  const themeReplacements = [
    ['--ink:#0a0a0b;', `--ink:${theme.ink};`],
    ['--ink-rgb:10,10,11;', `--ink-rgb:${theme.inkRGB};`],
    ['--paper:#f1efea;', `--paper:${theme.paper};`],
    ['--paper-rgb:241,239,234;', `--paper-rgb:${theme.paperRGB};`],
    ['--paper-tint:#e8e5de;', `--paper-tint:${theme.paperTint};`],
    ['--ink-tint:#18181a;', `--ink-tint:${theme.inkTint};`],
  ];
  for (const [from, to] of themeReplacements) {
    template = template.replace(from, to);
  }

  // 替换标题
  const title = (project.name || '设计提案') + ' · ' + _pf.COMPANY_NAME;
  template = template.replace('[必填] 替换为 PPT 标题 · Deck Title', title);

  // 生成幻灯片（现在是异步的）
  const slides = await buildSlides(project, pages, narrative);
  template = template.replace('<!-- SLIDES_HERE -->', slides.join('\n\n'));

  return template;
}

// ==================== 幻灯片构建 ====================

async function buildSlides(project, pages, narrative) {
  // If pages available, use 13 renderers; otherwise fallback to old method
  if (pages && pages.length > 0) {
    return await renderPages(pages, project);
  }
  // Backward compatibility: parse markdown narrative
  return fallbackSlides(project, narrative);
}

// ==================== 13 Renderers ====================

async function renderPages(pages, project) {
  const total = pages.length;
  const pagePromises = pages.map(async (page, i) => {
    const renderer = PAGE_RENDERERS[page.pageType];
    if (!renderer) return renderUnknown(page, i, total, project);

    // 异步渲染页面
    const html = await renderer(page, i, total, project);

    // Inject liNote if present
    const noteHtml = page.liNote ? renderLiNote(page.liNote) : '';
    if (noteHtml && html.includes('</section>')) {
      return html.replace('</section>', noteHtml + '\n    </section>');
    }
    return html;
  });

  // 等待所有页面渲染完成
  return Promise.all(pagePromises);
}

const PAGE_RENDERERS = {
  // ======== cover: 封面 ========
  async cover(page, i, total, project) {
    // 页面上下文，用于智能配图
    const pageContext = {
      pageTitle: page.title,
      sectionName: '封面',
      keywords: [project.name, project.type, '封面'],
      spaceType: project.spaceType
    };

    const imagesHtml = await renderImages(page.images, 'hero', '70vh', null, pageContext);

    return slide(page, i, total, 'hero', `
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;max-width:80%">
        <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.cover)}</div>
        <h1 class="h-hero" data-anim>${escHtml(page.title)}</h1>
        <div style="height:1.2vh"></div>
        ${page.blocks ? renderBlocks(page.blocks, 'meta-row', 'margin-top:2vh') : ''}
        ${imagesHtml}
      </div>
    `, project);
  },

  // ======== valueDirectory: 目录导航 ========
  valueDirectory(page, i, total, project) {
    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.valueDirectory)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div class="grid-3" data-anim style="align-content:start;padding-top:2vh">
        ${page.blocks ? renderBlocks(page.blocks, 'pillar') : ''}
      </div>
    `, project);
  },

  // ======== deepInsight: 深层洞察 ========
  async deepInsight(page, i, total, project) {
    // 页面上下文，用于智能配图
    const pageContext = {
      pageTitle: page.title,
      sectionName: '项目分析',
      keywords: [page.title, '分析', '需求'],
      spaceType: project.spaceType
    };

    const imagesHtml = await renderImages(page.images, 'content', '28vh', null, pageContext);

    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.deepInsight)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div class="split" data-anim style="align-items:start;padding-top:1vh;gap:3vw">
        <!-- 左文 -->
        <div class="col" style="width:60%">
          <div class="grid-3" style="align-content:start">
            ${page.blocks ? renderBlocks(page.blocks, 'pillar') : ''}
          </div>
        </div>
        <!-- 右图 -->
        <div class="col" style="width:40%;display:grid;grid-template-columns:1fr;gap:1.6vh;">
          ${imagesHtml}
        </div>
      </div>
    `, project);
  },

  // ======== logicBoard: 材质对比表 ========
  async logicBoard(page, i, total, project) {
    // 页面上下文，用于智能配图
    const pageContext = {
      pageTitle: page.title,
      sectionName: '材质方案',
      keywords: [page.title, '材质', '材料', '样板'],
      spaceType: project.spaceType
    };

    const imagesHtml = await renderImages(page.images, 'micro', '20vh', null, pageContext);

    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.logicBoard)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div class="split-55" data-anim style="align-items:start">
        <!-- 左文 -->
        <div class="col">
          ${page.blocks ? renderBlocks(page.blocks, 'rowline') : ''}
        </div>
        <!-- 右图 -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(150px, 1fr));gap:1.5vh;">
          ${imagesHtml}
        </div>
      </div>
    `, project);
  },

  // ======== visualNodes: 核心区对比 ========
  async visualNodes(page, i, total, project) {
    const leftBlock = page.blocks?.[0] ? pillarHtml(page.blocks[0]) : '';
    const rightBlock = page.blocks?.[1] ? pillarHtml(page.blocks[1]) : '';

    // 页面上下文，用于智能配图
    const pageContext = {
      pageTitle: page.title,
      sectionName: '方案对比',
      keywords: [page.title, '方案', '对比', '平面'],
      spaceType: project.spaceType
    };

    const leftImage = page.images?.slice(0, 1)
      ? await renderImages(page.images?.slice(0, 1), 'content', '28vh', null, pageContext)
      : '';

    const rightImage = page.images?.slice(1, 2)
      ? await renderImages(page.images?.slice(1, 2), 'content', '28vh', null, pageContext)
      : '';

    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.visualNodes)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div data-anim class="split" style="align-items:stretch">
        <div data-anim="left">${leftBlock}${leftImage}</div>
        <div class="v rule" style="height:auto;margin:0 1vw"></div>
        <div data-anim="right">${rightBlock}${rightImage}</div>
      </div>
    `, project);
  },

  // ======== extremeScenario: 极限场景 ========
  async extremeScenario(page, i, total, project) {
    // 页面上下文，用于智能配图
    const pageContext = {
      pageTitle: page.title,
      sectionName: '场景设计',
      keywords: [page.title, '场景', '设计'],
      spaceType: project.spaceType
    };

    const imagesHtml = await renderImages(page.images, 'hero', '32vh', null, pageContext);

    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.extremeScenario)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      ${imagesHtml}
      <div data-animate="pipeline" data-anim class="pipeline-section" style="margin-top:1vh">
        <div class="pipeline" data-cols="${Math.min(page.blocks?.length || 3, 6)}">
          ${page.blocks ? page.blocks.map((b, bi) => `
            <div class="step" data-anim="step">
              <div class="step-nb">${String(bi + 1).padStart(2, '0')}</div>
              <div class="step-title">${escHtml(b.title || '')}</div>
              <div class="step-desc">${escHtml(b.desc || '')}</div>
            </div>
          `).join('\n          ') : ''}
        </div>
      </div>
    `, project);
  },

  // ======== spaceNarrative: 空间叙事 ========
  async spaceNarrative(page, i, total, project) {
    // 页面上下文，用于智能配图
    const pageContext = {
      pageTitle: page.title,
      sectionName: '空间设计',
      keywords: [page.title, '空间', '设计'],
      spaceType: project.spaceType
    };

    const imagesHtml = await renderImages(page.images, 'hero', '36vh', null, pageContext);

    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.spaceNarrative)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div class="split-55" data-anim style="align-items:stretch">
        <!-- 左文 -->
        <div class="col" style="justify-content:center">
          ${page.blocks ? renderBlocks(page.blocks, 'callout') : ''}
        </div>
        <!-- 右图 -->
        <div>${imagesHtml}</div>
      </div>
    `, project);
  },

  // ======== coreRendering: 效果图网格 ========
  async coreRendering(page, i, total, project) {
    // 页面上下文，用于智能配图
    const pageContext = {
      pageTitle: page.title,
      sectionName: '效果图',
      keywords: [page.title, '效果', '效果图'],
      spaceType: project.spaceType
    };

    const imagesHtml = await renderImages(page.images, 'grid', 'auto', '16/9', pageContext);

    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.coreRendering)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div class="grid-2" data-anim style="align-content:start;padding-top:1vh">
        ${imagesHtml}
      </div>
    `, project);
  },

  // ======== lightingScenario: 灯光模式 ========
  lightingScenario(page, i, total, project) {
    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.lightingScenario)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div class="grid-4" data-anim style="align-content:start;padding-top:1vh">
        ${page.blocks ? renderBlocks(page.blocks, 'pillar') : ''}
      </div>
    `, project);
  },

  // ======== riskItem: 风险评估 ========
  riskItem(page, i, total, project) {
    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.riskItem)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div class="grid-3" data-anim style="align-content:start;padding-top:1vh">
        ${page.blocks ? renderBlocks(page.blocks, 'pillar') : ''}
      </div>
    `, project);
  },

  // ======== investmentModel: 投资分配 ========
  async investmentModel(page, i, total, project) {
    // 页面上下文，用于智能配图
    const pageContext = {
      pageTitle: page.title,
      sectionName: '预算分配',
      keywords: [page.title, '预算', '投资', '成本'],
      spaceType: project.spaceType
    };

    const imagesHtml = await renderImages(page.images, 'content', '30vh', null, pageContext);

    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.investmentModel)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div class="split" data-anim style="align-items:start;padding-top:1vh">
        <!-- 左文 -->
        <div class="col">
          ${page.blocks ? renderBlocks(page.blocks, 'stat') : ''}
        </div>
        <!-- 右图 -->
        <div style="display:flex;flex-direction:column;gap:1.5vh;">
          ${imagesHtml}
        </div>
      </div>
    `, project);
  },

  // ======== nextStep: 时间线 ========
  nextStep(page, i, total, project) {
    return slide(page, i, total, null, `
      <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.nextStep)}</div>
      <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
      <div class="rule" data-anim></div>
      <div data-animate="pipeline" data-anim class="pipeline-section" style="flex:1;justify-content:center">
        <div class="pipeline" data-cols="${Math.min(page.blocks?.length || 5, 6)}">
          ${page.blocks ? page.blocks.map((b, bi) => `
            <div class="step" data-anim="step">
              <div class="step-nb">${String(bi + 1).padStart(2, '0')}</div>
              <div class="step-title">${escHtml(b.title || '')}</div>
              <div class="step-desc">${escHtml(b.desc || '')}</div>
            </div>
          `).join('\n          ') : ''}
        </div>
      </div>
    `, project);
  },

  // ======== closing: 收尾 ========
  async closing(page, i, total, project) {
    // 页面上下文，用于智能配图
    const pageContext = {
      pageTitle: page.title,
      sectionName: '收尾',
      keywords: [page.title, '总结', '感谢'],
      spaceType: project.spaceType
    };

    const imagesHtml = await renderImages(page.images, 'hero', '55vh', null, pageContext);

    return slide(page, i, total, 'hero', `
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;max-width:72%">
        <div class="kicker" data-anim>${escHtml(page.kicker || PAGE_KICKERS.closing)}</div>
        <div class="rule" data-anim style="width:20%"></div>
        ${page.blocks ? renderBlocks(page.blocks, 'callout-inset') : ''}
        ${imagesHtml}
        <div class="sign" data-anim style="margin-top:2vh">— ${_pf.DESIGNER_SHORT} · ${_pf.COMPANY_NAME}</div>
      </div>
    `, project);
  },
};

// ==================== Block Renderers ====================

function renderBlocks(blocks, asType) {
  if (!blocks || !blocks.length) return '';
  return blocks.map(b => {
    switch (asType || b.type) {
      case 'pillar': return pillarHtml(b);
      case 'stat': return statHtml(b);
      case 'rowline': return rowlineHtml(b);
      case 'step': return stepHtml(b);
      case 'callout':
      case 'callout-inset': return calloutHtml(b, asType === 'callout-inset');
      default: return pillarHtml(b);
    }
  }).join('\n          ');
}

function pillarHtml(b) {
  const iconHtml = b.icon ? `<div class="ic">${escHtml(b.icon)}</div>` : '';
  return `<div class="pillar">${iconHtml}<div class="t">${escHtml(b.title || '')}</div><div class="d">${escHtml(b.desc || '')}</div></div>`;
}

function statHtml(b) {
  return `<div class="stat-card"><div class="stat-label">${escHtml(b.label || '')}</div><div class="stat-nb">${escHtml(b.value || b.title || '')}</div>${b.desc ? `<div class="stat-note">${escHtml(b.desc)}</div>` : ''}</div>`;
}

function rowlineHtml(b) {
  return `<div class="rowline"><div class="k">${escHtml(b.title || b.label || '')}</div><div class="v">${escHtml(b.desc || '')}</div><div class="m">${escHtml(b.meta || '')}</div></div>`;
}

function stepHtml(b) {
  return `<div class="step"><div class="step-title">${escHtml(b.title || '')}</div><div class="step-desc">${escHtml(b.desc || '')}</div></div>`;
}

function calloutHtml(b, inset) {
  const cls = inset ? 'callout' : 'callout';
  const style = inset ? 'border-left-color:var(--paper);margin:1vh 0;background:none;padding-left:2vw;font-size:max(16px,1.6vw)' : '';
  return `<blockquote class="${cls}" style="${style}"><div class="q-big">${escHtml(b.title || '')}</div>${b.desc ? `<div>${escHtml(b.desc)}</div>` : ''}${b.cite ? `<span class="cite">${escHtml(b.cite)}</span>` : ''}</blockquote>`;
}

// ==================== Image Renderers ====================

async function renderImages(images, type, height, aspectRatio, pageContext = {}) {
  if (!images || !images.length) return '';

  const imageTags = [];
  for (const img of images) {
    const h = img.height || height || '28vh';
    // 默认使用 contain 避免图片截断
    const fit = img.fit || 'contain';
    const pos = img.position || 'center';
    const arStyle = aspectRatio ? `aspect-ratio:${aspectRatio}` : '';

    // 自动搜索匹配的图片
    const imageUrl = await smartMatchImage(img.description || '', pageContext);

    imageTags.push(`<figure class="img-slot" style="${arStyle};max-height:${h};overflow:hidden;border-radius:8px;box-shadow:0 4px 12px rgba(var(--ink-rgb),0.15);background:rgba(var(--paper-rgb), 0.05);">
      <img src="${imageUrl}" alt="${escHtml(img.description || img.type || '配图')}" style="width:100%;height:100%;object-fit:${fit};object-position:${pos};" loading="lazy">
    </figure>`);
  }

  return imageTags.join('\n        ');
}

// ==================== liNote ====================

function renderLiNote(note) {
  return `      <div class="li-note"><div class="li-tag">${_pf.DESIGNER_SHORT || '设计师'}注</div><div class="li-text">${escHtml(note)}</div></div>`;
}

// ==================== Slide Wrapper ====================

function slide(page, i, total, extraClass, innerHtml, project) {
  const theme = page.theme === 'light' ? 'light' : 'dark';
  const cls = extraClass ? `slide ${theme} ${extraClass}` : `slide ${theme}`;
  const animate = page.animate || 'cascade';
  const sectionName = SECTION_NAMES[page.section] || '';
  const typeLabel = project?.spaceType ? (
    { residential: '私宅', restaurant: '餐饮', hotel: '酒店民宿', exhibition: '展厅', retail: '服务门店' }[project.spaceType] || ''
  ) : '';
  const pageNum = String(i + 1).padStart(2, '0');
  const totalStr = String(total).padStart(2, '0');
  const chromeText = page.chrome || `${_pf.COMPANY_NAME} · ${sectionName}`;

  return `    <section class="${cls}" data-animate="${animate}">
      <div class="chrome"><div class="left"><span>${escHtml(chromeText)}</span></div><div class="right">${escHtml(typeLabel)}</div></div>
      <div class="frame">
        ${innerHtml.trim()}
      </div>
      <div class="foot"><span class="title">${escHtml(project?.name || '')}</span><span>${pageNum} / ${totalStr}</span></div>
    </section>`;
}

// ==================== Unknown PageType Fallback ====================

function renderUnknown(page, i, total, project) {
  return slide(page, i, total, null, `
    <div class="kicker" data-anim>${escHtml(page.kicker || '')}</div>
    <h2 class="h-xl" data-anim>${escHtml(page.title)}</h2>
    <div class="rule" data-anim></div>
    <div class="grid-3" data-anim style="align-content:start;padding-top:2vh">
      ${page.blocks ? renderBlocks(page.blocks, 'pillar') : ''}
    </div>
  `, project);
}

// ==================== 向后兼容：旧版 Markdown 解析 ====================

function fallbackSlides(project, narrative) {
  if (!narrative) return [];
  const typeLabel = {
    residential: '私宅', restaurant: '餐饮', hotel: '酒店民宿',
    exhibition: '展厅', retail: '服务门店',
  }[project.spaceType] || '私宅';

  const acts = parseActsLegacy(narrative);
  const actTitles = ['溯源', '破题', '淬炼', '显现'];
  const actLayouts = ['dark', 'light', 'dark', 'light'];
  const slides = [];

  // Cover
  slides.push(`    <section class="slide hero dark" data-animate="hero">
      <div class="chrome"><div class="left"><span>${_pf.COMPANY_NAME}</span><span class="sep"></span><span>提案</span></div><div class="right"><span>${typeLabel}</span></div></div>
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;max-width:76%">
        <div class="kicker" data-anim>设计提案</div>
        <h1 class="h-hero" data-anim>${escHtml(project.name || '设计提案')}</h1>
        <div style="height:1.6vh"></div>
        <p class="lead" data-anim style="max-width:70%">${escHtml(project.brief || '')}</p>
      </div>
      <div class="foot"><span class="title">${escHtml(project.name || '')}</span><span>01 / 02</span></div>
    </section>`);

  // Acts
  for (let i = 0; i < 4 && i < acts.length; i++) {
    const act = acts[i];
    const points = parseActContentLegacy(act.content || '');
    slides.push(`    <section class="slide ${actLayouts[i]}" data-animate="cascade">
      <div class="chrome"><div class="left"><span>${_pf.COMPANY_NAME}</span><span class="sep"></span><span>${actTitles[i]}</span></div><div class="right">${typeLabel}</div></div>
      <div class="frame">
        <div class="kicker" data-anim>第${['一','二','三','四'][i]}幕</div>
        <h2 class="h-xl" data-anim>${escHtml(act.title)}</h2>
        <div class="rule" data-anim></div>
        <div class="grid-3" data-anim style="align-content:start;padding-top:2vh">
          ${points.map(p => `<div class="pillar"><div class="t">${escHtml(p.title)}</div><div class="d">${escHtml(p.desc)}</div></div>`).join('\n          ')}
        </div>
      </div>
      <div class="foot"><span class="title">${escHtml(project.name || '')}</span><span>0${i + 2} / ${Math.min(acts.length + 1, 6)}</span></div>
    </section>`);
  }

  return slides;
}

function parseActsLegacy(narrative) {
  if (!narrative) return [];
  const lines = narrative.split('\n');
  const acts = [];
  let current = null;
  const patterns = [/第[一二三四]幕/i, /第一幕|第二幕|第三幕|第四幕/, /溯源|破题|淬炼|显现/i, /Act\s*[1-4]/i];

  for (const line of lines) {
    const t = line.trim();
    if (patterns.some(p => p.test(t)) && (t.includes('幕') || t.includes('Act') || t.includes('溯源') || t.includes('破题') || t.includes('淬炼') || t.includes('显现'))) {
      if (current) acts.push(current);
      current = { title: t, content: '' };
      continue;
    }
    if (current) current.content += line + '\n';
  }
  if (current) acts.push(current);
  return acts;
}

function parseActContentLegacy(content) {
  if (!content) return [{ title: '待补充', desc: '' }];
  const points = [];
  let title = '', desc = '';
  for (const line of content.split('\n')) {
    const t = line.trim();
    if (t.startsWith('**') && t.endsWith('**')) {
      if (title) points.push({ title, desc: desc || '...' });
      title = t.replace(/\*\*/g, ''); desc = '';
    } else if (t.startsWith('- ') || t.startsWith('* ')) {
      desc += (desc ? ' ' : '') + t.slice(2);
    } else if (t && !t.startsWith('#') && !t.startsWith('>') && !t.startsWith('---')) {
      desc += (desc ? ' ' : '') + t;
    }
  }
  if (title) points.push({ title, desc: desc || '...' });
  return points.slice(0, 3);
}

// ==================== 工具 ====================

function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function savePpt(html, outputPath) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, html, 'utf-8');
}

// ==================== Exports ====================

module.exports = {
  generatePpt,
  savePpt,
  THEMES,
  THEME_KEYS,
};
