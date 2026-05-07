// 本地图片搜索，不需要外部依赖
// Pexels API 作为主图源，本地 znzmo CDN 作为 fallback

const { searchPexels } = require('./pexelsSearch.js');

/**
 * 根据关键词搜索室内设计图片
 * @param {string} keyword 搜索关键词（如：现代客厅、北欧卧室、厨房设计等）
 * @param {number} count 返回图片数量
 * @param {string} spaceType 空间类型（residential/restaurant/hotel/exhibition/retail）
 * @returns {Array<string>} 图片URL列表
 */
async function searchImages(keyword, count = 5, spaceType = 'residential') {
  // 知末图片库，按关键词分类
  const imageDatabase = {
    // === 住宅 (Residential) ===
    '客厅': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/4a7519ddeb9b208f38911b0a817dfbcd.jpg"
    ],
    '客餐厅': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg"
    ],
    '现代客厅': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg"
    ],
    '北欧客厅': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/4a7519ddeb9b208f38911b0a817dfbcd.jpg"
    ],

    // 卧室相关
    '卧室': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/962ded495a6ee8fb853d8a0c54d7a443.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/253fb86d1791bd29223dd3108cf3f898.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/4a7519ddeb9b208f38911b0a817dfbcd.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/302e61d2e9b487929a2921c0c8622fee.jpg"
    ],
    '主卧': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/962ded495a6ee8fb853d8a0c54d7a443.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/253fb86d1791bd29223dd3108cf3f898.jpg"
    ],
    '儿童房': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/315b8b9f3a8d45cb74c46f23cb98cd1c.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/1c6492d3c33595fcfd190a08741e64ff.jpg"
    ],

    // 厨房相关
    '厨房': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/302e61d2e9b487929a2921c0c8622fee.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7fd7b380cd31189db861303ac475f4a7.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/f0f80f946a2091f155ff9bef7c41eec2.jpg"
    ],
    '开放式厨房': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7fd7b380cd31189db861303ac475f4a7.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/f0f80f946a2091f155ff9bef7c41eec2.jpg"
    ],

    // 卫生间相关
    '卫生间': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/962ded495a6ee8fb853d8a0c54d7a443.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/253fb86d1791bd29223dd3108cf3f898.jpg"
    ],
    '卫浴': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/962ded495a6ee8fb853d8a0c54d7a443.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/253fb86d1791bd29223dd3108cf3f898.jpg"
    ],

    // 材质相关
    '材质': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7ed3df3f1227ad3fadfb34c00c9e0bef.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/5b482a2bc19f0becd73a90c6e1a7225d.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg"
    ],
    '样板': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7ed3df3f1227ad3fadfb34c00c9e0bef.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/5b482a2bc19f0becd73a90c6e1a7225d.jpg"
    ],
    '材料': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7ed3df3f1227ad3fadfb34c00c9e0bef.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/5b482a2bc19f0becd73a90c6e1a7225d.jpg"
    ],

    // 户型/平面图相关
    '户型': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/bbe81d1e765e4b3a42f1e4c30621fcd4.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/4a13ce3c2a9de5d5600174cc8e5bdc50.jpg"
    ],
    '平面图': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/bbe81d1e765e4b3a42f1e4c30621fcd4.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/4a13ce3c2a9de5d5600174cc8e5bdc50.jpg"
    ],
    '平面方案': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/bbe81d1e765e4b3a42f1e4c30621fcd4.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/4a13ce3c2a9de5d5600174cc8e5bdc50.jpg"
    ],

    // 预算/图表相关
    '预算': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/bbe81d1e765e4b3a42f1e4c30621fcd4.jpg"
    ],
    '图表': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/bbe81d1e765e4b3a42f1e4c30621fcd4.jpg"
    ],

    // 风格
    '北欧': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/4a7519ddeb9b208f38911b0a817dfbcd.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/962ded495a6ee8fb853d8a0c54d7a443.jpg"
    ],
    '现代': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg"
    ],
    '轻奢': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7fd7b380cd31189db861303ac475f4a7.jpg"
    ],
    '日式': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/253fb86d1791bd29223dd3108cf3f898.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/302e61d2e9b487929a2921c0c8622fee.jpg"
    ],

    // ==================== 餐饮 (Restaurant) ====================
    '餐饮门头': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg"
    ],
    '用餐区': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg"
    ],
    '吧台': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7fd7b380cd31189db861303ac475f4a7.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/f0f80f946a2091f155ff9bef7c41eec2.jpg"
    ],
    '包间': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/962ded495a6ee8fb853d8a0c54d7a443.jpg"
    ],
    '后厨': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/302e61d2e9b487929a2921c0c8622fee.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7fd7b380cd31189db861303ac475f4a7.jpg"
    ],
    '餐厅': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg"
    ],
    '翻台': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/bbe81d1e765e4b3a42f1e4c30621fcd4.jpg"
    ],

    // ==================== 酒店民宿 (Hotel) ====================
    '酒店大堂': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg"
    ],
    '酒店客房': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/962ded495a6ee8fb853d8a0c54d7a443.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/253fb86d1791bd29223dd3108cf3f898.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/4a7519ddeb9b208f38911b0a817dfbcd.jpg"
    ],
    '民宿外观': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/253fb86d1791bd29223dd3108cf3f898.jpg"
    ],
    '走廊动线': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg"
    ],
    '酒店': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg"
    ],
    '民宿': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/253fb86d1791bd29223dd3108cf3f898.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/302e61d2e9b487929a2921c0c8622fee.jpg"
    ],

    // ==================== 展厅 (Exhibition) ====================
    '展厅入口': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg"
    ],
    '展陈区': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7ed3df3f1227ad3fadfb34c00c9e0bef.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/5b482a2bc19f0becd73a90c6e1a7225d.jpg"
    ],
    '互动装置': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/f0f80f946a2091f155ff9bef7c41eec2.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg"
    ],
    '品牌墙': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7ed3df3f1227ad3fadfb34c00c9e0bef.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/5b482a2bc19f0becd73a90c6e1a7225d.jpg"
    ],
    '展厅': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg"
    ],
    '展品': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7ed3df3f1227ad3fadfb34c00c9e0bef.jpg"
    ],

    // ==================== 服务门店 (Retail) ====================
    '门店门头': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg"
    ],
    '橱窗': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7ed3df3f1227ad3fadfb34c00c9e0bef.jpg"
    ],
    '陈列架': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/5b482a2bc19f0becd73a90c6e1a7225d.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7ed3df3f1227ad3fadfb34c00c9e0bef.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/da4991e12b991470fe4b99d12e9235d8.jpg"
    ],
    '收银区': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/7fd7b380cd31189db861303ac475f4a7.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/f0f80f946a2091f155ff9bef7c41eec2.jpg"
    ],
    '门店': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/9ac3bfd7ecab87affa5631447fb2c1fa.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/7b600c6c752ed63198677add08b891be.jpg",
      "https://image.linggan.znzmo.com/thumb_v1/w560/eff0d38b4d4e25483e2e730ce3ca83dc.jpg"
    ],
    '坪效': [
      "https://image.linggan.znzmo.com/thumb_v1/w560/bbe81d1e765e4b3a42f1e4c30621fcd4.jpg"
    ]
  };

  // 模糊匹配关键词
  keyword = keyword.trim();
  let matchedImages = [];

  // 精确匹配
  if (imageDatabase[keyword]) {
    matchedImages = imageDatabase[keyword];
  } else {
    // 模糊匹配，找包含关键词的分类
    for (const [key, images] of Object.entries(imageDatabase)) {
      if (keyword.includes(key) || key.includes(keyword)) {
        matchedImages = matchedImages.concat(images);
      }
    }

    // 如果没有匹配到，根据空间类型返回通用图片
    if (matchedImages.length === 0) {
      const fallbackMap = {
        restaurant: '餐厅',
        hotel: '酒店',
        exhibition: '展厅',
        retail: '门店',
      };
      const fallback = fallbackMap[spaceType] || '现代';
      matchedImages = imageDatabase[fallback] || imageDatabase['现代'];
    }
  }

  // 去重并返回指定数量的图片
  const uniqueImages = [...new Set(matchedImages)];
  return uniqueImages.slice(0, count);
}

/**
 * 智能匹配图片：根据图片描述和页面上下文自动匹配最合适的图片
 * @param {string} description 图片描述
 * @param {object} context 页面上下文（页面标题、内容关键词、空间类型等）
 * @returns {string} 图片URL
 */
async function smartMatchImage(description, context = {}) {
  // 合并所有关键词
  const allKeywords = [
    description,
    context.pageTitle || '',
    context.sectionName || '',
    ...(context.keywords || [])
  ].join(' ');

  // 提取关键词（按空间类型分组优先级）
  const residentialKeywords = [
    '客厅', '客餐厅', '卧室', '主卧', '儿童房', '厨房', '开放式厨房',
    '卫生间', '卫浴', '材质', '样板', '材料', '户型', '平面图', '平面方案',
    '预算', '图表', '北欧', '现代', '轻奢', '日式'
  ];

  const restaurantKeywords = [
    '餐饮门头', '用餐区', '吧台', '包间', '后厨', '餐厅', '翻台'
  ];

  const hotelKeywords = [
    '酒店大堂', '酒店客房', '民宿外观', '走廊动线', '酒店', '民宿'
  ];

  const exhibitionKeywords = [
    '展厅入口', '展陈区', '互动装置', '品牌墙', '展厅', '展品'
  ];

  const retailKeywords = [
    '门店门头', '橱窗', '陈列架', '收银区', '门店', '坪效'
  ];

  // 根据空间类型选择优先关键词列表
  const spaceType = context.spaceType || 'residential';
  const priorityMap = {
    residential: residentialKeywords,
    restaurant: [...restaurantKeywords, ...residentialKeywords],
    hotel: [...hotelKeywords, ...residentialKeywords],
    exhibition: [...exhibitionKeywords, ...residentialKeywords],
    retail: [...retailKeywords, ...residentialKeywords],
  };

  const keywords = priorityMap[spaceType] || priorityMap.residential;

  // 找到最匹配的关键词
  let bestMatch = spaceType === 'restaurant' ? '餐厅'
    : spaceType === 'hotel' ? '酒店'
    : spaceType === 'exhibition' ? '展厅'
    : spaceType === 'retail' ? '门店'
    : '现代';
  let maxMatchCount = 0;

  for (const keyword of keywords) {
    const regex = new RegExp(keyword, 'g');
    const matches = (allKeywords.match(regex) || []).length;
    if (matches > maxMatchCount) {
      maxMatchCount = matches;
      bestMatch = keyword;
    }
  }

  // 优先使用 Pexels API 搜索真实图片
  try {
    const pexelsResults = await searchPexels(description, 3);
    if (pexelsResults.length > 0) {
      return pexelsResults[Math.floor(Math.random() * pexelsResults.length)].url;
    }
  } catch (_) { /* fall through to local */ }

  // Fallback: 本地 znzmo 图库
  const images = await searchImages(bestMatch, 3, spaceType);
  return images[Math.floor(Math.random() * images.length)];
}

module.exports = {
  searchImages,
  smartMatchImage
};
