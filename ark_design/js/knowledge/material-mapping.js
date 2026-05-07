var MaterialMapping = (function() {
  // 主材关键词 → 供应商品类映射
  var MATERIAL_CATEGORY_MAP = {
    '微水泥': '涂料/特殊涂料', '乳胶漆': '涂料', '硅藻泥': '涂料',
    '岩板': '石材/岩板', '大理石': '石材/岩板', '原石': '石材/岩板',
    '木地板': '地板', '复合地板': '地板', '实木地板': '地板',
    '瓷砖': '瓷砖', '水磨石': '瓷砖/特殊地面',
    '木饰面': '木作/饰面板', '护墙板': '木作/饰面板',
    '不锈钢': '金属/五金', '碳素钢': '金属/五金', '拉丝钢': '金属/五金',
    '长虹玻璃': '玻璃', '夹丝玻璃': '玻璃', '烤漆玻璃': '玻璃',
    '棉麻': '软装/布艺', '丝绸': '软装/布艺', '皮革': '软装/布艺'
  };

  return {
    // 从方案文本中提取材料关键词，匹配供应商
    matchSuppliers: function(proposalText) {
      var matched = [];
      Object.keys(MATERIAL_CATEGORY_MAP).forEach(function(mat) {
        if (proposalText.includes(mat)) {
          var category = MATERIAL_CATEGORY_MAP[mat];
          var suppliers = S.suppliers.filter(function(s) { return s.category.includes(category); });
          if (suppliers.length) {
            matched.push({ material: mat, category: category, suppliers: suppliers });
          }
        }
      });
      return matched;
    },

    buildContext: function(proposalText) {
      var matches = this.matchSuppliers(proposalText);
      if (!matches.length) return '';
      return '\n\n## 主材供应商匹配\n' + matches.map(function(m) {
        return '- **' + m.material + '**（' + m.category + '）：' +
          m.suppliers.map(function(s) {
            var stale = SupplyRAG.isStale(s) ? ' ⚠️' : '';
            return s.name + ' ' + s.priceRange + stale;
          }).join('、');
      }).join('\n');
    },

    // 三维语义标签 → 推荐材料品类
    emotionToMaterials: function(emotionTag) {
      var map = {
        '静谧':   ['微水泥', '哑光木皮', '棉麻', '纳米柔光面'],
        '包裹感': ['木饰面', '护墙板', '皮革', '棉麻'],
        '秩序':   ['岩板', '拉丝不锈钢', '烤漆玻璃'],
        '仪式感': ['大理石', '原石', '碳素钢', '长虹玻璃'],
        '粗犷':   ['原石', '碳素钢', '水磨石', '清水混凝土']
      };
      return map[emotionTag] || [];
    }
  };
})();
