var DNAStore = (function() {

  function _timeDecay(lastUsed) {
    if (!lastUsed) return 0.5;
    var days = (Date.now() - lastUsed) / 86400000;
    return Math.exp(-days / 90); // 90天半衰期
  }

  return {
    search: function(query, topN) {
      topN = topN || 3;
      var keywords = query.split(/[\s，,。、]+/).filter(Boolean);
      return S.designDNA
        .map(function(e) {
          var kScore = e.tags.filter(function(t) {
            return keywords.some(function(k) { return t.includes(k) || k.includes(t); });
          }).length;
          var score = kScore * _timeDecay(e.lastUsed) * Math.log(1 + (e.usedCount || 0) + 1);
          return Object.assign({}, e, { _score: score });
        })
        .filter(function(e) { return e._score > 0; })
        .sort(function(a, b) { return b._score - a._score; })
        .slice(0, topN);
    },

    add: function(entry) {
      var item = Object.assign({ id: uid(), createdAt: Date.now(), usedCount: 0, lastUsed: null }, entry);
      S.designDNA.push(item);
      Storage.saveKnowledge();
      return item;
    },

    markUsed: function(id) {
      var e = S.designDNA.find(function(x) { return x.id === id; });
      if (e) { e.usedCount = (e.usedCount || 0) + 1; e.lastUsed = Date.now(); Storage.saveKnowledge(); }
    },

    // 注入历史摘要（用于 /feed 累积追问）
    getSummary: function(n) {
      n = n || 10;
      return S.designDNA.slice(-n).map(function(e) { return e.tags.join('/'); }).join(' · ');
    },

    buildContext: function(query) {
      var hits = this.search(query, 3);
      if (!hits.length) return '';
      hits.forEach(function(e) { DNAStore.markUsed(e.id); });
      return '\n\n## 参考知识（设计DNA）\n' + hits.map(function(e) {
        return '- [' + e.tags.join('][') + '] ' + e.content;
      }).join('\n');
    }
  };
})();
