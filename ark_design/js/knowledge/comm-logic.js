var CommLogic = (function() {
  return {
    search: function(query, topN) {
      topN = topN || 3;
      var keywords = query.split(/[\s，,。、]+/).filter(Boolean);
      return S.commLogic
        .filter(function(e) { return !e.disabled; })
        .map(function(e) {
          var score = keywords.filter(function(k) {
            return e.scenario.includes(k) || e.tags.some(function(t) { return t.includes(k); });
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
      return '\n\n## 话术参考\n' + hits.map(function(e) {
        return '- [' + e.scenario + '] ' + e.script;
      }).join('\n');
    },

    add: function(entry) {
      var item = Object.assign({ id: uid(), createdAt: Date.now(), disabled: false, tags: [] }, entry);
      S.commLogic.push(item);
      Storage.saveKnowledge();
      return item;
    },

    // 标记禁用（李老师说"这太AI了"时触发）
    disable: function(id, reason) {
      var e = S.commLogic.find(function(x) { return x.id === id; });
      if (e) { e.disabled = true; e.disableReason = reason || ''; Storage.saveKnowledge(); }
    },

    // 检测否定词，返回是否触发纠错
    detectNegation: function(text) {
      var triggers = ['不对', '太AI了', '不是我说话的方式', '这不对', '不像我', '太机器了', '废话', '不自然'];
      return triggers.some(function(t) { return text.includes(t); });
    }
  };
})();
