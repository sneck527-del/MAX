/** Guizang (歸藏) Magazine 风格渲染器
 *
 * 将 ARK narrator 输出的 pages 数组渲染为电子杂志 × 电子墨水风格的横向翻页 HTML.
 *
 * pageType → layout 映射:
 *   cover           → Layout 1 (Hero Cover)
 *   valueDirectory  → Layout 3 (Big Numbers / stat-card grid)
 *   deepInsight     → Layout 4 (Left Text Right Image)
 *   logicBoard      → Layout 10 (Lead Image + Side Text)
 *   visualNodes     → Layout 9 (Before/After)
 *   extremeScenario → Layout 6 (Pipeline)
 *   spaceNarrative  → Layout 4 (Left Text Right Image)
 *   coreRendering   → Layout 5 (Image Grid)
 *   lightingScenario→ Layout 3 (Big Numbers / grid-4)
 *   riskItem        → Layout 3 (Big Numbers / grid-3)
 *   investmentModel → Layout 4 (Left Text Right Image, stats)
 *   nextStep        → Layout 6 (Pipeline)
 *   closing         → Layout 8 (Big Quote)
 */

const fs = require('fs');
const path = require('path');
const { smartMatchImage } = require('./imageSearch');
const { extractVariables } = require('./bridge.js');

// Template path
const TEMPLATE_GZ = path.join(__dirname, 'template-gz.html');

// Section names
const SECTION_NAMES = {
  1: '项目概况', 2: '概念推演', 3: '空间叙事',
  4: '效果图展示', 5: '灯光与材质', 6: '风险与预算', 7: '总结与下一步',
};

// Section labels for chrome
const SECTION_CHROME = {
  1: '项目概况 · Overview',
  2: '概念推演 · Concept',
  3: '空间叙事 · Narrative',
  4: '效果图展示 · Rendering',
  5: '灯光与材质 · Light & Material',
  6: '风险与预算 · Risk & Budget',
  7: '总结与下一步 · Next Step',
};

let _pf = { COMPANY_NAME: 'ARK Design', DESIGNER_SHORT: '设计师' };

// ════════════════════════════════════════════════════════════
// Main entry
// ════════════════════════════════════════════════════════════

async function generatePpt(project, debateLog, narratorOutput, themeName) {
  const pages = narratorOutput.pages || [];
  _pf = extractVariables(project._profile);

  let template = fs.readFileSync(TEMPLATE_GZ, 'utf-8');

  // Replace title
  const title = (project.name || '设计提案') + ' · ' + _pf.COMPANY_NAME;
  template = template.replace('[必填] 替换为 PPT 标题 · Deck Title', title);

  // Generate slides
  const slides = await buildSlides(project, pages);
  template = template.replace('<!-- SLIDES_HERE -->', slides.join('\n\n'));

  return template;
}

// ════════════════════════════════════════════════════════════
// Build: pages → slides with section dividers
// ════════════════════════════════════════════════════════════

async function buildSlides(project, pages) {
  if (!pages || pages.length === 0) return fallbackSlides(project);

  // Group pages by section
  const sections = {};
  for (const page of pages) {
    const sec = page.section || 1;
    if (!sections[sec]) sections[sec] = [];
    sections[sec].push(page);
  }

  const total = Object.values(sections).reduce((sum, p) => sum + p.length, 0)
    + Object.keys(sections).length - 1 + 1; // + section dividers + cover
  let slideIndex = 0;

  const slides = [];

  for (const secNum of Object.keys(sections).sort((a, b) => a - b)) {
    const secPages = sections[secNum];
    const secName = SECTION_NAMES[secNum] || `章节 ${secNum}`;

    // Section divider (Layout 2) — skip for section 1, use cover instead
    if (parseInt(secNum) === 1) {
      // Section 1 starts with cover
      const coverPage = secPages.find(p => p.pageType === 'cover');
      if (coverPage) {
        slideIndex++;
        const slide = await renderCover(coverPage, slideIndex, total, project);
        slides.push(slide);
        // Remove cover from pages
        const idx = secPages.indexOf(coverPage);
        if (idx >= 0) secPages.splice(idx, 1);
      }
    } else {
      slideIndex++;
      slides.push(renderSectionDivider(secNum, secName, slideIndex, total));
    }

    // Render each page
    for (const page of secPages) {
      slideIndex++;
      const slide = await renderGzSlide(page, secName, slideIndex, total, project);
      if (slide) slides.push(slide);
    }
  }

  return slides;
}

// ════════════════════════════════════════════════════════════
// Page type → Guizang layout dispatcher
// ════════════════════════════════════════════════════════════

async function renderGzSlide(page, secName, i, total, project) {
  const renderer = RENDERERS[page.pageType];
  if (!renderer) return renderUnknown(page, secName, i, total);
  return renderer(page, secName, i, total, project);
}

const RENDERERS = {
  cover: renderCover,
  valueDirectory: renderValueDirectory,
  deepInsight: renderDeepInsight,
  logicBoard: renderLogicBoard,
  visualNodes: renderVisualNodes,
  extremeScenario: renderExtremeScenario,
  spaceNarrative: renderSpaceNarrative,
  coreRendering: renderCoreRendering,
  lightingScenario: renderLightingScenario,
  riskItem: renderRiskItem,
  investmentModel: renderInvestmentModel,
  nextStep: renderNextStep,
  closing: renderClosing,
};

// ════════════════════════════════════════════════════════════
// Layout 1: Cover — hero dark
// ════════════════════════════════════════════════════════════

async function renderCover(page, i, total, project) {
  const title = escHtml(page.title || project.name || '设计提案');
  const kicker = escHtml(page.kicker || _pf.COMPANY_NAME || '');
  const lead = page.blocks ? page.blocks.map(b => b.value || b.desc || '').filter(Boolean).join(' · ') : '';
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · 项目概况`);
  const imgDesc = page.images?.[0]?.description || '';

  let heroImg = '';
  if (imgDesc) {
    const ctx = { pageTitle: page.title, sectionName: '封面', spaceType: project.spaceType };
    const imgUrl = await smartMatchImage(imgDesc, ctx);
    heroImg = `<figure class="frame-img" style="aspect-ratio:16/9; max-height:40vh; opacity:.5; margin-top:3vh" data-anim>
      <img src="${imgUrl}" alt="${escHtml(imgDesc)}">
    </figure>`;
  }

  const liNote = page.liNote
    ? `<div class="meta-row" data-anim style="margin-top:2vh"><span>${escHtml(page.liNote)}</span></div>`
    : '';

  return section('hero dark', i, total, chrome, '', `
    <div class="frame" style="display:grid; gap:3vh; align-content:center; min-height:74vh">
      <div class="kicker" data-anim>${kicker}</div>
      <h1 class="display-zh" data-anim>${title}</h1>
      ${lead ? `<p class="lead" style="max-width:55vw" data-anim>${lead}</p>` : ''}
      ${heroImg}
      ${liNote}
    </div>
  `);
}

// ════════════════════════════════════════════════════════════
// Layout 2: Section Divider — hero light/dark alternating
// ════════════════════════════════════════════════════════════

function renderSectionDivider(secNum, secName, i, total) {
  const theme = parseInt(secNum) % 2 === 0 ? 'hero light' : 'hero dark';
  const chrome = SECTION_CHROME[secNum] || secName;
  return section(theme, i, total, chrome, secName, `
    <div class="frame" style="display:grid; gap:5vh; align-content:center; min-height:74vh">
      <div class="kicker" data-anim>Section ${String(secNum).padStart(2, '0')}</div>
      <h1 class="display-zh" style="font-size:7vw" data-anim>${escHtml(secName)}</h1>
    </div>
  `);
}

// ════════════════════════════════════════════════════════════
// Layout 3: Value Directory / Big Numbers — light
// ════════════════════════════════════════════════════════════

function renderValueDirectory(page, secName, i, total) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  return renderStatGrid(page, secName, i, total, chrome, 'grid-6', 'light');
}

function renderLightingScenario(page, secName, i, total) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  return renderStatGrid(page, secName, i, total, chrome, 'grid-4', 'light');
}

function renderRiskItem(page, secName, i, total) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  return renderStatGrid(page, secName, i, total, chrome, 'grid-3', 'dark');
}

function renderStatGrid(page, secName, i, total, chrome, gridClass, theme) {
  const blocks = page.blocks || [];
  const statCards = blocks.map(b => `
    <div class="stat-card" data-anim>
      <div class="stat-label">${escHtml(b.label || b.title || '')}</div>
      <div class="stat-nb">${escHtml(b.value || b.desc || '—')}</div>
      ${b.note ? `<div class="stat-note">${escHtml(b.note)}</div>` : ''}
    </div>
  `).join('\n');

  const liNote = page.liNote
    ? `<div class="meta-row" data-anim style="margin-top:3vh"><span>${escHtml(page.liNote)}</span></div>`
    : '';

  return section(theme, i, total, chrome, secName, `
    <div class="frame" style="padding-top:5vh">
      <div class="kicker" data-anim>${escHtml(page.kicker || '')}</div>
      <h2 class="h1-zh" data-anim>${escHtml(page.title)}</h2>
      <div class="${gridClass}" style="margin-top:5vh">
        ${statCards}
      </div>
      ${liNote}
    </div>
  `);
}

// ════════════════════════════════════════════════════════════
// Layout 4: Left Text Right Image — dark/light alternating
// ════════════════════════════════════════════════════════════

async function renderDeepInsight(page, secName, i, total, project) {
  return renderTextImage(page, secName, i, total, project, 'dark', 'grid-2-7-5');
}

async function renderSpaceNarrative(page, secName, i, total, project) {
  return renderTextImage(page, secName, i, total, project, 'dark', 'grid-2-7-5');
}

async function renderInvestmentModel(page, secName, i, total, project) {
  return renderTextImage(page, secName, i, total, project, 'light', 'grid-2-7-5');
}

async function renderTextImage(page, secName, i, total, project, theme, gridClass) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  const blocks = page.blocks || [];

  // Left column: kicker + title + blocks (as stat or callout)
  const leftParts = [];
  if (page.kicker) leftParts.push(`<div class="kicker" data-anim>${escHtml(page.kicker)}</div>`);
  leftParts.push(`<h2 class="h1-zh" data-anim>${escHtml(page.title)}</h2>`);

  // Separate stat-type and callout-type blocks
  const statBlocks = blocks.filter(b => b.type === 'stat');
  const calloutBlocks = blocks.filter(b => b.type === 'callout');
  const otherBlocks = blocks.filter(b => !['stat', 'callout'].includes(b.type));

  if (statBlocks.length > 0) {
    const statHtml = statBlocks.map(b => `
      <div class="stat-card" data-anim>
        <div class="stat-label">${escHtml(b.label || '')}</div>
        <div class="stat-nb" style="font-size:4vw">${escHtml(b.value || b.desc || '')}</div>
        ${b.note ? `<div class="stat-note">${escHtml(b.note)}</div>` : ''}
      </div>
    `).join('\n');
    leftParts.push(`<div class="row" style="gap:3vw; flex-wrap:wrap">${statHtml}</div>`);
  }

  if (otherBlocks.length > 0) {
    const desc = otherBlocks.map(b => b.desc || b.value || '').filter(Boolean).join('<br>');
    if (desc) leftParts.push(`<p class="body-zh" data-anim>${desc}</p>`);
  }

  if (calloutBlocks.length > 0) {
    const c = calloutBlocks[0];
    leftParts.push(`<div class="callout" data-anim>
      "${escHtml(c.desc || c.value || '')}"
      ${c.title ? `<div class="callout-src">— ${escHtml(c.title)}</div>` : ''}
    </div>`);
  }

  if (page.liNote) {
    leftParts.push(`<div class="meta-row" data-anim><span>${escHtml(page.liNote)}</span></div>`);
  }

  // Right column: image
  const imgDesc = page.images?.[0]?.description || '';
  let rightHtml = '';
  if (imgDesc) {
    const ctx = { pageTitle: page.title, sectionName: secName, spaceType: project.spaceType };
    const imgUrl = await smartMatchImage(imgDesc, ctx);
    rightHtml = `<figure class="frame-img" style="aspect-ratio:16/10; max-height:56vh" data-anim>
      <img src="${imgUrl}" alt="${escHtml(imgDesc)}">
      <figcaption class="img-cap">${escHtml(imgDesc)}</figcaption>
    </figure>`;
  }

  return section(theme, i, total, chrome, secName, `
    <div class="frame ${gridClass}" style="padding-top:5vh">
      <div style="display:flex; flex-direction:column; justify-content:space-between; gap:3vh">
        ${leftParts.join('\n')}
      </div>
      ${rightHtml}
    </div>
  `);
}

// ════════════════════════════════════════════════════════════
// Layout 10: LogicBoard — Lead Image + Side Text
// ════════════════════════════════════════════════════════════

async function renderLogicBoard(page, secName, i, total, project) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  const blocks = page.blocks || [];

  // rowline blocks as lead paragraphs
  const descParts = blocks.map(b => {
    const t = b.title || '';
    const d = b.desc || b.value || '';
    return t && d ? `<strong>${escHtml(t)}：</strong>${escHtml(d)}` : escHtml(t || d);
  });

  const imgDesc = page.images?.[0]?.description || '';
  let rightHtml = '';
  if (imgDesc) {
    const ctx = { pageTitle: page.title, sectionName: secName, spaceType: project.spaceType };
    const imgUrl = await smartMatchImage(imgDesc, ctx);
    rightHtml = `<figure class="frame-img" style="aspect-ratio:3/4; max-height:56vh" data-anim>
      <img src="${imgUrl}" alt="${escHtml(imgDesc)}">
      <figcaption class="img-cap">${escHtml(imgDesc)}</figcaption>
    </figure>`;
  }

  const liNote = page.liNote
    ? `<div class="callout" style="margin-top:3vh" data-anim>
        "${escHtml(page.liNote)}"
        <div class="callout-src">— ${_pf.DESIGNER_SHORT}</div>
      </div>`
    : '';

  return section('light', i, total, chrome, secName, `
    <div class="frame grid-2-8-4" style="padding-top:5vh">
      <div>
        <div class="kicker" data-anim>${escHtml(page.kicker || '')}</div>
        <h2 class="h1-zh" style="margin-bottom:3vh" data-anim>${escHtml(page.title)}</h2>
        ${descParts.length > 0 ? `<p class="body-zh" data-anim>${descParts.join('</p><p class="body-zh" data-anim>')}</p>` : ''}
        ${liNote}
      </div>
      ${rightHtml}
    </div>
  `);
}

// ════════════════════════════════════════════════════════════
// Layout 9: VisualNodes — Before/After comparison
// ════════════════════════════════════════════════════════════

function renderVisualNodes(page, secName, i, total) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  const blocks = page.blocks || [];
  const leftBlock = blocks[0];
  const rightBlock = blocks[1];

  function buildPillar(b) {
    if (!b) return '';
    return `<div style="padding:3vh 2vw; border-left:3px solid currentColor">
      <div class="kicker" style="opacity:.9">${escHtml(b.label || b.title || '')}</div>
      <h3 class="h2-zh" style="margin-top:2vh">${escHtml(b.title || '')}</h3>
      <p class="body-zh" style="margin-top:2vh">${escHtml(b.desc || b.value || '')}</p>
    </div>`;
  }

  const liNote = page.liNote
    ? `<div class="meta-row" data-anim style="margin-top:3vh"><span>${escHtml(page.liNote)}</span></div>`
    : '';

  return section('light', i, total, chrome, secName, `
    <div class="frame" style="padding-top:5vh" data-animate="directional">
      <div class="kicker" data-anim>${escHtml(page.kicker || '')}</div>
      <h2 class="h1-zh" style="margin-bottom:3vh" data-anim>${escHtml(page.title)}</h2>
      <div class="grid-2-6-6" style="gap:5vw 4vh">
        <div data-anim="left" style="opacity:.65">${buildPillar(leftBlock)}</div>
        <div data-anim="right">${buildPillar(rightBlock)}</div>
      </div>
      ${liNote}
    </div>
  `);
}

// ════════════════════════════════════════════════════════════
// Layout 5: CoreRendering — Image Grid
// ════════════════════════════════════════════════════════════

async function renderCoreRendering(page, secName, i, total, project) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  const images = page.images || [];
  const ctx = { pageTitle: page.title, sectionName: secName, spaceType: project.spaceType };

  const imageHtmls = await Promise.all(
    images.slice(0, 6).map(async (img) => {
      const url = await smartMatchImage(img.description || '', ctx);
      return `<figure class="frame-img" style="height:26vh" data-anim>
        <img src="${url}" alt="${escHtml(img.description || '')}">
        <figcaption class="img-cap">${escHtml(img.description || '')}</figcaption>
      </figure>`;
    })
  );

  const gridClass = imageHtmls.length <= 3 ? 'grid-3' : 'grid-3-3';
  const gridStyle = 'grid-3-3' in {} ? '' : 'style="display:grid; grid-template-columns:repeat(3,1fr); gap:3vh 3vw"';

  const liNote = page.liNote
    ? `<div class="meta-row" data-anim style="margin-top:3vh"><span>${escHtml(page.liNote)}</span></div>`
    : '';

  return section('dark', i, total, chrome, secName, `
    <div class="frame" style="padding-top:4vh">
      <div class="kicker" data-anim>${escHtml(page.kicker || '')}</div>
      <h2 class="h1-zh" data-anim>${escHtml(page.title)}</h2>
      <div class="${gridClass}" style="margin-top:4vh; display:grid; grid-template-columns:repeat(${Math.min(imageHtmls.length, 3)},1fr); gap:3vh 3vw">
        ${imageHtmls.join('\n')}
      </div>
      ${liNote}
    </div>
  `, '效果图');
}

// ════════════════════════════════════════════════════════════
// Layout 6: Pipeline — ExtremeScenario / NextStep
// ════════════════════════════════════════════════════════════

async function renderExtremeScenario(page, secName, i, total, project) {
  const theme = 'light';
  return renderPipeline(page, secName, i, total, project, theme);
}

function renderNextStep(page, secName, i, total) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  const blocks = page.blocks || [];

  const steps = blocks.map((b, bi) => `
    <div class="step" data-anim="step">
      <div class="step-nb">${String(bi + 1).padStart(2, '0')}</div>
      <div class="step-title">${escHtml(b.title || b.label || '')}</div>
      <div class="step-desc">${escHtml(b.desc || b.value || '')}</div>
    </div>
  `).join('\n');

  const liNote = page.liNote
    ? `<div class="meta-row" data-anim style="margin-top:3vh"><span>${escHtml(page.liNote)}</span></div>`
    : '';

  return section('light', i, total, chrome, secName, `
    <div class="frame" data-animate="pipeline">
      <div class="kicker" data-anim>${escHtml(page.kicker || '')}</div>
      <h2 class="h1-zh" data-anim>${escHtml(page.title)}</h2>
      <div class="pipeline-section" style="margin-top:3vh">
        <div class="pipeline" data-cols="${Math.min(blocks.length, 6)}">
          ${steps}
        </div>
      </div>
      ${liNote}
    </div>
  `);
}

async function renderPipeline(page, secName, i, total, project, theme) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  const blocks = page.blocks || [];

  const steps = blocks.map((b, bi) => `
    <div class="step" data-anim="step">
      <div class="step-nb">${String(bi + 1).padStart(2, '0')}</div>
      <div class="step-title">${escHtml(b.title || b.label || '')}</div>
      <div class="step-desc">${escHtml(b.desc || b.value || '')}</div>
    </div>
  `).join('\n');

  // Image above pipeline
  const imgDesc = page.images?.[0]?.description || '';
  let imgHtml = '';
  if (imgDesc) {
    const ctx = { pageTitle: page.title, sectionName: secName, spaceType: project.spaceType };
    const imgUrl = await smartMatchImage(imgDesc, ctx);
    imgHtml = `<figure class="frame-img" style="aspect-ratio:16/9; max-height:30vh; margin-bottom:3vh" data-anim>
      <img src="${imgUrl}" alt="${escHtml(imgDesc)}">
      <figcaption class="img-cap">${escHtml(imgDesc)}</figcaption>
    </figure>`;
  }

  const liNote = page.liNote
    ? `<div class="meta-row" data-anim style="margin-top:3vh"><span>${escHtml(page.liNote)}</span></div>`
    : '';

  return section(theme, i, total, chrome, secName, `
    <div class="frame" data-animate="pipeline">
      <div class="kicker" data-anim>${escHtml(page.kicker || '')}</div>
      <h2 class="h1-zh" data-anim>${escHtml(page.title)}</h2>
      ${imgHtml}
      <div class="pipeline-section" style="margin-top:2vh">
        <div class="pipeline" data-cols="${Math.min(blocks.length, 6)}">
          ${steps}
        </div>
      </div>
      ${liNote}
    </div>
  `);
}

// ════════════════════════════════════════════════════════════
// Layout 8: Closing — Big Quote (衬线金句)
// ════════════════════════════════════════════════════════════

function renderClosing(page, secName, i, total) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  const quote = page.blocks?.[0]?.desc || page.blocks?.[0]?.value || page.title || '';
  const source = _pf.DESIGNER_SHORT + ' · ' + _pf.COMPANY_NAME;

  const liNote = page.liNote
    ? `<p class="lead" style="max-width:50vw; opacity:.65; margin-top:3vh" data-anim>${escHtml(page.liNote)}</p>`
    : '';

  return section('hero light', i, total, chrome, secName, `
    <div class="frame" style="display:grid; gap:5vh; align-content:center; min-height:70vh" data-animate="quote">
      <div class="kicker" data-anim>${escHtml(page.kicker || '提案核心')}</div>
      <blockquote style="font-family:var(--serif-zh); font-weight:700; font-size:5.2vw; line-height:1.2; letter-spacing:-.01em; max-width:68vw">
        <span data-anim="line" style="display:block">"${escHtml(quote)}"</span>
      </blockquote>
      ${liNote}
      <div class="meta-row" data-anim>
        <span>— ${escHtml(source)}</span>
      </div>
    </div>
  `);
}

// ════════════════════════════════════════════════════════════
// Fallback: unknown pageType
// ════════════════════════════════════════════════════════════

function renderUnknown(page, secName, i, total) {
  const chrome = escHtml(page.chrome || `${_pf.COMPANY_NAME} · ${secName}`);
  return section('light', i, total, chrome, secName, `
    <div class="frame" style="display:grid; gap:3vh; align-content:center; min-height:60vh">
      <div class="kicker">${escHtml(page.pageType || '')}</div>
      <h2 class="h1-zh">${escHtml(page.title)}</h2>
      ${page.liNote ? `<p class="body-zh">${escHtml(page.liNote)}</p>` : ''}
    </div>
  `);
}

// ════════════════════════════════════════════════════════════
// Fallback: no pages from narrator
// ════════════════════════════════════════════════════════════

function fallbackSlides(project) {
  return [
    section('hero dark', 1, 1, `${_pf.COMPANY_NAME} · 项目`, '', `
      <div class="frame" style="display:grid; gap:3vh; align-content:center; min-height:70vh">
        <h1 class="display-zh" data-anim>${escHtml(project.name || '设计提案')}</h1>
        <p class="lead" data-anim>${escHtml(project.brief || '')}</p>
      </div>
    `),
  ];
}

// ════════════════════════════════════════════════════════════
// Section wrapper
// ════════════════════════════════════════════════════════════

function section(theme, i, total, chromeText, secName, inner, footLabel) {
  const foot = footLabel || secName || '';
  const footRight = `${String(i).padStart(2, '0')} / ${String(total).padStart(2, '0')}`;
  return `    <section class="slide ${theme}">
      <div class="chrome">
        <div class="left"><span>${chromeText}</span></div>
        <div class="right"><span>${footRight}</span></div>
      </div>
${inner}
      <div class="foot">
        <div class="title">${foot}</div>
        <div>${footRight}</div>
      </div>
    </section>`;
}

// ════════════════════════════════════════════════════════════
// Util
// ════════════════════════════════════════════════════════════

function escHtml(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

module.exports = { generatePpt };
