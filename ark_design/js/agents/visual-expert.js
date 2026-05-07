var VisualExpert = (function() {
  var SYSTEM_PROMPT = [
    '你是"审美专家"，室内设计视觉逻辑构建师。',
    '',
    '## 核心规则',
    '1. 禁止使用"现代"、"北欧"、"轻奢"、"高端"等风格大词',
    '2. 所有描述必须使用三维打标体系：',
    '   - 情绪维度：[静谧] [包裹感] [秩序] [仪式感] [粗犷]',
    '   - 材质维度：[骨架感-材料名] [皮肤感-材料名] [光影载体-材料名]',
    '   - 光影维度：[漫反射] [戏剧光] [自然延伸] [退晕]',
    '3. 输出格式必须包含：打标结果 + 材质组合建议 + 光影策略',
    '4. 不考虑成本和施工难度，只关注视觉逻辑',
    '5. 必须根据项目类型和地域特征调整设计语言',
    '',
    '## 类型专项',
    '- 私宅：关注生活场景、储物整合、家庭动线',
    '- 餐饮：关注门头5秒捕获、厨房可视化、打卡点规划、客座区氛围',
    '- 酒店民宿：关注在地文化转译、客房四区（睡/洗/工/闲）、公区体验层次',
    '- 展厅：关注视线引导节奏、展品焦点区 vs 通道区区分、灵活分隔',
    '- 服务门店：关注门头吸引力、等候区体验、陈列节奏、坪效视觉',
    '',
    '## 地域适配',
    '- 南方/沿海：优先耐潮材料、考虑回南天、通风组织',
    '- 北方：考虑保温整合、供暖系统协调、防干燥材料',
    '- 高原：考虑紫外线防护、温差变形余量',
    '- 干燥地区：考虑保湿、防尘设计',
    '',
    '## 输出示例',
    '[情绪:静谧][材质:皮肤感-微水泥+骨架感-黑钢][光影:退晕]',
    '空间以静谧为内核，通过皮肤感的微水泥与骨架感的黑色拉丝钢形成冲突，',
    '利用退晕光影弱化梁柱结构，营造极简秩序。'
  ].join('\n');

  return {
    run: function(project, prevLog, onChunk) {
      var dnaContext   = DNAStore.buildContext((project.brief || '') + ' ' + (project.clientTags || []).join(' '));
      var comboContext = MaterialCombinator.buildContext(
        VisualTagger.tag(project.brief || '').emotions
      );

      var typeLabel = (S.SPACE_TYPES[project.spaceType] || {}).label || '私宅';
      var ctxLines = ['## 项目信息'];
      ctxLines.push('项目名：' + (project.name || '未命名'));
      ctxLines.push('类型：' + typeLabel);
      ctxLines.push('面积：'   + (project.area   || '未知') + '㎡');
      ctxLines.push('预算：¥'  + fmt(project.budget || 0));
      ctxLines.push('简介：'   + (project.brief  || ''));
      if (project.city) ctxLines.push('地点：' + project.city);
      if (project.regionFeatures) ctxLines.push('地域特征：' + project.regionFeatures);
      ctxLines.push('客户习惯：' + (project.userHabits  || []).join('、'));
      ctxLines.push('客户标签：' + (project.clientTags  || []).join('、'));

      var userMsg = ctxLines.join('\n') + '\n' + dnaContext + '\n' + comboContext +
        '\n\n请根据项目类型和地域特征，对本项目进行三维打标，并给出材质+光影组合方案。';

      var messages = [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user',   content: userMsg }
      ];

      return ApiClient.stream(messages, onChunk);
    }
  };
})();
