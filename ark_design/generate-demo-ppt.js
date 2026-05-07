const { generatePpt, savePpt } = require('./lib/ppt');

// Demo project data
const demoProject = {
  name: "现代轻奢住宅设计方案",
  type: "residential",
  budget: "120万",
  city: "上海"
};

// Demo debate log
const demoDebateLog = [];

// Demo 10-page PPT content
const demoNarratorOutput = {
  pages: [
    // Cover page
    {
      pageType: "cover",
      title: "现代轻奢住宅设计方案 · 上海",
      kicker: "设计提案",
      blocks: [
        { title: "项目地址：上海浦东", desc: "220㎡ 平层" },
        { title: "设计风格：现代轻奢", desc: "预算：120万" }
      ],
      images: [
        { type: "hero", description: "客厅效果图", height: "70vh", fit: "cover" }
      ],
      section: 1
    },

    // Value directory
    {
      pageType: "valueDirectory",
      title: "设计核心亮点",
      blocks: [
        { title: "空间优化", desc: "开放式客餐厅布局，提升空间利用率30%" },
        { title: "智能系统", desc: "全屋智能家居，照明/空调/安防一键控制" },
        { title: "收纳设计", desc: "定制化收纳系统，满足5口之家储物需求" },
        { title: "环保材料", desc: "E0级板材，无醛添加，保障家人健康" },
        { title: "灯光设计", desc: "无主灯设计，营造多层次光影氛围" },
        { title: "动线优化", desc: "家务动线/访客动线/居住动线分离，提升居住效率" }
      ],
      section: 1
    },

    // Deep insight
    {
      pageType: "deepInsight",
      title: "业主需求深度分析",
      blocks: [
        { title: "年轻夫妻+2个孩子+老人同住", desc: "需要足够的卧室和公共活动空间" },
        { title: "业主偏好现代轻奢风格", desc: "喜欢低饱和度色彩，高品质材质" },
        { title: "需要独立的办公/学习空间", desc: "夫妻居家办公，孩子需要学习区" },
        { title: "充足的储物空间", desc: "儿童用品、换季衣物、生活用品收纳" },
        { title: "厨房需要中西厨分离", desc: "热爱烹饪，需要专业的厨房配置" }
      ],
      images: [
        { type: "content", description: "户型分析图", height: "28vh", fit: "cover" },
        { type: "content", description: "业主意向参考", height: "28vh", fit: "cover" }
      ],
      section: 2
    },

    // Logic board - materials
    {
      pageType: "logicBoard",
      title: "材质选择方案",
      blocks: [
        { title: "地面：天然大理石+实木复合地板", desc: "客厅餐厅大理石，卧室暖色系地板" },
        { title: "墙面：艺术涂料+硬包背景", desc: "环保艺术漆，床头背景定制硬包" },
        { title: "柜体：烤漆面板+石英石台面", desc: "定制橱柜衣柜，防刮耐磨易清洁" },
        { title: "门窗：系统断桥铝+Low-E玻璃", desc: "隔音隔热，提高居住舒适度" },
        { title: "五金：进口品牌五金件", desc: "阻尼铰链，静音导轨，使用寿命长" }
      ],
      images: [
        { type: "micro", description: "材质样板", height: "20vh", fit: "cover" }
      ],
      section: 2
    },

    // Visual nodes - comparison
    {
      pageType: "visualNodes",
      title: "平面方案对比",
      blocks: [
        { title: "方案A：开放式布局", desc: "客餐厅打通，空间通透，互动性强" },
        { title: "方案B：半开放式布局", desc: "客厅加玻璃隔断，兼顾通透和私密" }
      ],
      images: [
        { type: "content", description: "方案A平面", height: "28vh", fit: "contain" },
        { type: "content", description: "方案B平面", height: "28vh", fit: "contain" }
      ],
      section: 2
    },

    // Space narrative
    {
      pageType: "spaceNarrative",
      title: "客餐厅空间叙事",
      blocks: [
        { title: "空间以暖灰色为主色调", desc: "搭配金属线条和大理石材质，营造轻奢质感" },
        { title: "无主灯设计搭配灯带和射灯", desc: "营造多层次光影效果，氛围可随心切换" },
        { title: "开放式厨房连接岛台", desc: "既是操作台也是吧台，满足早餐、简餐需求" },
        { title: "背景墙采用岩板+木格栅", desc: "现代感十足，同时增加空间温度" }
      ],
      images: [
        { type: "hero", description: "客餐厅效果图", height: "36vh", fit: "cover" }
      ],
      section: 3
    },

    // Core rendering - grid
    {
      pageType: "coreRendering",
      title: "空间效果图展示",
      images: [
        { type: "grid", description: "客厅效果图", aspectRatio: "16/9", fit: "cover" },
        { type: "grid", description: "主卧效果图", aspectRatio: "16/9", fit: "cover" },
        { type: "grid", description: "儿童房效果图", aspectRatio: "16/9", fit: "cover" },
        { type: "grid", description: "厨房效果图", aspectRatio: "16/9", fit: "cover" }
      ],
      section: 3
    },

    // Lighting scenario
    {
      pageType: "lightingScenario",
      title: "灯光设计方案",
      blocks: [
        { title: "基础照明：嵌入式筒灯", desc: "3000K暖白光，均匀照亮空间" },
        { title: "重点照明：射灯", desc: "照亮装饰画、摆件、背景墙，突出层次" },
        { title: "氛围照明：灯带", desc: "吊顶、柜体、背景墙暗藏灯带，营造温馨氛围" },
        { title: "智能控制：场景模式", desc: "回家/离家/观影/就餐，一键切换灯光模式" }
      ],
      section: 4
    },

    // Investment model - budget
    {
      pageType: "investmentModel",
      title: "预算分配方案",
      blocks: [
        { title: "基础装修：40万", desc: "占比33%，包含拆改、水电、泥木、油漆" },
        { title: "定制柜体：25万", desc: "占比21%，橱柜、衣柜、鞋柜、收纳柜等" },
        { title: "主材：20万", desc: "占比17%，瓷砖、地板、门窗、卫浴、五金" },
        { title: "软装：20万", desc: "占比17%，家具、灯具、窗帘、饰品、挂画" },
        { title: "家电：15万", desc: "占比12%，空调、冰箱、洗衣机、厨房电器" }
      ],
      images: [
        { type: "content", description: "预算饼图", height: "30vh", fit: "contain" }
      ],
      section: 5
    },

    // Closing page
    {
      pageType: "closing",
      title: "感谢聆听 · 期待合作",
      blocks: [
        { title: "设计团队：李老师工作室", desc: "专注高端住宅设计15年" }
      ],
      images: [
        { type: "hero", description: "设计团队", height: "55vh", fit: "cover" }
      ],
      section: 7
    }
  ],
  narrative: ""
};

// Generate PPT with "沙丘" theme
async function generate() {
  const html = await generatePpt(demoProject, demoDebateLog, demoNarratorOutput, "沙丘");

  // Save to file
  savePpt(html, "F:/code/ARK Design/demo-10page-ppt.html");

  console.log("✅ 10页演示PPT已生成：F:/code/ARK Design/demo-10page-ppt.html");
  console.log("打开文件即可查看效果，图片均来自 https://pin.znztv.com/");
}

generate();