var BudgetSlider = (function() {
  // 空间优先级：核心区保级，非核心区降级
  var CORE_SPACES    = ['客厅', '玄关', '主卧', '餐厅'];
  var NONCORE_SPACES = ['次卧', '儿童房', '储藏间', '衣帽间', '过道', '阳台'];

  // 材质降级映射
  var DOWNGRADE_MAP = {
    '实木地板':   { alt: '同色系复合地板', saving: 0.4 },
    '岩板':       { alt: '仿岩板瓷砖',     saving: 0.5 },
    '大理石':     { alt: '大理石纹瓷砖',   saving: 0.6 },
    '微水泥':     { alt: '微水泥质感涂料', saving: 0.3 },
    '木饰面':     { alt: '木纹贴膜',       saving: 0.5 },
    '定制柜':     { alt: '成品柜+局部定制', saving: 0.35 },
    '进口瓷砖':   { alt: '国产同规格瓷砖', saving: 0.4 }
  };

  return {
    // 生成 A/B 方案：A=原方案，B=降级方案
    generate: function(items, totalBudget) {
      var planA = items;
      var planB = [];
      var totalSaving = 0;

      items.forEach(function(item) {
        var isCore = CORE_SPACES.some(function(s) { return (item.space || '').includes(s); });
        if (isCore) {
          planB.push(Object.assign({}, item, { note: '核心区保级' }));
          return;
        }
        var downgrade = DOWNGRADE_MAP[item.material];
        if (downgrade) {
          var saving = (item.price || 0) * downgrade.saving;
          totalSaving += saving;
          planB.push(Object.assign({}, item, {
            material: downgrade.alt,
            price: Math.round((item.price || 0) * (1 - downgrade.saving)),
            note: '由' + item.material + '降为' + downgrade.alt + '，节省约¥' + Math.round(saving)
          }));
        } else {
          planB.push(Object.assign({}, item, { note: '维持原方案' }));
        }
      });

      return {
        planA: planA,
        planB: planB,
        totalSaving: Math.round(totalSaving),
        summary: '为保住核心区品质，非核心区材质微调，总价回落约¥' + Math.round(totalSaving) + '元'
      };
    },

    buildContext: function(budget) {
      return '\n\n## 预算策略\n核心区（' + CORE_SPACES.join('、') + '）保留高级材质；' +
             '非核心区（' + NONCORE_SPACES.join('、') + '）可执行A/B降级方案，总价控制在¥' + fmt(budget) + '以内。';
    }
  };
})();
