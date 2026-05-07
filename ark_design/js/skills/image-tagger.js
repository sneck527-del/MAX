var ImageTagger = (function() {
  // 15维标签 → 三维语义映射
  var STYLE_TO_EMOTION = {
    '极简': '静谧', '侘寂': '静谧', '日式': '静谧',
    '东方': '仪式感', '新中式': '仪式感',
    '轻奢': '秩序', '现代简约': '秩序',
    '工业风': '粗犷', '中古': '粗犷',
    '法式': '包裹感', '奶油风': '包裹感'
  };
  var MATERIAL_TO_DIM = {
    '微水泥': '皮肤感', '木地板': '皮肤感', '木饰面': '皮肤感',
    '棉麻': '皮肤感', '护墙板': '皮肤感',
    '岩板': '骨架感', '大理石': '骨架感', '原石': '骨架感',
    '不锈钢': '骨架感', '碳素钢': '骨架感',
    '长虹玻璃': '光影载体', '夹丝玻璃': '光影载体', '烤漆玻璃': '光影载体'
  };
  var CEILING_TO_LIGHTING = {
    '无主灯': '漫反射', '磁吸轨道': '漫反射', '边吊': '漫反射',
    '悬浮吊顶': '戏剧光', '叠级': '戏剧光',
    '平顶': '漫反射'
  };

  var ANALYSIS_PROMPT = '请分析这张室内设计图片，按以下格式输出（每项用中文冒号分隔）：\n' +
    '场景类型: \n空间场景: \n设计风格: \n主要颜色: \n主要材质: \n' +
    '吊顶类型: \n地面材质: \n墙面材质: \n特殊造型: \n光影特征: \n' +
    '情绪感受: \n只输出以上格式，不要其他说明。';

  var FLOORPLAN_PROMPT = '这张图片是室内平面图/户型图吗？只回答"是"或"否"。';

  function _compressImage(file, maxW, quality) {
    return new Promise(function(resolve) {
      var reader = new FileReader();
      reader.onload = function(e) {
        var img = new Image();
        img.onload = function() {
          var canvas = document.createElement('canvas');
          var ratio = Math.min(maxW / img.width, 1);
          canvas.width  = Math.round(img.width  * ratio);
          canvas.height = Math.round(img.height * ratio);
          canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
          var dataUrl = canvas.toDataURL('image/jpeg', quality);
          resolve(dataUrl.split(',')[1]); // 返回 base64
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  function _parseAnalysis(text) {
    var result = {};
    text.split('\n').forEach(function(line) {
      var idx = line.indexOf(':');
      if (idx < 0) idx = line.indexOf('：');
      if (idx < 0) return;
      var key = line.slice(0, idx).trim();
      var val = line.slice(idx + 1).trim();
      if (key && val) result[key] = val;
    });
    return result;
  }

  function _mapToThreeDim(parsed) {
    var tags = [];
    // 情绪维度
    var style = parsed['设计风格'] || '';
    Object.keys(STYLE_TO_EMOTION).forEach(function(k) {
      if (style.includes(k)) { var v = STYLE_TO_EMOTION[k]; if (!tags.includes(v)) tags.push(v); }
    });
    var mood = parsed['情绪感受'] || '';
    if (mood.includes('安静') || mood.includes('静') ) { if (!tags.includes('静谧'))   tags.push('静谧'); }
    if (mood.includes('仪式') || mood.includes('庄重')) { if (!tags.includes('仪式感')) tags.push('仪式感'); }
    if (mood.includes('秩序') || mood.includes('整齐')) { if (!tags.includes('秩序'))   tags.push('秩序'); }
    if (mood.includes('包裹') || mood.includes('温暖')) { if (!tags.includes('包裹感')) tags.push('包裹感'); }
    // 材质维度
    var mats = (parsed['主要材质'] || '') + (parsed['地面材质'] || '') + (parsed['墙面材质'] || '');
    Object.keys(MATERIAL_TO_DIM).forEach(function(k) {
      if (mats.includes(k)) { var v = MATERIAL_TO_DIM[k]; if (!tags.includes(v)) tags.push(v); }
    });
    // 光影维度
    var ceiling = parsed['吊顶类型'] || '';
    Object.keys(CEILING_TO_LIGHTING).forEach(function(k) {
      if (ceiling.includes(k)) { var v = CEILING_TO_LIGHTING[k]; if (!tags.includes(v)) tags.push(v); }
    });
    return tags;
  }

  return {
    // 单张图片打标（File 对象）
    tagImage: function(file) {
      return _compressImage(file, 1024, 0.85).then(function(b64) {
        // 先检测是否平面图
        return ApiClient.callVision(b64, FLOORPLAN_PROMPT).then(function(ans) {
          var isFloorPlan = ans.includes('是');
          if (isFloorPlan) {
            var item = DNAStore.add({ tags: ['户型图', '平面图'], content: file.name, source: 'image' });
            return { tags: ['户型图', '平面图'], parsed: {}, dnaId: item.id, isFloorPlan: true };
          }
          return ApiClient.callVision(b64, ANALYSIS_PROMPT).then(function(text) {
            var parsed = _parseAnalysis(text);
            var tags   = _mapToThreeDim(parsed);
            // 补充原始风格标签
            if (parsed['设计风格']) tags.push(parsed['设计风格']);
            if (parsed['空间场景']) tags.push(parsed['空间场景']);
            var content = Object.values(parsed).filter(Boolean).join(' | ').slice(0, 300);
            var item = DNAStore.add({ tags: tags, content: content, source: 'image' });
            return { tags: tags, parsed: parsed, dnaId: item.id, isFloorPlan: false };
          });
        });
      });
    },

    // 批量打标队列
    tagBatch: function(files, onProgress) {
      var results = [];
      var chain = Promise.resolve();
      files.forEach(function(file, i) {
        chain = chain.then(function() {
          return ImageTagger.tagImage(file).then(function(r) {
            results.push(Object.assign({ file: file.name }, r));
            if (onProgress) onProgress(i + 1, files.length, r);
          }).catch(function(e) {
            results.push({ file: file.name, error: e.message });
            if (onProgress) onProgress(i + 1, files.length, null);
          });
        });
      });
      return chain.then(function() { return results; });
    },

    // 从 ImageAnnotation CSV 导入
    importFromCSV: function(csvText) {
      var lines = csvText.split('\n');
      var headers = lines[0].split(',').map(function(h) { return h.trim(); });
      var imported = 0;
      lines.slice(1).forEach(function(line) {
        if (!line.trim()) return;
        var cols = line.split(',');
        var row = {};
        headers.forEach(function(h, i) { row[h] = (cols[i] || '').trim(); });
        var tags = [];
        if (row['设计风格']) tags.push(row['设计风格']);
        if (row['空间场景']) tags.push(row['空间场景']);
        if (row['主要材质']) tags.push(row['主要材质']);
        if (row['吊顶']) tags.push(row['吊顶']);
        var threeDim = _mapToThreeDim(row);
        tags = tags.concat(threeDim.filter(function(t) { return !tags.includes(t); }));
        if (tags.length) {
          DNAStore.add({ tags: tags, content: Object.values(row).join(' | ').slice(0, 300), source: 'csv' });
          imported++;
        }
      });
      Storage.saveKnowledge();
      return imported;
    }
  };
})();
