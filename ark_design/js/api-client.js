var ApiClient = (function() {
  var _controller = null;

  var PROVIDER_PRESETS = {
    deepseek: { url: 'https://api.deepseek.com', model: 'deepseek-chat' },
    openai:   { url: 'https://api.openai.com',   model: 'gpt-4o' },
    qwen:     { url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
    zhipu:    { url: 'https://open.bigmodel.cn',  model: 'glm-4-flash' },
    doubao:   { url: 'https://ark.cn-beijing.volces.com/api/v3', model: '' },
    ollama:   { url: 'http://localhost:11434',    model: 'qwen2.5' }
  };

  function _getEndpoint(provider, baseUrl) {
    if (provider === 'ollama') return baseUrl.replace(/\/+$/, '') + '/api/chat';
    if (provider === 'zhipu')  return baseUrl.replace(/\/+$/, '') + '/v4/chat/completions';
    return baseUrl.replace(/\/+$/, '') + '/v1/chat/completions';
  }

  return {
    getPresets: function() { return PROVIDER_PRESETS; },

    abort: function() { if (_controller) { _controller.abort(); _controller = null; } },

    // 流式调用，onChunk(text) 每次收到片段回调，返回 Promise<fullText>
    stream: function(messages, onChunk, opts) {
      opts = opts || {};
      var provider = opts.provider || S.apiProvider;
      var apiUrl   = opts.apiUrl   || S.apiUrl;
      var apiKey   = opts.apiKey   || S.apiKey;
      var model    = opts.model    || S.apiModel;

      _controller = new AbortController();

      var headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers['Authorization'] = 'Bearer ' + apiKey;

      var body = JSON.stringify({
        model: model,
        messages: messages,
        stream: true,
        temperature: opts.temperature || 0.7,
        max_tokens: opts.maxTokens || 4096
      });

      return fetch(_getEndpoint(provider, apiUrl), {
        method: 'POST',
        headers: headers,
        body: body,
        signal: _controller.signal
      }).then(function(res) {
        if (!res.ok) return res.text().then(function(t) { throw new Error('API错误 ' + res.status + ': ' + t); });
        var reader = res.body.getReader();
        var decoder = new TextDecoder();
        var full = '';

        function read() {
          return reader.read().then(function(r) {
            if (r.done) return full;
            var lines = decoder.decode(r.value, { stream: true }).split('\n');
            lines.forEach(function(line) {
              line = line.trim();
              if (!line || line === 'data: [DONE]') return;
              if (line.startsWith('data: ')) {
                try {
                  var json = JSON.parse(line.slice(6));
                  var delta = (json.choices && json.choices[0] && json.choices[0].delta && json.choices[0].delta.content) || '';
                  if (delta) { full += delta; if (onChunk) onChunk(delta); }
                } catch(e) {}
              }
            });
            return read();
          });
        }
        return read();
      });
    },

    // 非流式单次调用（用于打标、冲突检测等）
    call: function(messages, opts) {
      opts = opts || {};
      var provider = opts.provider || S.apiProvider;
      var apiUrl   = opts.apiUrl   || S.apiUrl;
      var apiKey   = opts.apiKey   || S.apiKey;
      var model    = opts.model    || S.apiModel;

      var headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers['Authorization'] = 'Bearer ' + apiKey;

      return fetch(_getEndpoint(provider, apiUrl), {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ model: model, messages: messages, stream: false, temperature: 0.3 })
      }).then(function(res) {
        if (!res.ok) return res.text().then(function(t) { throw new Error('API错误 ' + res.status + ': ' + t); });
        return res.json();
      }).then(function(json) {
        return (json.choices && json.choices[0] && json.choices[0].message && json.choices[0].message.content) || '';
      });
    },

    // Qwen 视觉调用（图像打标专用）
    callVision: function(base64Image, prompt) {
      var apiKey = S.qwenApiKey || S.apiKey;
      return fetch('https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
        body: JSON.stringify({
          model: 'qwen-vl-plus',
          messages: [{ role: 'user', content: [
            { type: 'image_url', image_url: { url: 'data:image/jpeg;base64,' + base64Image } },
            { type: 'text', text: prompt }
          ]}],
          stream: false
        })
      }).then(function(res) { return res.json(); })
        .then(function(json) {
          return (json.choices && json.choices[0] && json.choices[0].message && json.choices[0].message.content) || '';
        });
    }
  };
})();
