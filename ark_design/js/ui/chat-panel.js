var ChatPanel = (function() {
  var _el = null;

  function _getEl() { return _el || (_el = document.getElementById('chatMessages')); }

  function _bubble(agent, content, isStreaming) {
    var labels = {
      user: '李老师', orchestrator: '首席助理',
      'visual-expert': '审美专家', 'construction-mgr': '硬核执行官',
      'cost-controller': '精算专家', 'virtual-client': '刁钻客户',
      'narrative-architect': '叙事架构师', system: '系统'
    };
    var colors = {
      user: '#4a9eff', orchestrator: '#888',
      'visual-expert': '#7c6af7', 'construction-mgr': '#e05c5c',
      'cost-controller': '#e8a838', 'virtual-client': '#4caf8a',
      'narrative-architect': '#c084fc', system: '#666'
    };
    var label = labels[agent] || agent;
    var color = colors[agent] || '#888';
    var isUser = agent === 'user';

    var div = document.createElement('div');
    div.className = 'chat-bubble' + (isUser ? ' chat-bubble-user' : '') + (isStreaming ? ' streaming' : '');
    div.innerHTML =
      '<div class="bubble-header" style="color:' + color + '">' + esc(label) + '</div>' +
      '<div class="bubble-content" id="bubble-' + uid() + '">' + _renderMd(content) + '</div>';
    return div;
  }

  function _renderMd(text) {
    // 简单 Markdown 渲染：粗体、代码、换行
    return esc(text)
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  return {
    init: function() { _el = document.getElementById('chatMessages'); },

    addMessage: function(agent, content) {
      var el = _getEl(); if (!el) return null;
      var bubble = _bubble(agent, content, false);
      el.appendChild(bubble);
      el.scrollTop = el.scrollHeight;
      return bubble;
    },

    startStream: function(agent) {
      var el = _getEl(); if (!el) return null;
      var bubble = _bubble(agent, '', true);
      var contentEl = bubble.querySelector('.bubble-content');
      el.appendChild(bubble);
      el.scrollTop = el.scrollHeight;
      var full = '';
      return {
        append: function(chunk) {
          full += chunk;
          contentEl.innerHTML = _renderMd(full);
          el.scrollTop = el.scrollHeight;
        },
        finish: function() {
          bubble.classList.remove('streaming');
          return full;
        }
      };
    },

    addSystem: function(msg) { this.addMessage('system', msg); },

    clear: function() { var el = _getEl(); if (el) el.innerHTML = ''; },

    // 话术纠错提示
    showCorrectionPrompt: function(badText) {
      var el = _getEl(); if (!el) return;
      var div = document.createElement('div');
      div.className = 'correction-prompt';
      div.innerHTML =
        '<div class="correction-header">⚠️ 检测到话术纠错信号</div>' +
        '<div class="correction-body">刚才的表达方式已标记。请示范一句"正确的人话"，我会永久存入模仿库：</div>' +
        '<div class="correction-input-row">' +
        '<input id="correctionInput" placeholder="示范正确表达..." style="flex:1">' +
        '<button onclick="ChatPanel.saveCorrection()">存入模仿库</button>' +
        '</div>';
      el.appendChild(div);
      el.scrollTop = el.scrollHeight;
    },

    saveCorrection: function() {
      var input = document.getElementById('correctionInput');
      if (!input || !input.value.trim()) return;
      CommLogic.add({ scenario: '李老师示范', script: input.value.trim(), tags: ['模仿库', '李老师风格'] });
      showToast('已存入模仿库');
      var prompt = document.querySelector('.correction-prompt');
      if (prompt) prompt.remove();
    }
  };
})();
