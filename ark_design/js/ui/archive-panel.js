var ArchivePanel = (function() {
  var _entries = []; // [{ id, projectName, folderName, date, files[] }]
  var _searchQ = '';

  function _load() {
    try { _entries = JSON.parse(localStorage.getItem('ark_archive_entries') || '[]'); } catch(e) { _entries = []; }
  }

  function _save() {
    localStorage.setItem('ark_archive_entries', JSON.stringify(_entries));
  }

  function _filtered() {
    if (!_searchQ) return _entries;
    var q = _searchQ.toLowerCase();
    return _entries.filter(function(e) {
      return (e.projectName || '').toLowerCase().includes(q) ||
             (e.folderName  || '').toLowerCase().includes(q);
    });
  }

  function _fileIcon(key) {
    var m = { debate: '📋', ppt: '📊', script: '💬', budget: '💰', craft: '🔧', story: '🎬' };
    return m[key] || '📄';
  }

  function _renderEntry(e) {
    var fileChips = (e.files || []).map(function(f) {
      return '<span class="ap-chip">' + _fileIcon(f) + ' ' + esc(f) + '</span>';
    }).join('');
    return '<div class="ap-entry" id="ap-' + e.id + '">' +
      '<div class="ap-entry-header">' +
        '<div class="ap-entry-title">' + esc(e.projectName || '未命名') + '</div>' +
        '<div class="ap-entry-date">' + esc(e.date || '') + '</div>' +
      '</div>' +
      '<div class="ap-entry-folder">📁 ' + esc(e.folderName || '') + '</div>' +
      '<div class="ap-entry-files">' + fileChips + '</div>' +
      '<div class="ap-entry-actions">' +
        '<button class="btn btn-xs btn-danger" onclick="ArchivePanel.deleteEntry(\'' + e.id + '\')">删除记录</button>' +
      '</div>' +
    '</div>';
  }

  function _render() {
    var el = document.getElementById('archivePanel'); if (!el) return;
    var list = _filtered();
    // 按日期分组
    var groups = {};
    list.forEach(function(e) {
      var day = (e.date || '未知日期').slice(0, 10);
      if (!groups[day]) groups[day] = [];
      groups[day].push(e);
    });
    var days = Object.keys(groups).sort(function(a, b) { return b.localeCompare(a); });

    el.innerHTML =
      '<div class="ap-toolbar">' +
        '<input id="apSearch" placeholder="搜索项目名…" value="' + esc(_searchQ) + '" oninput="ArchivePanel.search(this.value)" style="flex:1">' +
        '<button class="btn btn-sm btn-outline" onclick="ArchivePanel.selectDir()">📂 重新选择目录</button>' +
        '<button class="btn btn-sm btn-outline" onclick="ArchivePanel.exportAll()">📤 导出全部记录</button>' +
      '</div>' +
      (list.length === 0
        ? '<div class="ap-empty">暂无归档记录<br><small>完成项目博弈后将自动归档</small></div>'
        : days.map(function(day) {
            return '<div class="ap-group">' +
              '<div class="ap-group-date">' + esc(day) + '</div>' +
              groups[day].map(_renderEntry).join('') +
            '</div>';
          }).join('')
      );
  }

  _load();

  return {
    init: function() { _load(); },

    render: function() { _render(); },

    addEntry: function(entry) {
      _entries.unshift(entry);
      _save();
      _render();
    },

    deleteEntry: function(id) {
      _entries = _entries.filter(function(e) { return e.id !== id; });
      _save();
      _render();
    },

    search: function(q) {
      _searchQ = q;
      _render();
    },

    selectDir: async function() {
      await ArchiveManager.selectDir();
    },

    exportAll: function() {
      var text = JSON.stringify(_entries, null, 2);
      var blob = new Blob([text], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = 'ark_archive_' + formatDate(Date.now()) + '.json';
      a.click();
      URL.revokeObjectURL(url);
    },

    getEntries: function() { return _entries.slice(); }
  };
})();
