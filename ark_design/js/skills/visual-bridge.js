var VisualBridge = (function() {
  // 情绪 → 渲染参数映射
  var EMOTION_PARAMS = {
    '静谧':   { colorTemp: 2700, saturation: 0.15, brightness: 0.4, contrast: 0.3 },
    '包裹感': { colorTemp: 3000, saturation: 0.25, brightness: 0.5, contrast: 0.35 },
    '秩序':   { colorTemp: 4000, saturation: 0.20, brightness: 0.6, contrast: 0.5 },
    '仪式感': { colorTemp: 3500, saturation: 0.30, brightness: 0.45, contrast: 0.7 },
    '粗犷':   { colorTemp: 3200, saturation: 0.35, brightness: 0.4, contrast: 0.8 }
  };
  var LIGHTING_PARAMS = {
    '漫反射':   { type: 'ambient',   spread: 0.9, intensity: 0.5 },
    '戏剧光':   { type: 'cinematic', spread: 0.2, intensity: 0.9 },
    '自然延伸': { type: 'natural',   spread: 0.6, intensity: 0.7 },
    '退晕':     { type: 'gradient',  spread: 0.8, intensity: 0.4 }
  };
  var MATERIAL_PARAMS = {
    '骨架感':   { texture: 'hard',   roughness: 0.8, metallic: 0.7 },
    '皮肤感':   { texture: 'soft',   roughness: 0.9, metallic: 0.0 },
    '光影载体': { texture: 'glass',  roughness: 0.1, metallic: 0.3 }
  };

  return {
    // 将博弈结果中的三维标签转译为渲染参数
    translate: function(tags) {
      tags = tags || [];
      var params = { emotions: [], materials: [], lightings: [], render: {} };

      tags.forEach(function(tag) {
        if (EMOTION_PARAMS[tag])  { params.emotions.push(tag);  Object.assign(params.render, EMOTION_PARAMS[tag]); }
        if (LIGHTING_PARAMS[tag]) { params.lightings.push(tag); Object.assign(params.render, { lighting: LIGHTING_PARAMS[tag] }); }
        if (MATERIAL_PARAMS[tag]) { params.materials.push(tag); Object.assign(params.render, { material: MATERIAL_PARAMS[tag] }); }
      });

      // 生成文字描述供叙事架构师使用
      params.description = [
        params.emotions.length  ? '情绪基调：' + params.emotions.join('×')   : '',
        params.materials.length ? '材质语言：' + params.materials.join('×')  : '',
        params.lightings.length ? '光影策略：' + params.lightings.join('×')  : ''
      ].filter(Boolean).join('，');

      return params;
    },

    // 从 debateLog 中提取所有三维标签并生成渲染参数
    fromDebateLog: function(debateLog) {
      var allTags = [];
      (debateLog || []).forEach(function(entry) {
        var matches = (entry.content || '').match(/\[([^\]]+)\]/g) || [];
        matches.forEach(function(m) {
          var tag = m.slice(1, -1);
          if (!allTags.includes(tag)) allTags.push(tag);
        });
      });
      return this.translate(allTags);
    }
  };
})();
