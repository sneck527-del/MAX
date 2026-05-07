// Pexels API 图片搜索 — 免费额度 200 req/hr
// API key 从 ~/.arkconfig.json 或环境变量 PEXELS_API_KEY 读取

const https = require('https');
const config = require('./config.js');

const PEXELS_API = 'api.pexels.com';

function getApiKey() {
  return config.get('pexels_api_key') || process.env.PEXELS_API_KEY || '';
}

/**
 * 用中文描述搜索 Pexels 室内设计图片
 * @param {string} description 中文图片描述（会转译成英文关键词）
 * @param {number} count 返回数量
 * @returns {Promise<Array<{url: string, photographer: string, alt: string}>>}
 */
async function searchPexels(description, count = 5) {
  const apiKey = getApiKey();
  if (!apiKey) return [];

  const query = translateQuery(description);
  const perPage = Math.min(count, 10);

  return new Promise((resolve) => {
    const url = `https://${PEXELS_API}/v1/search?query=${encodeURIComponent(query)}&per_page=${perPage}&orientation=landscape&size=medium`;

    const req = https.get(url, {
      headers: { 'Authorization': apiKey },
      timeout: 8000,
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.photos && json.photos.length > 0) {
            const results = json.photos.slice(0, count).map(p => ({
              url: p.src?.large || p.src?.landscape || p.src?.original,
              photographer: p.photographer || '',
              alt: p.alt || description,
            }));
            resolve(results);
          } else {
            resolve([]);
          }
        } catch (e) {
          resolve([]);
        }
      });
    });

    req.on('error', () => resolve([]));
    req.on('timeout', () => { req.destroy(); resolve([]); });
  });
}

/**
 * 中文描述 → 英文搜索关键词
 */
function translateQuery(description) {
  const map = {
    // 住宅
    '客厅': 'living room interior design',
    '客餐厅': 'open plan living dining',
    '卧室': 'bedroom interior design',
    '主卧': 'master bedroom design',
    '儿童房': 'kids room interior',
    '厨房': 'kitchen interior design',
    '开放式厨房': 'open kitchen design',
    '卫生间': 'bathroom interior',
    '卫浴': 'bathroom design',
    '户型': 'floor plan architecture',
    '平面图': 'floor plan',

    // 餐饮
    '餐厅': 'restaurant interior design',
    '餐厅门头': 'restaurant facade storefront',
    '用餐区': 'restaurant dining area',
    '吧台': 'bar counter design',
    '包间': 'private dining room',
    '后厨': 'commercial kitchen',
    '餐饮门头': 'restaurant storefront',

    // 酒店
    '酒店': 'hotel interior design',
    '酒店大堂': 'hotel lobby design',
    '酒店客房': 'hotel room interior',
    '民宿': 'boutique hotel room',
    '民宿外观': 'boutique hotel exterior',
    '走廊动线': 'hotel corridor design',

    // 展厅
    '展厅': 'exhibition hall design',
    '展厅入口': 'exhibition entrance design',
    '展陈区': 'exhibition display design',
    '互动装置': 'interactive installation exhibition',
    '品牌墙': 'brand wall display',
    '展品': 'gallery display',

    // 门店
    '门店': 'retail store interior',
    '门店门头': 'store facade design',
    '橱窗': 'store window display',
    '陈列架': 'retail shelving display',
    '陈列区': 'retail display design',
    '收银台': 'store counter design',
    '收银区': 'retail counter area',

    // 风格
    '现代': 'modern interior design',
    '北欧': 'scandinavian interior',
    '轻奢': 'luxury interior design',
    '日式': 'japanese interior design',
    '材质': 'interior materials texture',
    '灯光': 'interior lighting design',
    '效果图': 'interior design rendering',
    '场景': 'interior design',
  };

  // 精确匹配
  for (const [cn, en] of Object.entries(map)) {
    if (description.includes(cn)) return en;
  }

  // 通用
  return 'interior design';
}

module.exports = { searchPexels, translateQuery };
