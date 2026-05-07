var CinemaMode = (function() {
  var _el = null;
  var _acts = [];
  var _currentAct = 0;

  function _getEl() { return _el || (_el = document.getElementById('cinemaMode')); }

  function _buildActs(project, debateLog) {
    var vp = VisualBridge.fromDebateLog(debateLog);
    var habits = (project && project.userHabits) || [];

    return [
      {
        id: 'origin',
        title: '第一幕 · 溯源',
        subtitle: '听见空间的回响',
        content: _buildOriginContent(project, debateLog),
        color: '#1a1a2e',
        accent: '#7c6af7'
      },
      {
        id: 'concept',
        title: '第二幕 · 破题',
        subtitle: '逻辑的诗意',
        content: _buildConceptContent(debateLog, vp),
        color: '#0d1117',
        accent: '#c084fc'
      },
      {
        id: 'crucible',
        title: '第三幕 · 淬炼',
        subtitle: '为了1%的极致',
        content: _buildCrucibleContent(debateLog),
        color: '#0a0a0a',
        accent: '#e05c5c'
      },
      {
        id: 'manifestation',
        title: '第四幕 · 显现',
        subtitle: '触手可及的未来',
        content: _buildManifestContent(project, vp),
        color: '#0d1a0d',
        accent: '#4caf8a'
      }
    ];
  }

  function _buildOriginContent(project, debateLog) {
    var habits = (project && project.userHabits) || [];
    var clientEntry = (debateLog || []).find(function(e) { return e.agent === 'virtual-client'; });
    var conflict = clientEntry ? clientEntry.content.split('\n')[0].slice(0, 120) : '渴望品质与现实之间的张力。';
    return '<p class="cinema-lead">' + esc(project.brief || '一个关于回家的故事') + '</p>' +
      (habits.length ? '<ul class="cinema-list">' + habits.map(function(h) { return '<li>' + esc(h) + '</li>'; }).join('') + '</ul>' : '') +
      '<blockquote class="cinema-quote">' + esc(conflict) + '</blockquote>';
  }

  function _buildConceptContent(debateLog, vp) {
    var visualEntry = (debateLog || []).find(function(e) { return e.agent === 'visual-expert'; });
    var tags = visualEntry ? (visualEntry.content.match(/\[[^\]]+\]/g) || []).slice(0, 6) : [];
    return '<div class="cinema-tags">' + tags.map(function(t) { return '<span class="cinema-tag">' + esc(t) + '</span>'; }).join('') + '</div>' +
      '<p class="cinema-desc">' + esc(vp.description || '材质的对白，光影的刻度，空间的呼吸感。') + '</p>' +
      (visualEntry ? '<p class="cinema-body">' + esc(visualEntry.content.split('\n').slice(0, 3).join(' ')) + '</p>' : '');
  }

  function _buildCrucibleContent(debateLog) {
    var realistEntry = (debateLog || []).find(function(e) { return e.agent === 'construction-mgr'; });
    var rejections = realistEntry ? realistEntry.content.split('\n').filter(function(l) { return l.includes('🔴') || l.includes('驳回'); }).slice(0, 3) : [];
    return '<p class="cinema-lead">我们否决了更简单的做法，只为保留那一道光影的细腻。</p>' +
      (rejections.length ? '<ul class="cinema-list">' + rejections.map(function(r) { return '<li>' + esc(r) + '</li>'; }).join('') + '</ul>' : '<p class="cinema-body">所有节点经过严格技术审核。</p>');
  }

  function _buildManifestContent(project, vp) {
    var budget = (project && project.budget) ? '¥' + fmt(project.budget) : '待定';
    var material = (vp.materials && vp.materials[0]) || '木地板';
    var lighting = (vp.lightings && vp.lightings[0]) || '自然光';
    return '<p class="cinema-lead">下午四点，' + esc(lighting) + '穿过格栅，落在' + esc(material) + '上。</p>' +
      '<p class="cinema-body">这是属于您的空间，每一天都会有这样的时刻。</p>' +
      '<div class="cinema-budget">预算 ' + esc(budget) + ' · 本地服务商匹配 · 交付标准明确</div>';
  }

  function _renderAct(act) {
    return '<div class="cinema-act" style="background:' + act.color + '">' +
      '<div class="cinema-act-inner">' +
      '<div class="cinema-act-title" style="color:' + act.accent + '">' + esc(act.title) + '</div>' +
      '<div class="cinema-act-subtitle">' + esc(act.subtitle) + '</div>' +
      '<div class="cinema-act-content">' + act.content + '</div>' +
      '</div>' +
      '<div class="cinema-nav">' +
      (_currentAct > 0 ? '<button class="cinema-btn" onclick="CinemaMode.prev()">← 上一幕</button>' : '<span></span>') +
      '<span class="cinema-progress">' + (_currentAct + 1) + ' / ' + _acts.length + '</span>' +
      (_currentAct < _acts.length - 1 ? '<button class="cinema-btn" onclick="CinemaMode.next()">下一幕 →</button>' :
        '<button class="cinema-btn cinema-btn-exit" onclick="CinemaMode.exit()">退出预览</button>') +
      '</div>' +
      '</div>';
  }

  return {
    open: function(project, debateLog) {
      _acts = _buildActs(project, debateLog);
      _currentAct = 0;
      var el = _getEl(); if (!el) return;
      el.style.display = 'flex';
      el.innerHTML = _renderAct(_acts[_currentAct]);
      document.body.style.overflow = 'hidden';
    },

    next: function() {
      if (_currentAct < _acts.length - 1) {
        _currentAct++;
        var el = _getEl(); if (!el) return;
        el.innerHTML = _renderAct(_acts[_currentAct]);
      }
    },

    prev: function() {
      if (_currentAct > 0) {
        _currentAct--;
        var el = _getEl(); if (!el) return;
        el.innerHTML = _renderAct(_acts[_currentAct]);
      }
    },

    exit: function() {
      var el = _getEl(); if (!el) return;
      el.style.display = 'none';
      document.body.style.overflow = '';
    }
  };
})();
