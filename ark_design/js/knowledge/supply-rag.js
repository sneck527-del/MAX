var SupplyRAG = (function() {
  var WARN_DAYS = 90;

  return {
    search: function(query, topN) {
      topN = topN || 5;
      var keywords = query.split(/[\s，,。、]+/).filter(Boolean);
      return S.suppliers
        .map(function(e) {
          var score = keywords.filter(function(k) {
            return e.name.includes(k) || e.category.includes(k) || (e.notes||'').includes(k);
          }).length;
          return Object.assign({}, e, { _score: score });
        })
        .filter(function(e) { return e._score > 0; })
        .sort(function(a, b) { return b._score - a._score; })
        .slice(0, topN);
    },

    isStale: function(supplier) {
      if (!supplier.updatedAt) return true;
      return (Date.now() - supplier.updatedAt) > WARN_DAYS * 86400000;
    },

    getStaleList: function() {
      return S.suppliers.filter(function(s) { return SupplyRAG.isStale(s); });
    },

    buildContext: function(query) {
      var hits = this.search(query, 5);
      if (!hits.length) return '';
      return '\n\n## 本地供应商参考\n' + hits.map(function(e) {
        var stale = SupplyRAG.isStale(e) ? ' ⚠️价格已超90天' : '';
        return '- ' + e.name + '（' + e.category + '）' + e.priceRange + stale + (e.notes ? ' ' + e.notes : '');
      }).join('\n');
    },

    add: function(entry) {
      var item = Object.assign({ id: uid(), createdAt: Date.now(), updatedAt: Date.now() }, entry);
      S.suppliers.push(item);
      Storage.saveKnowledge();
      return item;
    },

    updatePrice: function(id, priceRange) {
      var s = S.suppliers.find(function(x) { return x.id === id; });
      if (s) { s.priceRange = priceRange; s.updatedAt = Date.now(); Storage.saveKnowledge(); }
    }
  };
})();
