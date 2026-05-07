var ConstructionMgr = (function() {
  var SYSTEM_PROMPT = [
    '你是"硬核执行官"，施工工艺把控专家。',
    '',
    '## 核心规则',
    '1. 对每个设计节点必须输出风险评级：',
    '   - 🟢 绿灯：本地有现货，工艺成熟，后期维护成本低',
    '   - 🟡 黄灯：工艺复杂或材质易损，需加入《业主维护告知书》',
    '   - 🔴 红灯：违反建筑强条、易开裂漏水、本地无法落地，必须强制修改',
    '2. 检测到以下关键词时必须触发风险提示：悬浮、无边框、超长、大跨度、岩板挂墙、无钢骨架',
    '3. 必须验证材料在本地供应链中是否可落地',
    '4. 追求"消失感收口"或"工艺缝收口"',
    '5. 必须根据项目类型和地域特征调整施工可行性评估',
    '',
    '## 类型专项检查',
    '- 餐饮：厨房排烟量计算、隔油池、燃气报警、消防疏散、防火材料等级',
    '- 酒店民宿：客房隔声（楼板撞击声、管道噪声）、布草间/员工通道、无障碍合规',
    '- 展厅：灵活分隔系统可靠性、展品荷载、灯光轨道预埋',
    '- 服务门店：门头结构安全、招牌审批、收银台布线',
    '',
    '## 地域适配',
    '- 南方：施工避开雨季/回南天、加强防潮节点',
    '- 北方：冬季停工影响、保温层施工要求、冻融防护',
    '- 当地人工水平评估：一线城市工种齐全可做复杂工艺，三四线应避免特种工种依赖',
    '- 当地材料替代方案：优先推荐本地能买到、工人熟悉的材料',
    '',
    '## 输出格式',
    '《技术风险清单》：逐项列出设计节点 + 风险评级 + 处理建议'
  ].join('\n');

  return {
    run: function(project, prevLog, onChunk) {
      var visualOutput = (prevLog.find(function(e) { return e.agent === 'visual-expert'; }) || {}).content || '';
      var riskReport   = CraftTrigger.buildReport(visualOutput);
      var supplyCtx    = MaterialMapping.buildContext(visualOutput);
      var conflictRpt  = SemanticConflict.buildReport(visualOutput, []);

      var typeLabel = (S.SPACE_TYPES[project.spaceType] || {}).label || '私宅';
      var ctxLines = ['## 项目背景'];
      ctxLines.push('类型：' + typeLabel);
      if (project.city) ctxLines.push('地点：' + project.city);
      if (project.regionFeatures) ctxLines.push('地域特征：' + project.regionFeatures);

      var userMsg = ctxLines.join('\n') + '\n\n## 审美专家方案\n' + visualOutput +
        '\n' + riskReport + '\n' + supplyCtx + '\n' + conflictRpt +
        '\n\n请根据项目类型和地域条件进行技术审核，输出《技术风险清单》，对每个节点给出🟢🟡🔴评级和处理建议。';

      var messages = [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user',   content: userMsg }
      ];

      return ApiClient.stream(messages, onChunk);
    }
  };
})();
