const PROVIDER_PRESETS = {
  deepseek: { url: 'https://api.deepseek.com', model: 'deepseek-chat' },
  openai:   { url: 'https://api.openai.com',   model: 'gpt-4o' },
  qwen:     { url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  zhipu:    { url: 'https://open.bigmodel.cn',  model: 'glm-4-flash' },
  doubao:   { url: 'https://ark.cn-beijing.volces.com/api/v3', model: '' },
  grsai:    { url: 'https://grsai.dakka.com.cn', model: 'gemini-3.1-pro' },
};

function getEndpoint(provider, baseUrl) {
  if (provider === 'zhipu') return baseUrl.replace(/\/+$/, '') + '/v4/chat/completions';
  return baseUrl.replace(/\/+$/, '') + '/v1/chat/completions';
}

async function stream(messages, onChunk, opts = {}) {
  const { provider, apiUrl, apiKey, model } = opts;
  if (!apiKey) throw new Error('未配置 API Key，请运行: node ark.js config --key <your-key>');

  const headers = { 'Content-Type': 'application/json' };
  if (apiKey) headers['Authorization'] = 'Bearer ' + apiKey;

  const body = JSON.stringify({
    model: model,
    messages: messages,
    stream: true,
    temperature: opts.temperature ?? 0.7,
    max_tokens: opts.maxTokens ?? 4096
  });

  const res = await fetch(getEndpoint(provider, apiUrl), {
    method: 'POST',
    headers,
    body,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API错误 ${res.status}: ${text}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let full = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const lines = decoder.decode(value, { stream: true }).split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed === 'data: [DONE]') continue;
      if (trimmed.startsWith('data: ')) {
        try {
          const json = JSON.parse(trimmed.slice(6));
          const delta = json.choices?.[0]?.delta?.content || '';
          if (delta) {
            full += delta;
            if (onChunk) onChunk(delta);
          }
        } catch (e) { /* skip parse errors */ }
      }
    }
  }
  return full;
}

async function call(messages, opts = {}) {
  const { provider, apiUrl, apiKey, model } = opts;
  if (!apiKey) throw new Error('未配置 API Key');

  const headers = { 'Content-Type': 'application/json' };
  if (apiKey) headers['Authorization'] = 'Bearer ' + apiKey;

  const res = await fetch(getEndpoint(provider, apiUrl), {
    method: 'POST',
    headers,
    body: JSON.stringify({
      model,
      messages,
      stream: false,
      temperature: opts.temperature ?? 0.3,
      max_tokens: opts.maxTokens ?? 2048
    })
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API错误 ${res.status}: ${text}`);
  }

  const json = await res.json();
  return json.choices?.[0]?.message?.content || '';
}

module.exports = { PROVIDER_PRESETS, getEndpoint, stream, call };
