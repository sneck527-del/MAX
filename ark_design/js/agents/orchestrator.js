var Orchestrator = (function() {
  var SYSTEM_PROMPT = [
    '你是"首席助理"，李老师的数字孪生项目经理。',
    '',
    '## 核心原则',
    '1. 说人话：禁止使用"作为AI"、"在某种程度上"、"当然"等废话',
    '2. 重逻辑：所有建议必须基于博弈结果，不随机生成',
    '3. 懂规矩：严格遵守李老师18年积累的施工红线和审美偏好',
    '',
    '## 知识库优先级',
    '1. Refutation_Database（红线，绝对不可违反）',
    '2. Design_DNA_Vector（李老师认可的审美逻辑）',
    '3. Local_Supply_RAG（本地供应商和工费参考）',
    '',
    '## 仲裁原则',
    '- 审美专家 vs 施工经理冲突：优先施工可行性，但保留核心视觉逻辑',
    '- 成本超标：执行A/B降级，核心区不降',
    '- 客户挑毛病：逐条回应，给出解决方案而非妥协',
    '',
    '## 自我进化',
    '- 如果李老师说"这不是我说话的方式"，立即记录并要求示范'
  ].join('\n');

  // 按项目类型返回辩论步骤配置
  function _getDebateSteps(spaceType) {
    var STEPS = {
      residential: [
        { id: 'visual-expert',    label: '审美专家',    color: '#7c6af7', agent: VisualExpert },
        { id: 'construction-mgr', label: '硬核执行官',  color: '#e05c5c', agent: ConstructionMgr },
        { id: 'cost-controller',  label: '精算专家',    color: '#e8a838', agent: CostController },
        { id: 'virtual-client',   label: '刁钻客户',    color: '#4caf8a', agent: VirtualClient }
      ],
      restaurant: [
        { id: 'construction-mgr', label: '硬核执行官',  color: '#e05c5c', agent: ConstructionMgr },
        { id: 'cost-controller',  label: '精算专家',    color: '#e8a838', agent: CostController },
        { id: 'visual-expert',    label: '审美专家',    color: '#7c6af7', agent: VisualExpert },
        { id: 'virtual-client',   label: '刁钻客户',    color: '#4caf8a', agent: VirtualClient }
      ],
      hotel: [
        { id: 'visual-expert',    label: '审美专家',    color: '#7c6af7', agent: VisualExpert },
        { id: 'construction-mgr', label: '硬核执行官',  color: '#e05c5c', agent: ConstructionMgr },
        { id: 'cost-controller',  label: '精算专家',    color: '#e8a838', agent: CostController },
        { id: 'virtual-client',   label: '刁钻客户',    color: '#4caf8a', agent: VirtualClient }
      ],
      exhibition: [
        { id: 'visual-expert',    label: '审美专家',    color: '#7c6af7', agent: VisualExpert },
        { id: 'cost-controller',  label: '精算专家',    color: '#e8a838', agent: CostController },
        { id: 'construction-mgr', label: '硬核执行官',  color: '#e05c5c', agent: ConstructionMgr },
        { id: 'virtual-client',   label: '刁钻客户',    color: '#4caf8a', agent: VirtualClient }
      ],
      retail: [
        { id: 'cost-controller',  label: '精算专家',    color: '#e8a838', agent: CostController },
        { id: 'visual-expert',    label: '审美专家',    color: '#7c6af7', agent: VisualExpert },
        { id: 'construction-mgr', label: '硬核执行官',  color: '#e05c5c', agent: ConstructionMgr },
        { id: 'virtual-client',   label: '刁钻客户',    color: '#4caf8a', agent: VirtualClient }
      ]
    };
    return STEPS[spaceType] || STEPS.residential;
  }

  // 构建项目上下文（类型+地域+资金）
  function _buildProjectContext(project) {
    var lines = [];
    var typeLabel = (S.SPACE_TYPES && S.SPACE_TYPES[project.spaceType] || {}).label || '';
    if (typeLabel) lines.push('项目类型：' + typeLabel);
    if (project.city) lines.push('项目地点：' + project.city);
    if (project.regionFeatures) lines.push('地域特征：' + project.regionFeatures);
    if (project.fundingPhases && project.fundingPhases.length) {
      lines.push('资金分期：' + project.fundingPhases.map(function(v,i){
        return '第'+(i+1)+'期 ¥'+fmt(v);
      }).join(' → '));
      var total = project.fundingPhases.reduce(function(a,b){ return a+b; }, 0);
      lines.push('资金总额：¥' + fmt(total));
    }
    return lines.length ? '\n## 项目全局上下文\n' + lines.join('\n') : '';
  }

  // 命令解析
  function _parseCommand(text) {
    var t = text.trim();
    if (t.startsWith('/new_project'))  return { cmd: 'new_project' };
    if (t.startsWith('/feed'))         return { cmd: 'feed', content: t.slice(5).trim() };
    if (t.startsWith('/generate'))     return { cmd: 'generate' };
    if (t.startsWith('/story_pitch'))  return { cmd: 'story_pitch' };
    if (t.startsWith('/settings'))     return { cmd: 'settings' };
    return { cmd: 'chat', content: t };
  }

  // 主对话（非命令）
  function _chat(userText, onChunk) {
    var dnaCtx     = DNAStore.buildContext(userText);
    var refuteCtx  = RefutationDB.buildContext(userText);
    var commCtx    = CommLogic.buildContext(userText);

    var messages = [
      { role: 'system', content: SYSTEM_PROMPT + dnaCtx + refuteCtx + commCtx }
    ];
    S.chatHistory.forEach(function(m) { messages.push(m); });
    messages.push({ role: 'user', content: userText });

    return ApiClient.stream(messages, onChunk).then(function(full) {
      S.chatHistory.push({ role: 'user',      content: userText });
      S.chatHistory.push({ role: 'assistant', content: full });
      if (S.chatHistory.length > 40) S.chatHistory = S.chatHistory.slice(-40);

      // 检测否定词，触发话术纠错
      if (CommLogic.detectNegation(userText)) {
        ChatPanel.showCorrectionPrompt(userText);
      }
      return full;
    });
  }

  // /feed 处理
  function _feed(content, onChunk) {
    var dnaSummary = DNAStore.getSummary(10);
    var tagged = VisualTagger.feedAndStore(content);

    var sysMsg = SYSTEM_PROMPT + '\n\n## 历史设计DNA摘要\n' + (dnaSummary || '（暂无）');
    var userMsg = [
      '李老师投喂了以下内容：',
      content,
      '',
      tagged ? '已提取标签：' + tagged.tags.join('、') : '（未提取到明确标签）',
      '',
      '请基于历史DNA摘要，提出2-3个深层专业问题，挖掘李老师的隐性经验。',
      '问题要有针对性，不要泛泛而谈。'
    ].join('\n');

    var messages = [
      { role: 'system', content: sysMsg },
      { role: 'user',   content: userMsg }
    ];
    return ApiClient.stream(messages, onChunk);
  }

  // /generate 处理
  function _generate(type, onChunk) {
    if (!S.currentProject) { showToast('请先创建或打开一个项目'); return Promise.resolve(''); }
    var debateLog = S.debateLog;

    if (type === 'ppt' || type === 'story') {
      var md = MdExporter.compile(S.currentProject, debateLog);
      if (onChunk) onChunk(md);
      return Promise.resolve(md);
    }

    var typePrompts = {
      script:    '生成客户话术包，根据客户性格标签定制，语言自然，像李老师说话。',
      craft:     '生成施工交底文件，逐项列出工艺要求和验收标准，给工人看的。',
      sales:     '生成导购小抄，给建材商用，包含情绪价值、生活痛点、性价比拆解。'
    };

    var prompt = typePrompts[type] || '生成项目总结。';
    var dnaCtx = DNAStore.buildContext(S.currentProject.brief || '');
    var debateSummary = debateLog.slice(-4).map(function(e) {
      return '【' + e.agent + '】' + (e.content || '').slice(0, 200);
    }).join('\n');

    var messages = [
      { role: 'system', content: SYSTEM_PROMPT + dnaCtx },
      { role: 'user',   content: '项目：' + S.currentProject.name + '\n\n博弈摘要：\n' + debateSummary + '\n\n' + prompt }
    ];
    return ApiClient.stream(messages, onChunk);
  }

  // /story_pitch 处理
  function _storyPitch(onChunk) {
    if (!S.currentProject || !S.debateLog.length) {
      showToast('请先完成项目博弈（/new_project）');
      return Promise.resolve('');
    }
    var projectCtx = _buildProjectContext(S.currentProject);
    return NarrativeArchitect.run(S.currentProject, S.debateLog, projectCtx, onChunk);
  }

  // 运行完整博弈流程
  function _runDebate(project, onStepStart, onChunk, onStepEnd, onPause) {
    S.debateLog = [];
    S.currentDebateStep = 0;
    S.debatePaused = false;

    var steps = _getDebateSteps(project.spaceType);
    var projectCtx = _buildProjectContext(project);

    var chain = Promise.resolve();

    steps.forEach(function(step, idx) {
      chain = chain.then(function() {
        if (S.debatePaused) {
          return new Promise(function(resolve) {
            S._debateResumeCallback = resolve;
          });
        }
        S.currentDebateStep = idx;
        if (onStepStart) onStepStart(step);

        return step.agent.run(project, S.debateLog, function(chunk) {
          if (onChunk) onChunk(step, chunk);
        }).then(function(full) {
          S.debateLog.push({ agent: step.id, content: full, timestamp: Date.now() });
          Storage.saveCurrentProject();
          if (onStepEnd) onStepEnd(step, full);

          if (onPause && idx < steps.length - 1) {
            return new Promise(function(resolve) {
              onPause(step, resolve);
            });
          }
        });
      });
    });

    // 首席助理仲裁
    chain = chain.then(function() {
      if (onStepStart) onStepStart({ id: 'orchestrator', label: '首席助理仲裁', color: '#888' });
      var debateSummary = S.debateLog.map(function(e) {
        var labels = { 'visual-expert': '审美专家', 'construction-mgr': '硬核执行官',
                       'cost-controller': '精算专家', 'virtual-client': '刁钻客户' };
        return '【' + (labels[e.agent] || e.agent) + '】\n' + (e.content || '').slice(0, 400);
      }).join('\n\n');

      var dnaCtx    = DNAStore.buildContext(project.brief || '');
      var refuteCtx = RefutationDB.buildContext(debateSummary);

      var messages = [
        { role: 'system', content: SYSTEM_PROMPT + dnaCtx + refuteCtx + projectCtx },
        { role: 'user',   content: '以下是四位专家的博弈记录，请综合考虑项目类型、地域条件和资金节奏，仲裁并输出最终方案摘要：\n\n' + debateSummary }
      ];

      return ApiClient.stream(messages, function(chunk) {
        if (onChunk) onChunk({ id: 'orchestrator', label: '首席助理', color: '#888' }, chunk);
      }).then(function(full) {
        S.debateLog.push({ agent: 'orchestrator', content: full, timestamp: Date.now() });
        Storage.saveCurrentProject();
        if (onStepEnd) onStepEnd({ id: 'orchestrator' }, full);
      });
    });

    // 自动触发叙事架构师
    chain = chain.then(function() {
      if (onStepStart) onStepStart({ id: 'narrative-architect', label: '叙事架构师', color: '#c084fc' });
      return NarrativeArchitect.run(project, S.debateLog, projectCtx, function(chunk) {
        if (onChunk) onChunk({ id: 'narrative-architect', label: '叙事架构师', color: '#c084fc' }, chunk);
      }).then(function(full) {
        S.debateLog.push({ agent: 'narrative-architect', content: full, timestamp: Date.now() });
        Storage.saveCurrentProject();
        if (onStepEnd) onStepEnd({ id: 'narrative-architect' }, full);
      });
    });

    return chain;
  }

  return {
    getDebateSteps: _getDebateSteps,
    buildProjectContext: _buildProjectContext,

    handle: function(userText, onChunk) {
      var parsed = _parseCommand(userText);
      S.isGenerating = true;

      var p;
      switch (parsed.cmd) {
        case 'new_project': p = Promise.resolve('__new_project__'); break;
        case 'feed':        p = _feed(parsed.content || userText, onChunk); break;
        case 'generate':    p = Promise.resolve('__generate__'); break;
        case 'story_pitch': p = _storyPitch(onChunk); break;
        case 'settings':    p = Promise.resolve('__settings__'); break;
        default:            p = _chat(userText, onChunk);
      }

      return p.finally(function() { S.isGenerating = false; });
    },

    runDebate: _runDebate,
    generate:  _generate,
    resumeDebate: function() {
      S.debatePaused = false;
      if (S._debateResumeCallback) { S._debateResumeCallback(); S._debateResumeCallback = null; }
    }
  };
})();
