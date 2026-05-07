var PersonaRandomizer = (function() {
  var PERSONAS = [
    {
      id: 'perfectionist',
      label: '细节强迫症',
      weight: 0.25,
      focus: ['对缝', '色差', '插座位置', '开关高度', '门缝', '踢脚线'],
      opener: '我要盯着每一个细节——'
    },
    {
      id: 'budget_warrior',
      label: '性价比杀手',
      weight: 0.30,
      focus: ['为什么这么贵', '网上更便宜', '能不能换便宜的', '这个值吗'],
      opener: '我在网上查了一下，同款——'
    },
    {
      id: 'life_observer',
      label: '生活体验派',
      weight: 0.30,
      focus: ['动线', '收纳', '打扫', '实用性', '生活场景'],
      opener: '我不看图纸好不好看，我只问——'
    },
    {
      id: 'ambivalent',
      label: '审美纠结体',
      weight: 0.15,
      focus: ['我又看了个视频', '我朋友家是另一种风格', '我改主意了', '能不能换'],
      opener: '我昨天刷到一个视频，感觉那个更好——'
    }
  ];

  return {
    // 按权重随机激活一种或多种性格模式
    pick: function(clientTags) {
      clientTags = clientTags || [];

      // 如果客户标签里有明确性格，优先使用
      var forced = PERSONAS.filter(function(p) {
        return clientTags.some(function(t) { return t.includes(p.label) || t.includes(p.id); });
      });
      if (forced.length) return forced;

      // 否则按权重随机选1-2种
      var rand = Math.random();
      var cumulative = 0;
      var selected = [];
      var shuffled = PERSONAS.slice().sort(function() { return Math.random() - 0.5; });
      for (var i = 0; i < shuffled.length; i++) {
        cumulative += shuffled[i].weight;
        if (rand < cumulative) { selected.push(shuffled[i]); break; }
      }
      // 30%概率叠加第二种性格
      if (Math.random() < 0.3 && shuffled.length > 1) {
        var second = shuffled.find(function(p) { return p.id !== selected[0].id; });
        if (second) selected.push(second);
      }
      return selected;
    },

    buildContext: function(clientTags) {
      var personas = this.pick(clientTags);
      return '\n\n## 客户性格模式\n' + personas.map(function(p) {
        return '- [' + p.label + '] 关注点：' + p.focus.slice(0, 3).join('、');
      }).join('\n');
    }
  };
})();
