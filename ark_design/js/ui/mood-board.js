var MoodBoard = (function() {
  var _items = []; // [{ id, file, base64, tags, parsed, dnaId }]

  function _renderItem(item) {
    var tagsHtml = (item.tags || []).map(function(t) {
      return '<span class="mb-tag">' + esc(t) + '</span>';
    }).join('');
    return '<div class="mb-item" id="mb-' + item.id + '">' +
      '<img src="data:image/jpeg;base64,' + item.base64 + '" class="mb-img">' +
      '<div class="mb-tags">' + (item.loading ? '<span class="mb-loading">打标中…</span>' : tagsHtml) + '</div>' +
      '<button class="mb-remove" onclick="MoodBoard.removeItem(\'' + item.id + '\')">×</button>' +
      '</div>';
  }

  function _rerender() {
    var el = document.getElementById('moodBoardGrid'); if (!el) return;
    el.innerHTML = _items.map(_renderItem).join('');
  }

  function _processFile(file) {
    return new Promise(function(resolve) {
      var reader = new FileReader();
      reader.onload = function(e) {
        var img = new Image();
        img.onload = function() {
          var canvas = document.createElement('canvas');
          var ratio = Math.min(800 / img.width, 1);
          canvas.width  = Math.round(img.width  * ratio);
          canvas.height = Math.round(img.height * ratio);
          canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/jpeg', 0.8).split(',')[1]);
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  return {
    init: function() {
      var zone = document.getElementById('moodBoardZone'); if (!zone) return;

      zone.addEventListener('dragover', function(e) { e.preventDefault(); zone.classList.add('drag-over'); });
      zone.addEventListener('dragleave', function() { zone.classList.remove('drag-over'); });
      zone.addEventListener('drop', function(e) {
        e.preventDefault();
        zone.classList.remove('drag-over');
        var files = Array.from(e.dataTransfer.files).filter(function(f) { return f.type.startsWith('image/'); });
        if (files.length) MoodBoard.addFiles(files);
      });
    },

    addFiles: function(files) {
      var items = files.map(function(f) {
        return { id: uid(), file: f, base64: '', tags: [], loading: true };
      });
      _items = _items.concat(items);
      _rerender();

      // 批量打标队列
      ImageTagger.tagBatch(files, function(done, total, result) {
        var item = items[done - 1];
        if (!item) return;
        _processFile(item.file).then(function(b64) {
          item.base64  = b64;
          item.loading = false;
          if (result && !result.error) {
            item.tags  = result.tags || [];
            item.dnaId = result.dnaId;
          } else {
            item.tags = ['打标失败'];
          }
          var el = document.getElementById('mb-' + item.id);
          if (el) el.outerHTML = _renderItem(item);
        });
      }).then(function() {
        showToast('全部打标完成，共 ' + items.length + ' 张');
        MoodBoard.showConfirmBatch(items);
      });
    },

    // 批量确认写入 DNA 库
    showConfirmBatch: function(items) {
      var el = document.getElementById('moodBoardActions'); if (!el) return;
      var successItems = items.filter(function(i) { return i.dnaId; });
      el.innerHTML =
        '<div class="mb-confirm">' +
        '<span>' + successItems.length + ' 张图片已打标，确认写入设计DNA库？</span>' +
        '<button class="btn btn-primary btn-sm" onclick="MoodBoard.confirmAll()">全部写入</button>' +
        '<button class="btn btn-outline btn-sm" onclick="MoodBoard.clearConfirm()">取消</button>' +
        '</div>';
    },

    confirmAll: function() {
      Storage.saveKnowledge();
      showToast('已写入设计DNA库');
      this.clearConfirm();
    },

    clearConfirm: function() {
      var el = document.getElementById('moodBoardActions');
      if (el) el.innerHTML = '';
    },

    removeItem: function(id) {
      _items = _items.filter(function(i) { return i.id !== id; });
      _rerender();
    },

    openPicker: function() {
      var input = document.createElement('input');
      input.type = 'file'; input.accept = 'image/*'; input.multiple = true;
      input.onchange = function(e) {
        var files = Array.from(e.target.files);
        if (files.length) MoodBoard.addFiles(files);
      };
      input.click();
    },

    clear: function() { _items = []; _rerender(); }
  };
})();
