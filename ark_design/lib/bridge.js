/** ARK Design Profile Bridge — 读取 _profile 注入 prompt 变量 */

const path = require('path');
const fs = require('fs');

// ==================== 默认值（保持向后兼容） ====================

const DEFAULTS = {
  COMPANY_NAME: '李老师设计工作室',
  COMPANY_NAME_EN: 'Li Laoshi',
  DESIGNER_SHORT: '李老师',
  BRAND: 'ARK Design',
  DESIGN_STYLE: '',
  FORBIDDEN_WORDS: '很漂亮、很高档、效果图、温馨、大气',
  TARGET_CLIENT: '',
  PRICE_RANGE: '',
  CITY: '',
  COMPANY_TAGLINE: '',
};

// ==================== Profile → 变量映射 ====================

function extractVariables(profile) {
  if (!profile || typeof profile !== 'object') return { ...DEFAULTS };

  const companyName = profile.company_name || '';
  // 从公司名提取简短设计师称呼：取第一个中文字符 + "老师"
  let designerShort = '李老师';
  if (companyName) {
    const match = companyName.match(/^[一-鿿]/);
    if (match) {
      designerShort = match[0] + '老师';
    }
  }

  return {
    COMPANY_NAME: companyName || DEFAULTS.COMPANY_NAME,
    COMPANY_NAME_EN: companyName ? companyName.replace(/[^\w\s]/g, '').trim() : DEFAULTS.COMPANY_NAME_EN,
    DESIGNER_SHORT: designerShort,
    BRAND: companyName ? (companyName + ' · ARK Design') : DEFAULTS.BRAND,
    DESIGN_STYLE: profile.design_style || DEFAULTS.DESIGN_STYLE,
    FORBIDDEN_WORDS: profile.forbidden_words || DEFAULTS.FORBIDDEN_WORDS,
    TARGET_CLIENT: profile.target_client || DEFAULTS.TARGET_CLIENT,
    PRICE_RANGE: profile.price_range || DEFAULTS.PRICE_RANGE,
    CITY: profile.city || DEFAULTS.CITY,
    COMPANY_TAGLINE: profile.company_tagline || DEFAULTS.COMPANY_TAGLINE,
  };
}

/**
 * 对模板文本做变量替换
 * @param {string} template — 含 {{VAR}} 占位符的模板
 * @param {object} profile — 设计师 profile 对象（可选）
 * @returns {string} — 替换后的文本
 */
function applyProfile(template, profile) {
  const vars = extractVariables(profile);
  let result = template;
  // 只替换存在的占位符，保留未使用的变量
  result = result.replace(/\{\{COMPANY_NAME\}\}/g, vars.COMPANY_NAME);
  result = result.replace(/\{\{COMPANY_NAME_EN\}\}/g, vars.COMPANY_NAME_EN);
  result = result.replace(/\{\{DESIGNER_SHORT\}\}/g, vars.DESIGNER_SHORT);
  result = result.replace(/\{\{BRAND\}\}/g, vars.BRAND);
  result = result.replace(/\{\{DESIGN_STYLE\}\}/g, vars.DESIGN_STYLE);
  result = result.replace(/\{\{FORBIDDEN_WORDS\}\}/g, vars.FORBIDDEN_WORDS);
  result = result.replace(/\{\{TARGET_CLIENT\}\}/g, vars.TARGET_CLIENT);
  result = result.replace(/\{\{PRICE_RANGE\}\}/g, vars.PRICE_RANGE);
  result = result.replace(/\{\{CITY\}\}/g, vars.CITY);
  result = result.replace(/\{\{COMPANY_TAGLINE\}\}/g, vars.COMPANY_TAGLINE);
  return result;
}

/**
 * 从 project.json 加载 profile 并返回变量映射
 * @param {string} projectDir — 项目目录路径
 * @returns {object} — 替换变量
 */
function loadProfileFromProject(projectDir) {
  const projectPath = path.join(projectDir, 'project.json');
  if (!fs.existsSync(projectPath)) return { ...DEFAULTS };
  try {
    const project = JSON.parse(fs.readFileSync(projectPath, 'utf-8'));
    const profile = project._profile || {};
    return extractVariables(profile);
  } catch (e) {
    return { ...DEFAULTS };
  }
}

module.exports = {
  DEFAULTS,
  extractVariables,
  applyProfile,
  loadProfileFromProject,
};
