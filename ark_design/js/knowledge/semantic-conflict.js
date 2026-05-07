var SemanticConflict = (function() {
  // 审美悖论规则：[情绪标签] 与 [禁配特征] 的冲突矩阵
  var CONFLICT_RULES = [
    { emotion: '静谧', forbidden: ['高饱和', '撞色', '多色系', '荧光', '鲜艳'], hint: '静谧感与高饱和色彩冲突，建议降低色彩纯度' },
    { emotion: '秩序', forbidden: ['混搭', '多材质', '随机', '自由排列', '不规则'], hint: '秩序感要求材质克制，建议控制在3种以内' },
    { emotion: '仪式感', forbidden: ['随意', '对称破坏', '无轴线'], hint: '仪式感依赖轴线与对称，建议强化空间序列' },
    { emotion: '包裹感', forbidden: ['冷色调', '大面积留白', '高反光'], hint: '包裹感需要暖色围合，冷色调会破坏安全感' },
    { material: '皮肤感', forbidden: ['粗糙肌理', '暴露结构', '工业感'], hint: '皮肤感材质与粗犷骨架感冲突，需明确主次' },
    { material: '骨架感', forbidden: ['柔软', '圆润', '无边界'], hint: '骨架感需要硬朗线条支撑，避免过度柔化' },
    { lighting: '漫反射', forbidden: ['点光源', '射灯阵列', '高亮度'], hint: '漫反射氛围与强点光源冲突，建议隐藏光源' },
    { lighting: '戏剧光', forbidden: ['均匀照明', '无阴影', '全亮'], hint: '戏剧光依赖明暗对比，均匀照明会消解戏剧感' }
  ];

  return {
    // 检测方案文本中的审美悖论，返回冲突列表
    detect: function(proposalText, tags) {
      tags = tags || [];
      var conflicts = [];
      var text = proposalText + ' ' + tags.join(' ');

      CONFLICT_RULES.forEach(function(rule) {
        var dimension = rule.emotion || rule.material || rule.lighting;
        if (!text.includes(dimension) && !tags.some(function(t) { return t.includes(dimension); })) return;
        rule.forbidden.forEach(function(f) {
          if (text.includes(f)) {
            conflicts.push({
              dimension: dimension,
              conflict: f,
              hint: rule.hint,
              severity: 'warning'
            });
          }
        });
      });

      // 检查 aesthetic-rules.json 中的自定义红线
      S.aestheticRules.forEach(function(r) {
        if (text.includes(r.rule)) {
          conflicts.push({ dimension: '自定义红线', conflict: r.rule, hint: r.category, severity: r.severity || 'error' });
        }
      });

      return conflicts;
    },

    buildReport: function(proposalText, tags) {
      var conflicts = this.detect(proposalText, tags);
      if (!conflicts.length) return '';
      return '\n\n## ⚠️ 审美悖论预警\n' + conflicts.map(function(c) {
        var icon = c.severity === 'error' ? '🔴' : '🟡';
        return icon + ' [' + c.dimension + '] 检测到"' + c.conflict + '" → ' + c.hint;
      }).join('\n');
    }
  };
})();
