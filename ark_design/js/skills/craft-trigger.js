var CraftTrigger = (function() {
  // 关键词 → 施工风险规则
  var RISK_RULES = [
    { keywords: ['悬浮', '悬浮吊顶', '无支撑'], level: '🔴', risk: '悬浮结构跨度超过3米必须钢骨架加固，本地工人找平经验不足，后期必裂' },
    { keywords: ['无边框', '无缝', '通铺'], level: '🟡', risk: '无边框/无缝工艺对工人精度要求极高，需提前确认本地工人施工经验' },
    { keywords: ['超长', '大跨度', '无柱'], level: '🟡', risk: '大跨度结构需结构工程师复核，确认楼板承重' },
    { keywords: ['极简收口', '消失感', '隐形'], level: '🟡', risk: '极简收口工艺复杂，需专业工人，建议提前打样确认效果' },
    { keywords: ['岩板挂墙', '大板挂墙'], level: '🔴', risk: '大面积岩板挂墙需干挂工艺，基层握钉力不足或超重风险，必须结构复核' },
    { keywords: ['微水泥地面', '微水泥地板'], level: '🟡', risk: '微水泥地面硬度有限，养宠物或重物拖拽易留划痕，需告知业主维护要求' },
    { keywords: ['地暖', '地热'], level: '🟡', risk: '地暖系统需与地面材料兼容，实木地板不建议配地暖，需确认材料耐温性' },
    { keywords: ['墙排', '隐蔽水管'], level: '🟡', risk: '墙排预埋深度需符合规范，完工后必须做48小时闭水试验' },
    { keywords: ['玻璃隔断', '全玻璃'], level: '🟡', risk: '玻璃隔断需使用钢化安全玻璃，厚度不低于10mm，需提供安全认证' },
    { keywords: ['开放式厨房', '无门厨房'], level: '🟡', risk: '开放式厨房油烟问题需强排风系统，建议配置侧吸+顶吸双重排烟' }
  ];

  return {
    // 扫描方案文本，返回触发的风险列表
    scan: function(text) {
      var triggered = [];
      RISK_RULES.forEach(function(rule) {
        var hit = rule.keywords.some(function(k) { return text.includes(k); });
        if (hit) triggered.push({ level: rule.level, risk: rule.risk, keywords: rule.keywords });
      });
      return triggered;
    },

    buildReport: function(text) {
      var risks = this.scan(text);
      if (!risks.length) return '';
      return '\n\n## 施工风险预警\n' + risks.map(function(r) {
        return r.level + ' ' + r.risk;
      }).join('\n');
    }
  };
})();
