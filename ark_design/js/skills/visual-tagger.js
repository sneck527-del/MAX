var VisualTagger = (function() {
  // 描述词 → 三维维度映射表
  var EMOTION_MAP = {
    '安静': '静谧', '呼吸感': '静谧', '留白': '静谧', '极简': '静谧', '禅意': '静谧',
    '安全': '包裹感', '温暖': '包裹感', '围合': '包裹感', '舒适': '包裹感', '柔软': '包裹感',
    '整齐': '秩序', '对称': '秩序', '规整': '秩序', '逻辑': '秩序', '克制': '秩序',
    '高级': '仪式感', '庄重': '仪式感', '轴线': '仪式感', '序列': '仪式感', '焦点': '仪式感',
    '粗犷': '粗犷', '工业': '粗犷', '原始': '粗犷', '野性': '粗犷', '力量': '粗犷'
  };

  var MATERIAL_MAP = {
    '不锈钢': '骨架感', '碳素钢': '骨架感', '拉丝钢': '骨架感', '原石': '骨架感', '混凝土': '骨架感',
    '微水泥': '皮肤感', '木皮': '皮肤感', '木饰面': '皮肤感', '棉麻': '皮肤感', '皮革': '皮肤感', '纳米': '皮肤感',
    '长虹玻璃': '光影载体', '夹丝玻璃': '光影载体', '水波纹': '光影载体', '丝绸': '光影载体', '烤漆玻璃': '光影载体'
  };

  var LIGHTING_MAP = {
    '无主灯': '漫反射', '灯槽': '漫反射', '退晕': '漫反射', '均匀': '漫反射', '柔和': '漫反射',
    '射灯': '戏剧光', '窄束': '戏剧光', '明暗': '戏剧光', '阴影': '戏剧光', '聚光': '戏剧光',
    '格栅': '自然延伸', '百叶': '自然延伸', '投影': '自然延伸', '自然光': '自然延伸', '阳光': '自然延伸'
  };

  function _mapTokens(text, map) {
    var results = [];
    Object.keys(map).forEach(function(keyword) {
      if (text.includes(keyword)) {
        var val = map[keyword];
        if (!results.includes(val)) results.push(val);
      }
    });
    return results;
  }

  return {
    // 将自然语言描述映射到三维标签
    tag: function(text) {
      var emotions  = _mapTokens(text, EMOTION_MAP);
      var materials = _mapTokens(text, MATERIAL_MAP);
      var lightings = _mapTokens(text, LIGHTING_MAP);

      var tags = [];
      emotions.forEach(function(e)  { tags.push(e); });
      materials.forEach(function(m) { tags.push(m); });
      lightings.forEach(function(l) { tags.push(l); });

      return {
        emotions:  emotions,
        materials: materials,
        lightings: lightings,
        tags:      tags,
        formatted: tags.map(function(t) { return '[' + t + ']'; }).join('')
      };
    },

    // 从 /feed 内容中提取标签并存入 DNA 库
    feedAndStore: function(text) {
      var result = this.tag(text);
      if (!result.tags.length) return null;
      return DNAStore.add({ tags: result.tags, content: text.slice(0, 200), source: 'feed' });
    }
  };
})();
