var HabitChecker = (function() {
  // 用户习惯 → 设计方案冲突检测规则
  var CONFLICT_RULES = [
    { habit: '不爱打扫', conflicts: ['开敞书架', '格栅', '开放式储物', '无门柜'], hint: '业主不爱打扫，开敞储物会积灰，建议改为有门柜体' },
    { habit: '养宠',     conflicts: ['微水泥地面', '实木地板', '丝绸', '棉麻地毯'], hint: '业主养宠物，该材料易被抓花或沾毛，建议耐磨替代方案' },
    { habit: '有娃',     conflicts: ['玻璃隔断', '尖角家具', '高台阶', '开放楼梯'], hint: '业主有小孩，存在安全隐患，建议圆角处理或增加防护' },
    { habit: '晚睡',     conflicts: ['卧室大窗', '无遮光帘', '东向卧室'], hint: '业主有晚睡习惯，卧室需配置遮光窗帘，避免早晨光线干扰' },
    { habit: '在家办公', conflicts: ['开放式书房', '无隔音'], hint: '业主在家办公，建议书房做隔音处理，避免干扰' },
    { habit: '爱做饭',   conflicts: ['开放式厨房', '无强排风'], hint: '业主爱做饭，开放式厨房油烟问题严重，必须配置强力排烟系统' },
    { habit: '喜欢喝茶', conflicts: ['无茶水区', '无储水柜'], hint: '业主喜欢喝茶，建议在客厅或书房规划专属茶水区' },
    { habit: '收藏多',   conflicts: ['无展示柜', '储物不足'], hint: '业主收藏多，需规划足够的展示和储物空间' }
  ];

  return {
    check: function(userHabits, proposalText) {
      userHabits = userHabits || [];
      var conflicts = [];
      CONFLICT_RULES.forEach(function(rule) {
        if (!userHabits.some(function(h) { return h.includes(rule.habit); })) return;
        rule.conflicts.forEach(function(c) {
          if (proposalText.includes(c)) {
            conflicts.push({ habit: rule.habit, conflict: c, hint: rule.hint });
          }
        });
      });
      return conflicts;
    },

    buildReport: function(userHabits, proposalText) {
      var conflicts = this.check(userHabits, proposalText);
      if (!conflicts.length) return '';
      return '\n\n## 🚨 生活习惯冲突\n' + conflicts.map(function(c) {
        return '- [' + c.habit + '] "' + c.conflict + '" → ' + c.hint;
      }).join('\n');
    }
  };
})();
