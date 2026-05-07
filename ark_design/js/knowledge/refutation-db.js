var RefutationDB = (function() {
  return {
    search: function(query, topN) {
      topN = topN || 3;
      var keywords = query.split(/[\s，,。、]+/).filter(Boolean);
      return S.refutations
        .map(function(e) {
          var score = keywords.filter(function(k) {
            return e.objection.includes(k) || e.category.includes(k);
          }).length;
          return Object.assign({}, e, { _score: score });
        })
        .filter(function(e) { return e._score > 0; })
        .sort(function(a, b) { return b._score - a._score; })
        .slice(0, topN);
    },

    buildContext: function(query) {
      var hits = this.search(query, 3);
      if (!hits.length) return '';
      return '\n\n## 红线库（绝对禁止）\n' + hits.map(function(e) {
        return '- [' + e.category + '] 异议："' + e.objection + '" → 应对："' + e.response + '"';
      }).join('\n');
    },

    add: function(entry) {
      var item = Object.assign({ id: uid(), createdAt: Date.now() }, entry);
      S.refutations.push(item);
      Storage.saveKnowledge();
      return item;
    }
  };
})();
