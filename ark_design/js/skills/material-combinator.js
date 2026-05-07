var MaterialCombinator = (function() {
  // 情绪标签 → 经典材质+光影组合
  var COMBOS = {
    '静谧': [
      { materials: ['哑光微水泥', '纳米柔光面'], lighting: '漫反射', note: '大面积留白，无可见光源，墙面退晕' },
      { materials: ['哑光木皮', '棉麻'], lighting: '自然延伸', note: '格栅引入自然光，低频视觉信号' }
    ],
    '包裹感': [
      { materials: ['木饰面', '皮革软包'], lighting: '漫反射', note: '三面围合，暖色调，隐藏灯带' },
      { materials: ['棉麻', '木作格栅'], lighting: '自然延伸', note: '暖色围合，格栅光影，触感友好' }
    ],
    '秩序': [
      { materials: ['岩板', '拉丝不锈钢'], lighting: '漫反射', note: '通铺同色系，对缝精准，均匀照明' },
      { materials: ['烤漆玻璃', '碳素钢'], lighting: '戏剧光', note: '强对齐线，轨道射灯，克制装饰' }
    ],
    '仪式感': [
      { materials: ['大理石', '碳素钢'], lighting: '戏剧光', note: '轴线对称，重点照明，空间序列' },
      { materials: ['原石', '长虹玻璃'], lighting: '自然延伸', note: '竖向光影纹理，强化入户轴线' }
    ],
    '粗犷': [
      { materials: ['原石', '碳素钢'], lighting: '戏剧光', note: '暴露结构，窄束光切割阴影' },
      { materials: ['水磨石', '拉丝不锈钢'], lighting: '自然延伸', note: '粗犷质感与几何光影对话' }
    ]
  };

  return {
    suggest: function(emotionTags) {
      var results = [];
      (emotionTags || []).forEach(function(tag) {
        var combos = COMBOS[tag];
        if (combos) {
          // 随机选一个组合
          var combo = combos[Math.floor(Math.random() * combos.length)];
          results.push(Object.assign({ emotion: tag }, combo));
        }
      });
      return results;
    },

    buildContext: function(emotionTags) {
      var suggestions = this.suggest(emotionTags);
      if (!suggestions.length) return '';
      return '\n\n## 材质组合建议\n' + suggestions.map(function(s) {
        return '- [' + s.emotion + '] ' + s.materials.join(' + ') + ' × ' + s.lighting + '：' + s.note;
      }).join('\n');
    }
  };
})();
