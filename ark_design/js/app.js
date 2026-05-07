var App = (function() {

  // ── 种子数据 ──────────────────────────────────────────────
  function _loadSeeds() {
    var promises = [];
    if (!S.designDNA.length)
      promises.push(fetch('data/dna-seed.json').then(function(r){return r.json();}).then(function(d){S.designDNA=d;}).catch(function(){}));
    if (!S.refutations.length)
      promises.push(fetch('data/refutation-seed.json').then(function(r){return r.json();}).then(function(d){S.refutations=d;}).catch(function(){}));
    if (!S.aestheticRules.length)
      promises.push(fetch('data/aesthetic-rules.json').then(function(r){return r.json();}).then(function(d){S.aestheticRules=d;}).catch(function(){}));
    if (!S.commLogic.length)
      promises.push(fetch('data/comm-seed.json').then(function(r){return r.json();}).then(function(d){S.commLogic=d;}).catch(function(){}));
    return Promise.all(promises).then(function(){if(promises.length)Storage.saveKnowledge();});
  }

  // ── 视图切换 ──────────────────────────────────────────────
  function _switchView(view) {
    S.activeView = view;
    document.querySelectorAll('.view-panel').forEach(function(el){el.style.display='none';});
    document.querySelectorAll('.nav-btn').forEach(function(el){el.classList.remove('active');});
    var panel = document.getElementById('view-'+view);
    if (panel) panel.style.display = 'flex';
    var btn = document.querySelector('[data-view="'+view+'"]');
    if (btn) btn.classList.add('active');
    if (view==='knowledge') KnowledgePanel.render();
    if (view==='archive')   ArchivePanel.render();
  }

  // ── 项目 ──────────────────────────────────────────────────
  function _updateProjectHeader() {
    var el = document.getElementById('projectTitle');
    if (el) el.textContent = S.currentProject ? S.currentProject.name : '未选择项目';
  }

  function _startNewProject() {
    document.getElementById('newProjectModal').style.display = 'flex';
    document.getElementById('npName').focus();
  }

  function _submitNewProject() {
    var name    = (document.getElementById('npName').value   ||'').trim();
    var brief   = (document.getElementById('npBrief').value  ||'').trim();
    var area    = parseFloat(document.getElementById('npArea').value)   ||0;
    var budget  = parseFloat(document.getElementById('npBudget').value) ||0;
    var tagsRaw = (document.getElementById('npTags').value   ||'').trim();
    var habRaw  = (document.getElementById('npHabits').value ||'').trim();
    var spaceType = document.getElementById('npSpaceType').value;
    var city      = (document.getElementById('npCity').value    ||'').trim();
    var regionRaw = (document.getElementById('npRegion').value  ||'').trim();
    var fundingRaw = (document.getElementById('npFunding').value ||'').trim();
    if (!name) { showToast('请填写项目名称','error'); return; }
    var fundingPhases = fundingRaw ? fundingRaw.split(/[，,、\s]+/).filter(Boolean).map(function(s){
      var n = parseFloat(s.replace(/万/g,'0000'));
      return isNaN(n) ? 0 : n;
    }) : [];
    S.currentProject = {
      id: uid(), name: name, brief: brief, area: area, budget: budget,
      spaceType: spaceType, city: city,
      regionFeatures: regionRaw,
      fundingPhases: fundingPhases,
      clientTags: tagsRaw ? tagsRaw.split(/[，,、\s]+/).filter(Boolean) : [],
      userHabits: habRaw  ? habRaw.split(/[，,、\s]+/).filter(Boolean)  : [],
      createdAt: Date.now(), debateLog: []
    };
    S.debateLog = [];
    S.chatHistory = [];
    Storage.saveCurrentProject();
    document.getElementById('newProjectModal').style.display = 'none';
    ['npName','npBrief','npArea','npBudget','npTags','npHabits','npCity','npRegion','npFunding'].forEach(function(id){
      var el=document.getElementById(id); if(el) el.value='';
    });
    _updateProjectHeader();
    _renderProjectList();
    _switchView('chat');
    var typeLabel = (S.SPACE_TYPES[spaceType] || {}).label || spaceType;
    var msg = '项目「'+name+'」（'+typeLabel+'）已创建。预算 ¥'+fmt(budget)+'，面积 '+area+'㎡，'+city;
    if (fundingPhases.length) {
      msg += '\n资金分期：'+fundingPhases.map(function(v,i){ return '第'+(i+1)+'期 ¥'+fmt(v); }).join(' → ');
    }
    msg += '\n输入 /generate 开始博弈，或直接告诉我您的想法。';
    ChatPanel.clear();
    DebatePanel.clear();
    ChatPanel.addSystem(msg);
  }

  // ── UI 辅助 ───────────────────────────────────────────────
  function _setGeneratingUI(on) {
    var btn    = document.getElementById('sendBtn');
    var inp    = document.getElementById('chatInput');
    var stopBtn = document.getElementById('stopBtn');
    if (btn)    { btn.disabled = on; btn.textContent = on ? '生成中…' : '发送'; }
    if (inp)    inp.disabled = on;
    if (stopBtn) stopBtn.style.display = on ? 'inline-flex' : 'none';
  }

  function _autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  // ── 发送消息 ──────────────────────────────────────────────
  function _sendMessage() {
    var input = document.getElementById('chatInput');
    if (!input) return;
    var text = input.value.trim();
    if (!text || S.isGenerating) return;
    input.value = '';
    _autoResize(input);

    var t = text.trim();
    if (t === '/new_project' || t.startsWith('/new_project ')) { _startNewProject(); return; }
    if (t === '/generate')    { ChatPanel.addMessage('user', text); _runGenerate();    return; }
    if (t === '/story_pitch') { ChatPanel.addMessage('user', text); _runStoryPitch();  return; }
    if (t === '/settings')    { _openSettings(); return; }

    ChatPanel.addMessage('user', text);
    S.isGenerating = true;
    _setGeneratingUI(true);
    var stream = ChatPanel.startStream('orchestrator');
    Orchestrator.handle(text, function(chunk){ stream.append(chunk); })
      .then(function(){ stream.finish(); })
      .catch(function(e){ stream.finish(); ChatPanel.addSystem('出错：'+(e.message||e)); })
      .finally(function(){ S.isGenerating=false; _setGeneratingUI(false); });
  }

  // ── 博弈 ──────────────────────────────────────────────────
  function _runGenerate() {
    if (!S.currentProject) { ChatPanel.addSystem('请先创建项目（/new_project）'); return; }
    _switchView('debate');
    DebatePanel.clear();
    S.debateLog = [];
    S.isGenerating = true;
    _setGeneratingUI(true);
    Orchestrator.runDebate(
      S.currentProject,
      function(step, chunk)          { DebatePanel.onChunk(step, chunk); },
      function(step, full, resumeCb) { DebatePanel.onStepEnd(step, full, resumeCb); },
      function(step)                 { DebatePanel.onStepStart(step); }
    ).then(function() {
      _archiveProject();
      _switchView('chat');
      ChatPanel.addSystem('博弈完成。输入 /story_pitch 生成四幕剧叙事，或切换到「博弈」视图查看完整记录。');
    }).catch(function(e) {
      if (e && e.name !== 'AbortError') ChatPanel.addSystem('博弈出错：'+(e.message||e));
    }).finally(function() { S.isGenerating=false; _setGeneratingUI(false); });
  }

  function _runStoryPitch() {
    if (!S.currentProject || !S.debateLog.length) {
      ChatPanel.addSystem('请先完成博弈（/generate）'); return;
    }
    S.isGenerating = true;
    _setGeneratingUI(true);
    var stream = ChatPanel.startStream('narrative-architect');
    Orchestrator.handle('/story_pitch', function(chunk){ stream.append(chunk); })
      .then(function(){ stream.finish(); })
      .catch(function(e){ stream.finish(); ChatPanel.addSystem('出错：'+(e.message||e)); })
      .finally(function(){ S.isGenerating=false; _setGeneratingUI(false); });
  }

  // ── 归档 ──────────────────────────────────────────────────
  function _archiveProject() {
    if (!S.currentProject || !S.debateLog.length) return;
    var debateMd = ArchiveManager.buildDebateLog(S.currentProject, S.debateLog);
    var pptMd    = MdExporter.compile(S.currentProject, S.debateLog);
    ClientPersona.recordFromProject(S.currentProject, S.debateLog);
    ArchiveManager.archive(S.currentProject, S.debateLog, { debate: debateMd, ppt: pptMd });
  }

  // ── 设置 ──────────────────────────────────────────────────
  function _openSettings() {
    var modal = document.getElementById('settingsModal');
    if (!modal) return;
    document.getElementById('setProvider').value = S.apiProvider || 'deepseek';
    document.getElementById('setUrl').value      = S.apiUrl      || '';
    document.getElementById('setKey').value      = S.apiKey      || '';
    document.getElementById('setModel').value    = S.apiModel    || '';
    document.getElementById('setQwenKey').value  = S.qwenApiKey  || '';
    modal.style.display = 'flex';
  }

  function _saveSettings() {
    S.apiProvider = document.getElementById('setProvider').value;
    S.apiUrl      = document.getElementById('setUrl').value.trim();
    S.apiKey      = document.getElementById('setKey').value.trim();
    S.apiModel    = document.getElementById('setModel').value.trim();
    S.qwenApiKey  = document.getElementById('setQwenKey').value.trim();
    Storage.saveSettings();
    document.getElementById('settingsModal').style.display = 'none';
    showToast('设置已保存');
  }

  function _onProviderChange() {
    var provider = document.getElementById('setProvider').value;
    var presets  = ApiClient.getPresets();
    var preset   = presets[provider];
    if (preset) {
      document.getElementById('setUrl').value   = preset.url;
      document.getElementById('setModel').value = preset.model;
    }
  }

  // ── 项目列表 ──────────────────────────────────────────────
  function _renderProjectList() {
    var el = document.getElementById('projectList');
    if (!el) return;
    if (!S.projects.length) {
      el.innerHTML = '<div class="proj-empty">暂无项目，点击「新建项目」开始</div>';
      return;
    }
    el.innerHTML = S.projects.slice().reverse().map(function(p) {
      var active = S.currentProject && S.currentProject.id === p.id;
      var typeLabel = (S.SPACE_TYPES[p.spaceType] || {}).label || '';
      return '<div class="proj-item'+(active?' proj-item-active':'')+'" onclick="App.loadProject(\''+p.id+'\')">' +
        '<div class="proj-item-name">'+esc(p.name)+'</div>' +
        '<div class="proj-item-meta">'+typeLabel+(p.city?' · '+esc(p.city):'')+' · ¥'+fmt(p.budget)+'</div>' +
        '</div>';
    }).join('');
  }

  // ── 影院模式 ──────────────────────────────────────────────
  function _openCinema() {
    if (!S.currentProject || !S.debateLog.length) { showToast('请先完成博弈'); return; }
    CinemaMode.open(S.currentProject, S.debateLog);
  }

  // ── 导出 PPT ──────────────────────────────────────────────
  function _exportPPT() {
    if (!S.currentProject || !S.debateLog.length) { showToast('请先完成博弈'); return; }
    var md = MdExporter.compile(S.currentProject, S.debateLog);
    MdExporter.download(md, (S.currentProject.name||'output') + '_PPT大纲.md');
  }

  // ── 公开 API ──────────────────────────────────────────────
  return {
    init: function() {
      Storage.loadAll();
      _loadSeeds().then(function() {
        ChatPanel.init();
        DebatePanel.init();
        ArchivePanel.init();
        MoodBoard.init();
        _updateProjectHeader();
        _renderProjectList();
        _switchView('chat');

        // 恢复最近项目
        if (S.projects.length) {
          S.currentProject = S.projects[S.projects.length - 1];
          S.debateLog = S.currentProject.debateLog || [];
          _updateProjectHeader();
          _renderProjectList();
        }

        ChatPanel.addSystem('欢迎回来，李老师。输入 /new_project 创建新项目，或 /settings 配置 API。');
      });

      // 事件绑定
      var sendBtn = document.getElementById('sendBtn');
      var input   = document.getElementById('chatInput');
      var stopBtn = document.getElementById('stopBtn');

      if (sendBtn) sendBtn.addEventListener('click', _sendMessage);
      if (input) {
        input.addEventListener('keydown', function(e) {
          if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); _sendMessage(); }
        });
        input.addEventListener('input', function() { _autoResize(this); });
      }
      if (stopBtn) stopBtn.addEventListener('click', function() {
        ApiClient.abort();
        S.isGenerating = false;
        _setGeneratingUI(false);
        showToast('已停止生成');
      });

      // 导航
      document.querySelectorAll('.nav-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          _switchView(this.dataset.view);
        });
      });

      // 新建项目按钮
      var newProjBtn = document.getElementById('newProjectBtn');
      if (newProjBtn) newProjBtn.addEventListener('click', _startNewProject);

      // 新建项目表单
      var submitBtn = document.getElementById('npSubmit');
      if (submitBtn) submitBtn.addEventListener('click', _submitNewProject);
      var cancelBtn = document.getElementById('npCancel');
      if (cancelBtn) cancelBtn.addEventListener('click', function() {
        document.getElementById('newProjectModal').style.display = 'none';
      });

      // 设置表单
      var saveSetBtn  = document.getElementById('saveSettingsBtn');
      if (saveSetBtn)  saveSetBtn.addEventListener('click', _saveSettings);
      var closeSetBtn = document.getElementById('closeSettingsBtn');
      if (closeSetBtn) closeSetBtn.addEventListener('click', function() {
        document.getElementById('settingsModal').style.display = 'none';
      });
      var providerSel = document.getElementById('setProvider');
      if (providerSel) providerSel.addEventListener('change', _onProviderChange);

      // 影院模式
      var cinemaBtn = document.getElementById('cinemaBtn');
      if (cinemaBtn) cinemaBtn.addEventListener('click', _openCinema);

      // 导出 PPT
      var exportBtn = document.getElementById('exportPptBtn');
      if (exportBtn) exportBtn.addEventListener('click', _exportPPT);

      // 情绪板上传
      var mbUpload = document.getElementById('mbUploadBtn');
      if (mbUpload) mbUpload.addEventListener('click', function() { MoodBoard.openPicker(); });

      // 快捷命令按钮
      document.querySelectorAll('.quick-cmd').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var cmd = this.dataset.cmd;
          if (!cmd) return;
          var inp = document.getElementById('chatInput');
          if (inp) { inp.value = cmd; _sendMessage(); }
        });
      });

      // 关闭 modal（点击遮罩）
      document.querySelectorAll('.modal-overlay').forEach(function(el) {
        el.addEventListener('click', function(e) {
          if (e.target === this) this.style.display = 'none';
        });
      });
    },

    switchView:       _switchView,
    startNewProject:  _startNewProject,
    submitNewProject: _submitNewProject,
    sendMessage:      _sendMessage,
    openSettings:     _openSettings,
    saveSettings:     _saveSettings,
    openCinema:       _openCinema,
    exportPPT:        _exportPPT,

    loadProject: function(id) {
      var p = S.projects.find(function(x){ return x.id===id; });
      if (!p) return;
      S.currentProject = p;
      S.debateLog = p.debateLog || [];
      S.chatHistory = [];
      _updateProjectHeader();
      _renderProjectList();
      _switchView('chat');
      ChatPanel.clear();
      ChatPanel.addSystem('已切换到项目「'+p.name+'」。');
    }
  };
})();

window.addEventListener('DOMContentLoaded', function() { App.init(); });
