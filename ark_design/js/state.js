var S = {
  // API 配置
  apiProvider: 'deepseek',
  apiUrl: 'https://api.deepseek.com',
  apiKey: '',
  apiModel: 'deepseek-chat',
  qwenApiKey: '',         // 视觉打标专用

  // 项目
  currentProject: null,  // { id, name, brief, clientTags[], userHabits[], budget, area, createdAt, debateLog[], spaceType, city, regionFeatures, fundingPhases[] }
  projects: [],

  // 项目类型映射
  SPACE_TYPES: {
    residential:    { label: '私宅',      icon: '🏠' },
    restaurant:     { label: '餐饮',      icon: '🍽️' },
    hotel:          { label: '酒店民宿',  icon: '🏨' },
    exhibition:     { label: '展厅',      icon: '🎨' },
    retail:         { label: '服务门店',  icon: '🏪' }
  },

  // 地域气候分类
  REGION_TYPES: {
    south:    { label: '南方（华南/华东）', traits: '潮湿、回南天、空调负荷大、需防潮通风' },
    north:    { label: '北方（华北/东北）', traits: '干燥、冬季供暖、需保温防冻、施工窗口期短' },
    plateau:  { label: '高原（云贵/川西）', traits: '强紫外线、温差大、热胀冷缩、供氧需求' },
    coastal:  { label: '沿海',             traits: '盐雾腐蚀、抗风压、防水等级要求高' },
    arid:     { label: '干燥地区（西北）', traits: '风沙大、保湿需求、防尘设计' }
  },

  // 对话
  chatHistory: [],
  debateLog: [],          // [{ agent, content, timestamp }] — 持久化到 currentProject

  // 知识库
  designDNA: [],          // [{ id, tags[], content, source, createdAt, usedCount, lastUsed }]
  refutations: [],        // [{ id, objection, response, category }]
  suppliers: [],          // [{ id, name, category, priceRange, notes, updatedAt }]
  commLogic: [],          // [{ id, scenario, script, tags[], disabled }]
  aestheticRules: [],     // [{ id, rule, category, severity }]
  templates: [],          // [{ id, name, type, budget, clientType, debateLog[], createdAt }]
  clientPersonas: [],     // [{ id, name, tags[], habits[], projectIds[] }]

  // 归档输出目录句柄（File System Access API）
  outputDirHandle: null,

  // UI
  activeView: 'chat',     // 'chat' | 'debate' | 'knowledge' | 'archive' | 'moodboard'
  isGenerating: false,
  debatePaused: false,
  currentDebateStep: 0
};
