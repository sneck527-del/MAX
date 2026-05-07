var ClientPersona = (function() {

  // 从项目中提取客户标签
  function _extractTags(project, debateLog) {
    var tags = (project.clientTags || []).slice();

    // 从刁钻客户的输出中提取性格标签
    var clientEntry = (debateLog || []).find(function(e) { return e.agent === 'virtual-client'; });
    if (clientEntry) {
      var content = clientEntry.content || '';
      if (content.includes('细节') || content.includes('强迫')) tags.push('细节控');
      if (content.includes('预算') || content.includes('价格') || content.includes('贵')) tags.push('预算敏感');
      if (content.includes('生活') || content.includes('体验') || content.includes('习惯')) tags.push('生活体验派');
      if (content.includes('纠结') || content.includes('换')) tags.push('审美纠结');
    }

    // 去重
    return tags.filter(function(t, i) { return tags.indexOf(t) === i; });
  }

  // 计算预算敏感度
  function _budgetSensitivity(project, debateLog) {
    var budget = project.budget || 0;
    var area   = project.area || 100;
    var perSqm = budget / area;

    if (perSqm < 1200) return 'high';   // 高度敏感
    if (perSqm < 2000) return 'medium'; // 中度敏感
    return 'low';                       // 低敏感（品质优先）
  }

  return {
    // 项目完成后自动录入画像
    recordFromProject: function(project, debateLog) {
      if (!project || !project.name) return;

      var tags = _extractTags(project, debateLog);
      var sensitivity = _budgetSensitivity(project, debateLog);

      // 查找是否已有同名客户画像
      var existing = S.clientPersonas.find(function(p) {
        return p.name === (project.clientName || project.name);
      });

      if (existing) {
        // 合并标签
        tags.forEach(function(t) {
          if (!existing.tags.includes(t)) existing.tags.push(t);
        });
        existing.projectIds = existing.projectIds || [];
        if (!existing.projectIds.includes(project.id)) existing.projectIds.push(project.id);
        existing.budgetSensitivity = sensitivity;
        existing.lastUpdated = Date.now();
      } else {
        S.clientPersonas.push({
          id: uid(),
          name: project.clientName || project.name,
          tags: tags,
          budgetSensitivity: sensitivity,
          projectIds: [project.id],
          createdAt: Date.now(),
          lastUpdated: Date.now()
        });
      }

      Storage.saveKnowledge();
    },

    // 查找相似客户画像
    findSimilar: function(tags, topN) {
      topN = topN || 3;
      return S.clientPersonas
        .map(function(p) {
          var score = (p.tags || []).filter(function(t) {
            return (tags || []).includes(t);
          }).length;
          return { persona: p, score: score };
        })
        .filter(function(r) { return r.score > 0; })
        .sort(function(a, b) { return b.score - a.score; })
        .slice(0, topN)
        .map(function(r) { return r.persona; });
    },

    // 生成虚拟客户上下文提示
    buildContext: function(clientTags) {
      var similar = this.findSimilar(clientTags, 2);
      if (!similar.length) return '';
      return '【历史相似客户参考】\n' +
        similar.map(function(p) {
          return '· ' + p.name + '（' + (p.tags || []).join('、') + '）' +
            '，预算敏感度：' + ({ high: '高', medium: '中', low: '低' }[p.budgetSensitivity] || '未知');
        }).join('\n') + '\n';
    }
  };
})();
