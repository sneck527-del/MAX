var Storage = (function() {
  var PREFIX = 'ark_';

  function save(key, val) {
    try { localStorage.setItem(PREFIX + key, JSON.stringify(val)); } catch(e) { console.error('[Storage] save failed:', key, e); }
  }
  function load(key, def) {
    try { var v = localStorage.getItem(PREFIX + key); return v ? JSON.parse(v) : def; } catch(e) { return def; }
  }

  return {
    saveSettings: function() {
      var enc = Encryption.encryptSensitiveFields({
        apiProvider: S.apiProvider,
        apiUrl: S.apiUrl,
        apiKey: S.apiKey,
        apiModel: S.apiModel,
        qwenApiKey: S.qwenApiKey
      });
      save('settings', enc);
    },
    loadSettings: function() {
      var s = Encryption.decryptSensitiveFields(load('settings', {}));
      if (s.apiProvider) S.apiProvider = s.apiProvider;
      if (s.apiUrl)      S.apiUrl      = s.apiUrl;
      if (s.apiKey)      S.apiKey      = s.apiKey;
      if (s.apiModel)    S.apiModel    = s.apiModel;
      if (s.qwenApiKey)  S.qwenApiKey  = s.qwenApiKey;
    },
    saveProjects: function() { save('projects', S.projects); },
    loadProjects: function() { S.projects = load('projects', []); },
    saveKnowledge: function() {
      save('dna',       S.designDNA);
      save('refute',    S.refutations);
      save('supply',    S.suppliers);
      save('comm',      S.commLogic);
      save('rules',     S.aestheticRules);
      save('templates', S.templates);
      save('personas',  S.clientPersonas);
    },
    loadKnowledge: function() {
      S.designDNA      = load('dna',       []);
      S.refutations    = load('refute',    []);
      S.suppliers      = load('supply',    []);
      S.commLogic      = load('comm',      []);
      S.aestheticRules = load('rules',     []);
      S.templates      = load('templates', []);
      S.clientPersonas = load('personas',  []);
    },
    // 当前项目的 debateLog 持久化到 projects 数组里
    saveCurrentProject: function() {
      if (!S.currentProject) return;
      S.currentProject.debateLog = S.debateLog;
      var idx = S.projects.findIndex(function(p) { return p.id === S.currentProject.id; });
      if (idx >= 0) S.projects[idx] = S.currentProject;
      else S.projects.push(S.currentProject);
      save('projects', S.projects);
    },
    loadAll: function() {
      this.loadSettings();
      this.loadProjects();
      this.loadKnowledge();
    }
  };
})();
