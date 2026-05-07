var KnowledgePanel = (function() {
  var _activeTab = 'dna';

  var TABS = [
    { id: 'dna',      label: '设计DNA',   icon: '🧬' },
    { id: 'refute',   label: '红线库',    icon: '🚫' },
    { id: 'supply',   label: '供应商',    icon: '🏪' },
    { id: 'comm',     label: '话术库',    icon: '💬' },
    { id: 'template', label: '项目模板',  icon: '📋' },
    { id: 'persona',  label: '客户画像',  icon: '👤' }
  ];

  function _renderTabs() {
    return '<div class="kp-tabs">' +
      TABS.map(function(t) {
        return '<button class="kp-tab' + (_activeTab === t.id ? ' active' : '') + '" onclick="KnowledgePanel.switchTab(\'' + t.id + '\')">' +
          t.icon + ' ' + t.label + '</button>';
      }).join('') +
      '</div>';
  }

  function _renderDNA() {
    var items = S.designDNA.slice().sort(function(a, b) { return (b.lastUsed || 0) - (a.lastUsed || 0); });
    var staleCount = SupplyRAG.getStaleList().length;
    return '<div class="kp-toolbar">' +
      '<input id="dnaSearch" placeholder="搜索标签或内容…" oninput="KnowledgePanel.searchDNA(this.value)" style="flex:1">' +
      '<button class="btn btn-sm btn-outline" onclick="KnowledgePanel.importCSV()">📥 从CSV导入</button>' +
      '</div>' +
      (staleCount ? '<div class="kp-warn">⚠️ 有 ' + staleCount + ' 个供应商价格超过90天未更新</div>' : '') +
      '<div class="kp-list" id="dnaList">' + _dnaRows(items) + '</div>';
  }

  function _dnaRows(items) {
    if (!items.length) return '<div class="kp-empty">暂无数据</div>';
    return items.map(function(e) {
      return '<div class="kp-row">' +
        '<div class="kp-row-tags">' + e.tags.map(function(t) { return '<span class="tag">' + esc(t) + '</span>'; }).join('') + '</div>' +
        '<div class="kp-row-content">' + esc((e.content || '').slice(0, 80)) + '</div>' +
        '<div class="kp-row-meta">使用 ' + (e.usedCount || 0) + ' 次 · ' + (e.source || '') + '</div>' +
        '<button class="btn btn-xs btn-danger" onclick="KnowledgePanel.deleteDNA(\'' + e.id + '\')">删除</button>' +
        '</div>';
    }).join('');
  }

  function _renderSupply() {
    var stale = SupplyRAG.getStaleList();
    return '<div class="kp-toolbar">' +
      '<input id="supplySearch" placeholder="搜索供应商…" oninput="KnowledgePanel.searchSupply(this.value)" style="flex:1">' +
      '<button class="btn btn-sm btn-primary" onclick="KnowledgePanel.addSupplier()">+ 新增</button>' +
      '</div>' +
      (stale.length ? '<div class="kp-warn">⚠️ 以下供应商价格超过90天：' + stale.map(function(s) { return s.name; }).join('、') + '</div>' : '') +
      '<div class="kp-list">' +
      S.suppliers.map(function(s) {
        var isStale = SupplyRAG.isStale(s);
        return '<div class="kp-row' + (isStale ? ' kp-row-stale' : '') + '">' +
          '<strong>' + esc(s.name) + '</strong> <span class="tag">' + esc(s.category) + '</span>' +
          '<span style="margin-left:8px">' + esc(s.priceRange) + '</span>' +
          (isStale ? ' <span class="warn-badge">⚠️价格过期</span>' : '') +
          '<div style="margin-top:4px;display:flex;gap:6px">' +
          '<input id="price-' + s.id + '" value="' + esc(s.priceRange) + '" style="width:120px" placeholder="更新价格">' +
          '<button class="btn btn-xs btn-outline" onclick="KnowledgePanel.updatePrice(\'' + s.id + '\')">更新</button>' +
          '<button class="btn btn-xs btn-danger" onclick="KnowledgePanel.deleteSupplier(\'' + s.id + '\')">删除</button>' +
          '</div></div>';
      }).join('') +
      '</div>';
  }

  function _renderComm() {
    return '<div class="kp-toolbar">' +
      '<button class="btn btn-sm btn-primary" onclick="KnowledgePanel.addComm()">+ 新增话术</button>' +
      '</div>' +
      '<div class="kp-list">' +
      S.commLogic.map(function(e) {
        return '<div class="kp-row' + (e.disabled ? ' kp-row-disabled' : '') + '">' +
          '<div class="kp-row-tags"><span class="tag">' + esc(e.scenario) + '</span>' +
          e.tags.map(function(t) { return '<span class="tag">' + esc(t) + '</span>'; }).join('') +
          (e.disabled ? ' <span class="warn-badge">已禁用</span>' : '') + '</div>' +
          '<div class="kp-row-content">' + esc((e.script || '').slice(0, 100)) + '</div>' +
          '<div style="display:flex;gap:6px;margin-top:4px">' +
          (!e.disabled ? '<button class="btn btn-xs btn-danger" onclick="KnowledgePanel.disableComm(\'' + e.id + '\')">禁用</button>' : '') +
          '<button class="btn btn-xs btn-outline" onclick="KnowledgePanel.deleteComm(\'' + e.id + '\')">删除</button>' +
          '</div></div>';
      }).join('') +
      '</div>';
  }

  function _renderRefute() {
    return '<div class="kp-toolbar">' +
      '<button class="btn btn-sm btn-primary" onclick="KnowledgePanel.addRefute()">+ 新增红线</button>' +
      '</div>' +
      '<div class="kp-list">' +
      S.refutations.map(function(e) {
        return '<div class="kp-row">' +
          '<span class="tag tag-danger">' + esc(e.category) + '</span>' +
          '<div><strong>异议：</strong>' + esc(e.objection) + '</div>' +
          '<div><strong>应对：</strong>' + esc(e.response) + '</div>' +
          '<button class="btn btn-xs btn-danger" onclick="KnowledgePanel.deleteRefute(\'' + e.id + '\')">删除</button>' +
          '</div>';
      }).join('') +
      '</div>';
  }

  function _renderTemplate() {
    return '<div class="kp-toolbar">' +
      '<span style="color:var(--text-dim);font-size:12px">完成项目后可将博弈逻辑提炼为模板</span>' +
      '<button class="btn btn-sm btn-primary" onclick="KnowledgePanel.saveAsTemplate()">💾 保存当前项目为模板</button>' +
      '</div>' +
      '<div class="kp-list">' +
      (S.templates.length ? S.templates.map(function(t) {
        return '<div class="kp-row">' +
          '<strong>' + esc(t.name) + '</strong>' +
          '<span class="tag">' + esc(t.clientType || '') + '</span>' +
          '<span class="tag">¥' + fmt(t.budget || 0) + '</span>' +
          '<div style="display:flex;gap:6px;margin-top:4px">' +
          '<button class="btn btn-xs btn-primary" onclick="KnowledgePanel.applyTemplate(\'' + t.id + '\')">套用</button>' +
          '<button class="btn btn-xs btn-danger" onclick="KnowledgePanel.deleteTemplate(\'' + t.id + '\')">删除</button>' +
          '</div></div>';
      }).join('') : '<div class="kp-empty">暂无模板</div>') +
      '</div>';
  }

  function _renderPersona() {
    return '<div class="kp-list">' +
      (S.clientPersonas.length ? S.clientPersonas.map(function(p) {
        return '<div class="kp-row">' +
          '<strong>' + esc(p.name) + '</strong>' +
          p.tags.map(function(t) { return '<span class="tag">' + esc(t) + '</span>'; }).join('') +
          '<div style="font-size:11px;color:var(--text-dim)">关联项目：' + (p.projectIds || []).length + ' 个</div>' +
          '</div>';
      }).join('') : '<div class="kp-empty">客户画像将在项目完成后自动积累</div>') +
      '</div>';
  }

  return {
    render: function() {
      var el = document.getElementById('knowledgePanel'); if (!el) return;
      var content = '';
      switch (_activeTab) {
        case 'dna':      content = _renderDNA();      break;
        case 'refute':   content = _renderRefute();   break;
        case 'supply':   content = _renderSupply();   break;
        case 'comm':     content = _renderComm();     break;
        case 'template': content = _renderTemplate(); break;
        case 'persona':  content = _renderPersona();  break;
      }
      el.innerHTML = _renderTabs() + content;
    },

    switchTab: function(tab) { _activeTab = tab; this.render(); },

    searchDNA: function(q) {
      var results = q ? DNAStore.search(q, 50) : S.designDNA;
      var list = document.getElementById('dnaList');
      if (list) list.innerHTML = _dnaRows(results);
    },

    searchSupply: function(q) {
      _activeTab = 'supply';
      this.render();
    },

    deleteDNA: function(id) {
      S.designDNA = S.designDNA.filter(function(e) { return e.id !== id; });
      Storage.saveKnowledge(); this.render();
    },

    deleteSupplier: function(id) {
      S.suppliers = S.suppliers.filter(function(e) { return e.id !== id; });
      Storage.saveKnowledge(); this.render();
    },

    updatePrice: function(id) {
      var input = document.getElementById('price-' + id);
      if (input) { SupplyRAG.updatePrice(id, input.value.trim()); showToast('价格已更新'); this.render(); }
    },

    disableComm: function(id) { CommLogic.disable(id, '手动禁用'); this.render(); },

    deleteComm: function(id) {
      S.commLogic = S.commLogic.filter(function(e) { return e.id !== id; });
      Storage.saveKnowledge(); this.render();
    },

    deleteRefute: function(id) {
      S.refutations = S.refutations.filter(function(e) { return e.id !== id; });
      Storage.saveKnowledge(); this.render();
    },

    addRefute: function() {
      var obj = prompt('异议内容：'); if (!obj) return;
      var res = prompt('应对话术：'); if (!res) return;
      var cat = prompt('分类（如：价格异议/工期异议）：') || '其他';
      RefutationDB.add({ objection: obj, response: res, category: cat });
      this.render();
    },

    addComm: function() {
      var scenario = prompt('场景描述：'); if (!scenario) return;
      var script = prompt('话术内容：'); if (!script) return;
      CommLogic.add({ scenario: scenario, script: script, tags: [] });
      this.render();
    },

    addSupplier: function() {
      var name = prompt('供应商名称：'); if (!name) return;
      var cat  = prompt('品类（如：石材/地板）：') || '其他';
      var price = prompt('价格区间（如：200-400元/㎡）：') || '';
      SupplyRAG.add({ name: name, category: cat, priceRange: price, notes: '' });
      this.render();
    },

    importCSV: function() {
      var input = document.createElement('input');
      input.type = 'file'; input.accept = '.csv';
      input.onchange = function(e) {
        var file = e.target.files[0]; if (!file) return;
        var reader = new FileReader();
        reader.onload = function(ev) {
          var count = ImageTagger.importFromCSV(ev.target.result);
          showToast('已导入 ' + count + ' 条设计DNA');
          KnowledgePanel.render();
        };
        reader.readAsText(file, 'utf-8');
      };
      input.click();
    },

    saveAsTemplate: function() {
      if (!S.currentProject || !S.debateLog.length) { showToast('请先完成项目博弈'); return; }
      var name = prompt('模板名称：', S.currentProject.name + ' 模板'); if (!name) return;
      var tpl = {
        id: uid(), name: name,
        clientType: (S.currentProject.clientTags || []).join('、'),
        budget: S.currentProject.budget,
        debateLog: S.debateLog,
        createdAt: Date.now()
      };
      S.templates.push(tpl);
      Storage.saveKnowledge();
      showToast('模板已保存');
      this.render();
    },

    applyTemplate: function(id) {
      var tpl = S.templates.find(function(t) { return t.id === id; });
      if (!tpl) return;
      if (!confirm('套用模板"' + tpl.name + '"？将覆盖当前博弈记录。')) return;
      S.debateLog = tpl.debateLog.slice();
      Storage.saveCurrentProject();
      showToast('模板已套用，可直接 /generate 或 /story_pitch');
    },

    deleteTemplate: function(id) {
      S.templates = S.templates.filter(function(t) { return t.id !== id; });
      Storage.saveKnowledge(); this.render();
    }
  };
})();
