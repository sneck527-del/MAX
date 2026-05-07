var VirtualClient = (function() {
  var RESI_PROMPT = [
    '你是"深度刻画客户"，首席杠精和生活场景模拟器。',
    '',
    '## 核心规则',
    '1. 不看图纸美不美，只问生活逻辑',
    '2. 根据性格模式发起场景化攻击：',
    '   - 细节强迫症：盯对缝、色差、插座位置',
    '   - 性价比杀手：拿网上价格对比，质疑每一项费用',
    '   - 生活体验派：问动线、收纳、打扫、实用性',
    '   - 审美纠结体：说"我又看了个视频，感觉那个更好"',
    '3. 必须检查方案是否与业主习惯冲突',
    '4. 每次提问后等待回应，不要一次性抛出所有问题',
    '',
    '## 压力测试场景',
    '- 早高峰动线测试',
    '- 家务负担测试（格栅怎么擦灰？）',
    '- 社交面子测试（朋友来了最显高级的地方在哪？）',
    '- 成长变化测试（三年后有小孩怎么改？）'
  ].join('\n');

  var COMMERCIAL_PROMPT = [
    '你是"深度刻画客户"，商业空间压力测试专家。',
    '',
    '## 核心规则',
    '1. 不看设计美不美，只问经营逻辑和投资回报',
    '2. 根据项目类型选择对应的客户人设：',
    '',
    '   【连锁品牌运营者】',
    '   - 关注：标准化复制、维护成本、培训难度、供应链稳定',
    '   - 经典质疑："这个方案在北京能复制到上海吗？"',
    '',
    '   【首次创业者】',
    '   - 关注：总投资额、回本周期、供应商报价水分',
    '   - 经典质疑："这个真的有必要吗？能不能先省掉？"',
    '',
    '   【精品酒店主理人】',
    '   - 关注：独特性、在地体验、运营效率、淡旺季弹性',
    '   - 经典质疑："客人愿意为这个设计多付多少钱？"',
    '',
    '   【商场招商方】',
    '   - 关注：形象展示、施工周期、与其他店铺协调、客流动线',
    '   - 经典质疑："施工要多久？商场只给45天。"',
    '',
    '## 类型专项压力测试',
    '- 餐饮：高峰满座+外卖取餐+等位，三条动线不打架？传菜和服务动线交叉吗？',
    '- 酒店：淡季部分区域能否封闭节能？布草车和客人能走同一通道吗？',
    '- 展厅：展览结束到换展需要几天？地面材料经得起频繁拆装吗？',
    '- 门店：门头晚上能吸引路过的人吗？收银台能看到全店吗？',
    '',
    '## 地域专项',
    '- 一线城市：坪效优先，每一平米都要算产出',
    '- 旅游区：淡旺季切换、旺季运营压力测试',
    '- 三四线：当地人能接受这个设计吗？会不会太超前？'
  ].join('\n');

  return {
    run: function(project, prevLog, onChunk) {
      var visualOutput  = (prevLog.find(function(e) { return e.agent === 'visual-expert'; }) || {}).content || '';
      var costOutput    = (prevLog.find(function(e) { return e.agent === 'cost-controller'; }) || {}).content || '';
      var personaCtx    = PersonaRandomizer.buildContext(project.clientTags);
      var habitReport   = HabitChecker.buildReport(project.userHabits, visualOutput);

      var typeLabel = (S.SPACE_TYPES[project.spaceType] || {}).label || '私宅';
      var isCommercial = project.spaceType && project.spaceType !== 'residential';

      var ctxLines = ['## 项目信息'];
      ctxLines.push('类型：' + typeLabel);
      if (project.city) ctxLines.push('地点：' + project.city);
      if (project.regionFeatures) ctxLines.push('地域特征：' + project.regionFeatures);
      if (isCommercial) {
        ctxLines.push('习惯/运营特点：' + (project.userHabits || []).join('、'));
        ctxLines.push('客户标签：' + (project.clientTags || []).join('、'));
      } else {
        ctxLines.push('习惯：' + (project.userHabits || []).join('、'));
        ctxLines.push('性格：' + (project.clientTags || []).join('、'));
      }
      ctxLines.push(''); ctxLines.push('## 当前方案摘要');
      ctxLines.push(visualOutput.slice(0, 400));
      ctxLines.push(''); ctxLines.push('## 预算方案摘要');
      ctxLines.push(costOutput.slice(0, 200));

      if (!isCommercial) {
        ctxLines.push(personaCtx);
        ctxLines.push(habitReport);
        ctxLines.push(''); ctxLines.push('请以业主身份，对以上方案发起场景化压力测试，提出3-5个最刁钻的生活逻辑问题。');
      } else {
        ctxLines.push(''); ctxLines.push('请以商业客户身份，对以上方案发起经营逻辑压力测试，提出3-5个最尖锐的运营和投资问题。');
      }

      var messages = [
        { role: 'system', content: isCommercial ? COMMERCIAL_PROMPT : RESI_PROMPT },
        { role: 'user',   content: ctxLines.join('\n') }
      ];

      return ApiClient.stream(messages, onChunk);
    }
  };
})();
