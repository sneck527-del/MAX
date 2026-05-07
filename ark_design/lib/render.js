const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const DRAW_BASE = 'https://grsai.dakka.com.cn/v1/draw/completions';
const DRAW_MODEL = 'gpt-image-2';
const CONCURRENCY = 5;
const STYLE_PREFIX = '统一风格：大师级建筑室内设计摄影作品，写实照片，真实光影，极致细节，温暖大地色调（米色/陶土/沙色），柔和自然光线，极简构图，徕卡色彩风格，高端精品酒店氛围，浅景深，8K分辨率';

/**
 * Render images for a project: reads proposal.html, generates images via grsai,
 * replaces placeholders with real images.
 */
async function renderProject(projectDir, onProgress) {
  const htmlPath = path.resolve(projectDir, 'proposal.html');
  if (!fs.existsSync(htmlPath)) {
    throw new Error('未找到 proposal.html: ' + htmlPath);
  }

  const apiKey = process.env.GRSAI_API_KEY;
  if (!apiKey) {
    throw new Error('请设置 GRSAI_API_KEY 环境变量');
  }

  let html = fs.readFileSync(htmlPath, 'utf-8');
  const imagesDir = path.resolve(projectDir, 'images');
  fs.mkdirSync(imagesDir, { recursive: true });

  // Extract all image placeholders with their descriptions
  const placeholders = extractPlaceholders(html);

  if (placeholders.length === 0) {
    onProgress('没有找到待生成的图片占位符');
    return html;
  }

  onProgress(`找到 ${placeholders.length} 张图片待生成`);

  // Generate images with concurrency limit
  const results = await batchGenerate(placeholders, imagesDir, apiKey, onProgress);

  // Replace placeholders with real images
  let updatedHtml = html;
  let replaced = 0;
  for (const r of results) {
    if (r.imagePath) {
      const relativePath = path.relative(path.dirname(htmlPath), r.imagePath).replace(/\\/g, '/');
      updatedHtml = updatedHtml.replace(r.placeholderHtml, r.replacementHtml(relativePath));
      replaced++;
    }
  }

  const outputPath = path.resolve(projectDir, 'proposal.rendered.html');
  fs.writeFileSync(outputPath, updatedHtml, 'utf-8');
  onProgress(`完成！已替换 ${replaced}/${placeholders.length} 张图片 → ${outputPath}`);

  return updatedHtml;
}

/**
 * Extract image placeholders from HTML.
 * Returns array of { index, description, placeholderHtml, replacementHtml(path) }
 */
function extractPlaceholders(html) {
  const results = [];
  const regex = /<figure class="img-slot[^"]*"[^>]*>[\s\S]*?<\/figure>/g;
  let match;
  let index = 0;

  while ((match = regex.exec(html)) !== null) {
    const placeholderHtml = match[0];
    // Extract description from .label
    const labelMatch = placeholderHtml.match(/<div class="label">([\s\S]*?)<\/div>/);
    const description = labelMatch ? labelMatch[1].trim() : `配图_${index}`;

    // Extract max-height from inline style
    const heightMatch = placeholderHtml.match(/max-height:([^;]+)/);
    const height = heightMatch ? heightMatch[1].trim() : '32vh';

    results.push({
      index: index++,
      description,
      height,
      placeholderHtml,
      replacementHtml: (imagePath) => buildReplacement(imagePath, description, height),
    });
  }

  return results;
}

function buildReplacement(imagePath, description, height) {
  return `<figure class="frame-img" style="height:${height}">
      <img src="${imagePath}" alt="${escAttr(description)}"
           style="width:100%;height:100%;object-fit:contain">
      <figcaption class="frame-cap"><span class="pf">${escHtml(description)}</span></figcaption>
    </figure>`;
}

/**
 * Generate images in batches with CONCURRENCY limit.
 */
async function batchGenerate(placeholders, imagesDir, apiKey, onProgress) {
  const results = [];
  const queue = [...placeholders];

  async function worker() {
    while (queue.length > 0) {
      const ph = queue.shift();
      const fname = `img_${String(ph.index).padStart(3, '0')}.png`;
      const outPath = path.join(imagesDir, fname);

      if (fs.existsSync(outPath)) {
        onProgress(`  [${ph.index + 1}/${placeholders.length}] 跳过 (已存在): ${ph.description.slice(0, 30)}...`);
        results.push({ ...ph, imagePath: outPath });
        continue;
      }

      onProgress(`  [${ph.index + 1}/${placeholders.length}] 生成: ${ph.description.slice(0, 40)}...`);
      try {
        const imageUrl = await drawRequest(apiKey, ph.description);
        if (imageUrl) {
          await downloadImage(imageUrl, outPath);
          onProgress(`    ✓ ${Math.round(fs.statSync(outPath).size / 1024)}KB`);
          results.push({ ...ph, imagePath: outPath });
        } else {
          onProgress(`    ✗ 生成失败 (无返回 URL)`);
          results.push({ ...ph, imagePath: null });
        }
      } catch (e) {
        onProgress(`    ✗ 错误: ${e.message.slice(0, 60)}`);
        results.push({ ...ph, imagePath: null });
      }
    }
  }

  // Launch CONCURRENCY workers
  const workers = Array.from({ length: CONCURRENCY }, () => worker());
  await Promise.all(workers);

  return results;
}

/**
 * Call grsai draw API (streaming SSE).
 */
function drawRequest(apiKey, description) {
  const prompt = `${description}。${STYLE_PREFIX}`;
  const payload = JSON.stringify({
    model: DRAW_MODEL,
    prompt,
    aspectRatio: '4:3',
  });

  return new Promise((resolve, reject) => {
    const url = new URL(DRAW_BASE);
    const options = {
      hostname: url.hostname,
      path: url.pathname,
      port: url.port || 443,
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      timeout: 600000,
    };

    const req = https.request(options, (res) => {
      let buffer = '';
      let imageUrl = null;

      res.on('data', (chunk) => {
        buffer += chunk.toString();
        // Parse SSE lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmed.slice(6));
              if (data.status === 'succeeded') {
                const results = data.results || [];
                if (results.length > 0) {
                  imageUrl = results[0].url;
                }
              } else if (data.status === 'failed') {
                console.warn('  draw failed:', data.failure_reason || 'unknown');
              }
            } catch (e) {
              // partial JSON, continue collecting
            }
          }
        }
      });

      res.on('end', () => {
        resolve(imageUrl);
      });

      res.on('error', reject);
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error('请求超时'));
    });

    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

/**
 * Download image from URL to local path.
 */
function downloadImage(url, outPath) {
  return new Promise((resolve, reject) => {
    const protocol = url.startsWith('https') ? https : http;
    protocol.get(url, { timeout: 300000 }, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error(`下载失败: HTTP ${res.statusCode}`));
        return;
      }
      const file = fs.createWriteStream(outPath);
      res.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
      file.on('error', reject);
    }).on('error', reject).on('timeout', function() {
      this.destroy();
      reject(new Error('下载超时'));
    });
  });
}

// ==================== 工具 ====================

function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escAttr(s) {
  return String(s || '').replace(/"/g,'&quot;').replace(/&/g,'&amp;');
}

module.exports = {
  renderProject,
  extractPlaceholders,
};
