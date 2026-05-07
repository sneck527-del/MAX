var ScriptGenerator = (function() {
  var TEMPLATES = {
    budget: {
      label: '预算敏感型',
      opener: '我给您算笔账，',
      logic: '这个钱摊到{years}年的使用周期，每天只有{daily}元。',
      closer: '在您看不见的地方我们没有省，该花的一分没少。'
    },
    professional: {
      label: '专业型',
      opener: '从工艺角度来说，',
      logic: '这个节点我们用的是{process}，比常规做法多了{extra}道工序。',
      closer: '这是行业里能做到这个精度的标准做法。'
    },
    quality: {
      label: '品质型',
      opener: '您摸一下这个材料，',
      logic: '这是{material}，{feature}，{brand}的产品，用了{years}年不会有问题。',
      closer: '买东西买的是安心，这个我可以保证。'
    }
  };

  return {
    // 根据客户性格标签生成差异化话术
    generate: function(clientTags, context) {
      clientTags = clientTags || [];
      var type = 'quality';
      if (clientTags.includes('预算敏感') || clientTags.includes('性价比')) type = 'budget';
      else if (clientTags.includes('专业') || clientTags.includes('懂行')) type = 'professional';

      var tpl = TEMPLATES[type];
      return {
        type: type,
        label: tpl.label,
        script: tpl.opener + tpl.logic + tpl.closer,
        context: context || ''
      };
    },

    // 生成导购小抄（给建材商用）
    generateSalesNote: function(material, emotionTag, clientHabits) {
      clientHabits = clientHabits || [];
      var painPoints = [];
      if (clientHabits.includes('养宠')) painPoints.push('耐抓耐磨，宠物爪子不留痕');
      if (clientHabits.includes('有娃')) painPoints.push('环保等级E0，儿童安全');
      if (clientHabits.includes('不爱打扫')) painPoints.push('易清洁，日常拖把即可');

      return [
        '【情绪价值】这款' + material + '支撑了空间的"' + (emotionTag || '高级感') + '"，',
        '【生活痛点】' + (painPoints.length ? painPoints.join('，') : '品质稳定，长期使用无忧') + '，',
        '【性价比】当下多投入，换来' + (15) + '年使用寿命，折算每年成本极低。'
      ].join('\n');
    },

    buildContext: function(clientTags) {
      var result = this.generate(clientTags);
      return '\n\n## 话术策略\n客户类型：' + result.label + '\n参考话术：' + result.script;
    }
  };
})();
