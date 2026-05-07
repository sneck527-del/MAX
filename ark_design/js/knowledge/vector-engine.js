var VectorEngine = (function() {
  // 简单的TF-IDF风格关键词向量，用于图片+文字的相似度检索
  function _tokenize(text) {
    return text.split(/[\s，,。、\[\]【】]+/).filter(function(t) { return t.length > 0; });
  }

  function _cosineSim(a, b) {
    var setA = {}, setB = {}, dot = 0, normA = 0, normB = 0;
    a.forEach(function(t) { setA[t] = (setA[t] || 0) + 1; });
    b.forEach(function(t) { setB[t] = (setB[t] || 0) + 1; });
    Object.keys(setA).forEach(function(t) {
      normA += setA[t] * setA[t];
      if (setB[t]) dot += setA[t] * setB[t];
    });
    Object.keys(setB).forEach(function(t) { normB += setB[t] * setB[t]; });
    return (normA && normB) ? dot / (Math.sqrt(normA) * Math.sqrt(normB)) : 0;
  }

  return {
    // 在 designDNA 中检索与 query 最相似的条目
    search: function(query, topN) {
      topN = topN || 5;
      var qTokens = _tokenize(query);
      return S.designDNA
        .map(function(e) {
          var eTokens = _tokenize(e.tags.join(' ') + ' ' + (e.content || ''));
          return Object.assign({}, e, { _sim: _cosineSim(qTokens, eTokens) });
        })
        .filter(function(e) { return e._sim > 0; })
        .sort(function(a, b) { return b._sim - a._sim; })
        .slice(0, topN);
    },

    // 图片打标结果入库后，检索视觉相似的历史案例
    findSimilarByTags: function(tags, topN) {
      return this.search(tags.join(' '), topN || 3);
    }
  };
})();
