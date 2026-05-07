var DebatePanel = (function() {
  var _el = null;
  var _currentStep = null;
  var _streamEls = {};

  var AGENT_COLORS = {
    'visual-expert':      '#7c6af7',
    'construction-mgr':   '#e05c5c',
    'cost-controller':    '#e8a838',
    'virtual-client':     '#4caf8a',
    'orchestrator':       '#888',
    'narrative-architect':'#c084fc'
  };
  var AGENT_LABELS = {
    'visual-expert':      '审美专家',
    'construction-mgr':   '硬核执行官',
    'cost-controller':    '精算专家',
    'virtual-client':     '刁钻客户',
    'orchestrator':       '首席助理',
    'narrative-architect':'叙事架构师'
  };

  function _getEl() { return _el || (_el = document.getElementById('debatePanel')); }

  function _renderMd(text) {
    return esc(text)
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/🟢/g, '<span class="risk-green">🟢</span>')
      .replace(/🟡/g, '<span class="risk-yellow">🟡</span>')
      .replace(/🔴/g, '<span class="risk-red">🔴</span>')
      .replace(/\n/g, '<br>');
  }

  return {
    init: function() { _el = document.getElementById('debatePanel'); },

    clear: function() {
      var el = _getEl(); if (!el) return;
      el.innerHTML = '';
      _streamEls = {};
    },

    // 显示步骤开始
    onStepStart: function(step) {
      var el = _getEl(); if (!el) return;
      _currentStep = step;

      var card = document.createElement('div');
      card.className = 'debate-card';
      card.id = 'debate-card-' + step.id;
      card.innerHTML =
        '<div class="debate-card-header" style="border-left:3px solid ' + (AGENT_COLORS[step.id] || '#888') + '">' +
        '<span class="debate-agent-label" style="color:' + (AGENT_COLORS[step.id] || '#888') + '">' +
          esc(AGENT_LABELS[step.id] || step.label) + '</span>' +
        '<span class="debate-status streaming-dot">思考中…</span>' +
        '</div>' +
        '<div class="debate-card-body" id="debate-body-' + step.id + '"></div>' +
        '<div class="debate-card-actions" id="debate-actions-' + step.id + '" style="display:none">' +
        '<button class="btn btn-sm btn-outline" onclick="DebatePanel.continueDebate()">继续 →</button>' +
        '<button class="btn btn-sm btn-danger"  onclick="DebatePanel.interruptDebate()">打断并修正</button>' +
        '</div>';
      el.appendChild(card);
      el.scrollTop = el.scrollHeight;

      _streamEls[step.id] = document.getElementById('debate-body-' + step.id);
    },

    // 流式追加内容
    onChunk: function(step, chunk) {
      var bodyEl = _streamEls[step.id];
      if (!bodyEl) return;
      bodyEl._full = (bodyEl._full || '') + chunk;
      bodyEl.innerHTML = _renderMd(bodyEl._full);
      var el = _getEl(); if (el) el.scrollTop = el.scrollHeight;
    },

    // 步骤结束，显示暂停按钮
    onStepEnd: function(step, full, resumeCallback) {
      var card = document.getElementById('debate-card-' + step.id);
      if (card) {
        var status = card.querySelector('.debate-status');
        if (status) status.textContent = '完成';
        status && status.classList.remove('streaming-dot');
      }
      // 最后两步（orchestrator / narrative-architect）不显示暂停按钮
      if (step.id === 'orchestrator' || step.id === 'narrative-architect') return;
      var actionsEl = document.getElementById('debate-actions-' + step.id);
      if (actionsEl) {
        actionsEl.style.display = 'flex';
        actionsEl._resume = resumeCallback;
      }
    },

    continueDebate: function() {
      // 隐藏当前暂停按钮，继续博弈
      var actionsEls = document.querySelectorAll('.debate-card-actions');
      actionsEls.forEach(function(el) {
        if (el._resume) { el._resume(); el._resume = null; }
        el.style.display = 'none';
      });
      Orchestrator.resumeDebate();
    },

    interruptDebate: function() {
      // 弹出修正输入框
      var el = _getEl(); if (!el) return;
      var div = document.createElement('div');
      div.className = 'debate-interrupt';
      div.innerHTML =
        '<div class="interrupt-header">✏️ 修正方向</div>' +
        '<textarea id="interruptInput" rows="3" placeholder="告诉我哪里不对，我会注入后续Agent的上下文…"></textarea>' +
        '<div style="display:flex;gap:8px;margin-top:8px">' +
        '<button class="btn btn-primary btn-sm" onclick="DebatePanel.submitInterrupt()">注入并继续</button>' +
        '<button class="btn btn-outline btn-sm" onclick="this.closest(\'.debate-interrupt\').remove();DebatePanel.continueDebate()">取消修正</button>' +
        '</div>';
      el.appendChild(div);
      el.scrollTop = el.scrollHeight;
      document.getElementById('interruptInput').focus();
    },

    submitInterrupt: function() {
      var input = document.getElementById('interruptInput');
      if (!input || !input.value.trim()) return;
      var correction = input.value.trim();
      // 将修正内容注入 debateLog，后续 Agent 会读到
      S.debateLog.push({ agent: 'user-correction', content: '【李老师修正】' + correction, timestamp: Date.now() });
      input.closest('.debate-interrupt').remove();
      showToast('修正已注入，继续博弈');
      DebatePanel.continueDebate();
    }
  };
})();
