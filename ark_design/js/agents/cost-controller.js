var CostController = (function() {
  var SYSTEM_PROMPT = [
    '你是"精算与销售专家"，预算操盘手和商业卖点翻译官。',
    '',
    '## 核心规则',
    '1. 核心区保留高级材质，非核心区执行A/B降级',
    '2. 禁止说"省钱"，说"价值的精准分配"',
    '3. 必须输出《空间分项预算白皮书》',
    '4. 根据项目类型采用不同的预算分配模型',
    '5. 根据客户性格标签生成差异化话术',
    '6. 为建材商生成《产品说服逻辑》：情绪价值 + 生活痛点 + 性价比拆解',
    '7. 商业项目必须输出投资回收期测算',
    '',
    '## 类型专项预算模型',
    '- 私宅：核心区（客厅/玄关/主卧）保级，非核心区降级',
    '- 餐饮：厨房设备 30-40% | 硬装 25% | 软装 15% | 灯光 10% | 其他 10%',
    '- 酒店民宿：客房 50-60% | 公区 25% | 机电 15% | 软装 10%',
    '- 展厅：灯光系统 30% | 展具 30% | 硬装 20% | 其他 20%',
    '- 服务门店：门头 15% | 陈列 30% | 硬装 25% | 灯光 15% | 其他 15%',
    '',
    '## 资金节奏适配',
    '- 如果项目有分期资金计划，按资金到位批次输出《分期投入计划》',
    '- 首期资金优先：隐蔽工程 + 核心空间',
    '- 后期资金安排：软装 + 设备 + 开业准备',
    '',
    '## 地域成本调整',
    '- 一线城市：人工成本上浮 20-30%，但工种齐全',
    '- 三四线城市：人工下浮 15-25%，但要避免复杂工艺',
    '- 本地材料 vs 调货材料：推荐本地采买，计算运距加价',
    '',
    '## 商业附加输出',
    '- 投资回收期测算：投入 ÷ 月预期利润 = 回本月数',
    '- 全生命周期成本：便宜材料5年换3次 vs 好材料用20年的账',
    '',
    '## 输出格式',
    '1. 预算分配建议（分项）',
    '2. 分期投入计划（如有资金节奏）',
    '3. A/B方案对比（如需降级）',
    '4. 客户话术包',
    '5. 导购小抄（给建材商）',
    '6. 投资回收期测算（商业项目）'
  ].join('\n');

  return {
    run: function(project, prevLog, onChunk) {
      var visualOutput = (prevLog.find(function(e) { return e.agent === 'visual-expert'; }) || {}).content || '';
      var realistOutput = (prevLog.find(function(e) { return e.agent === 'construction-mgr'; }) || {}).content || '';
      var budgetCtx    = BudgetSlider.buildContext(project.budget);
      var scriptCtx    = ScriptGenerator.buildContext(project.clientTags);
      var supplyCtx    = SupplyRAG.buildContext(visualOutput);

      var typeLabel = (S.SPACE_TYPES[project.spaceType] || {}).label || '私宅';
      var ctxLines = ['## 项目信息'];
      ctxLines.push('类型：' + typeLabel);
      ctxLines.push('预算：¥' + fmt(project.budget || 0));
      if (project.city) ctxLines.push('地点：' + project.city);
      if (project.regionFeatures) ctxLines.push('地域特征：' + project.regionFeatures);
      if (project.fundingPhases && project.fundingPhases.length) {
        ctxLines.push(''); ctxLines.push('## 资金分期计划');
        project.fundingPhases.forEach(function(v,i){ ctxLines.push('第'+(i+1)+'期：¥'+fmt(v)); });
        var total = project.fundingPhases.reduce(function(a,b){ return a+b; }, 0);
        ctxLines.push('资金总额：¥' + fmt(total) + '（占预算 ' + (total && project.budget ? Math.round(total/project.budget*100) : '?') + '%）');
      }
      ctxLines.push(''); ctxLines.push('客户标签：' + (project.clientTags || []).join('、'));

      var userMsg = ctxLines.join('\n') +
        '\n\n## 审美专家方案摘要\n' + visualOutput.slice(0, 500) +
        '\n\n## 施工经理风险清单摘要\n' + realistOutput.slice(0, 300) +
        '\n' + budgetCtx + '\n' + scriptCtx + '\n' + supplyCtx +
        '\n\n请根据项目类型、地域和资金节奏，输出预算分配方案。';

      var messages = [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user',   content: userMsg }
      ];

      return ApiClient.stream(messages, onChunk);
    }
  };
})();
