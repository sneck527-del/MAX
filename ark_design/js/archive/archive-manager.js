var ArchiveManager = (function() {
  var _dirHandle = null;

  function _sanitizeName(name) {
    return (name || 'unnamed').replace(/[\\/:*?"<>|]/g, '-').slice(0, 50);
  }

  function _getVersionedName(existingFiles, baseName) {
    if (!existingFiles.includes(baseName)) return baseName;
    var i = 2;
    while (existingFiles.includes(baseName.replace('.md', '_v' + i + '.md'))) i++;
    return baseName.replace('.md', '_v' + i + '.md');
  }

  return {
    // 首次使用时选择输出目录
    selectDir: async function() {
      try {
        _dirHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
        S.outputDirHandle = _dirHandle;
        showToast('输出目录已设置');
        return true;
      } catch(e) {
        if (e.name !== 'AbortError') showToast('目录选择失败：' + e.message, 'error');
        return false;
      }
    },

    // 归档当前项目的所有输出
    archive: async function(project, debateLog, outputs) {
      if (!_dirHandle && !S.outputDirHandle) {
        var ok = await this.selectDir();
        if (!ok) return;
      }
      var dir = _dirHandle || S.outputDirHandle;

      var folderName = formatDate(Date.now()) + '_' + _sanitizeName(project.name || '未命名项目');

      try {
        var projectDir = await dir.getDirectoryHandle(folderName, { create: true });

        // 获取已有文件列表（用于版本号）
        var existingFiles = [];
        for await (var entry of projectDir.values()) {
          existingFiles.push(entry.name);
        }

        var writes = [];
        Object.keys(outputs).forEach(function(key) {
          var fileNames = {
            debate:  '博弈记录.md',
            ppt:     'PPT大纲.md',
            script:  '客户话术.md',
            budget:  '预算白皮书.md',
            craft:   '施工交底.md',
            story:   '四幕剧叙事.md'
          };
          var baseName = fileNames[key] || (key + '.md');
          var fileName = _getVersionedName(existingFiles, baseName);
          existingFiles.push(fileName);
          writes.push(
            projectDir.getFileHandle(fileName, { create: true })
              .then(function(fh) { return fh.createWritable(); })
              .then(function(w) { return w.write(outputs[key]).then(function() { return w.close(); }); })
          );
        });

        await Promise.all(writes);
        showToast('已归档到 ' + folderName);
        ArchivePanel.addEntry({ id: uid(), projectName: project.name, folderName: folderName, date: formatDate(Date.now()), files: Object.keys(outputs) });
      } catch(e) {
        showToast('归档失败：' + e.message, 'error');
      }
    },

    // 生成博弈记录 MD
    buildDebateLog: function(project, debateLog) {
      var labels = { 'visual-expert': '审美专家', 'construction-mgr': '硬核执行官',
                     'cost-controller': '精算专家', 'virtual-client': '刁钻客户',
                     'orchestrator': '首席助理', 'narrative-architect': '叙事架构师',
                     'user-correction': '李老师修正' };
      return '# ' + (project.name || '未命名') + ' · 博弈记录\n\n' +
        '日期：' + formatDate(Date.now()) + '\n\n---\n\n' +
        debateLog.map(function(e) {
          return '## ' + (labels[e.agent] || e.agent) + '\n\n' + (e.content || '') + '\n\n---';
        }).join('\n\n');
    }
  };
})();
