export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 处理 CORS 预检请求
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    // 根路径返回 HTML 界面
    if (url.pathname === '/' && request.method === 'GET') {
      return new Response(getHTML(), {
        headers: {
          'Content-Type': 'text/html;charset=UTF-8',
        },
      });
    }

    // 翻译 API 端点
    if (url.pathname === '/api/translate' && request.method === 'POST') {
      try {
        const { text, target_lang, source_lang } = await request.json();

        if (!text || !target_lang) {
          return jsonResponse({ error: 'Missing required parameters: text and target_lang' }, 400);
        }

        // 调用 DeepL API
        const deeplResponse = await translateWithDeepL(
          text,
          target_lang,
          source_lang,
          env.DEEPL_API_KEY
        );

        return jsonResponse(deeplResponse);
      } catch (error) {
        return jsonResponse({ error: error.message }, 500);
      }
    }

    // 获取支持的语言列表
    if (url.pathname === '/api/languages' && request.method === 'GET') {
      try {
        const languages = await getLanguages(env.DEEPL_API_KEY);
        return jsonResponse(languages);
      } catch (error) {
        return jsonResponse({ error: error.message }, 500);
      }
    }

    return jsonResponse({ error: 'Not found' }, 404);
  },
};

/**
 * 调用 DeepL API 进行翻译
 */
async function translateWithDeepL(text, targetLang, sourceLang, apiKey) {
  if (!apiKey) {
    throw new Error('DEEPL_API_KEY is not configured');
  }

  // 判断使用免费版还是专业版 API
  const isFreeApi = apiKey.endsWith(':fx');
  const baseUrl = isFreeApi
    ? 'https://api-free.deepl.com/v2'
    : 'https://api.deepl.com/v2';

  const body = new URLSearchParams({
    text: text,
    target_lang: targetLang.toUpperCase(),
  });

  if (sourceLang) {
    body.append('source_lang', sourceLang.toUpperCase());
  }

  const response = await fetch(`${baseUrl}/translate`, {
    method: 'POST',
    headers: {
      'Authorization': `DeepL-Auth-Key ${apiKey}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`DeepL API error: ${response.status} - ${errorText}`);
  }

  return await response.json();
}

/**
 * 获取 DeepL 支持的语言列表
 */
async function getLanguages(apiKey) {
  if (!apiKey) {
    throw new Error('DEEPL_API_KEY is not configured');
  }

  const isFreeApi = apiKey.endsWith(':fx');
  const baseUrl = isFreeApi
    ? 'https://api-free.deepl.com/v2'
    : 'https://api.deepl.com/v2';

  const response = await fetch(`${baseUrl}/languages?type=target`, {
    method: 'GET',
    headers: {
      'Authorization': `DeepL-Auth-Key ${apiKey}`,
    },
  });

  if (!response.ok) {
    throw new Error(`DeepL API error: ${response.status}`);
  }

  return await response.json();
}

/**
 * 返回 JSON 响应
 */
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

function getHTML() {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeepL Pro Translate</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root {
            --primary: #0f172a;
            --primary-hover: #1e293b;
            --accent: #3b82f6;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text-main: #1e293b;
            --text-muted: #64748b;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, sans-serif;
        }

        body {
            background-color: var(--bg);
            color: var(--text-main);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }

        .app-container {
            background: var(--card-bg);
            width: 100%;
            max-width: 1000px;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
            border: 1px solid var(--border);
            overflow: hidden;
        }

        /* 顶部导航 */
        .header {
            padding: 20px 32px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
            font-size: 1.2rem;
            color: var(--primary);
        }

        /* 语言选择栏 */
        .toolbar {
            padding: 16px 32px;
            background: #fdfdfd;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--border);
        }

        select {
            appearance: none;
            background: white;
            border: 1px solid var(--border);
            padding: 8px 32px 8px 12px;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            outline: none;
            transition: all 0.2s;
        }

        select:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
        }

        .swap-btn {
            background: none;
            border: 1px solid var(--border);
            padding: 8px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            color: var(--text-muted);
            transition: all 0.2s;
        }

        .swap-btn:hover {
            background: var(--bg);
            color: var(--accent);
        }

        /* 主编辑器 */
        .editor-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            min-height: 350px;
        }

        .editor-pane {
            position: relative;
            padding: 24px 32px;
        }

        .editor-pane:first-child {
            border-right: 1px solid var(--border);
        }

        textarea {
            width: 100%;
            height: 100%;
            border: none;
            resize: none;
            font-size: 18px;
            line-height: 1.6;
            color: var(--text-main);
            outline: none;
            background: transparent;
        }

        textarea::placeholder {
            color: #cbd5e1;
        }

        .pane-footer {
            position: absolute;
            bottom: 16px;
            right: 24px;
            display: flex;
            gap: 8px;
        }

        /* 翻译按钮 */
        .action-bar {
            padding: 20px 32px;
            background: #fdfdfd;
            display: flex;
            justify-content: flex-end;
            border-top: 1px solid var(--border);
        }

        .btn-primary {
            background: var(--primary);
            color: white;
            border: none;
            padding: 12px 28px;
            border-radius: 10px;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }

        .btn-primary:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
        }

        .btn-primary:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }

        .icon-btn {
            background: white;
            border: 1px solid var(--border);
            padding: 6px;
            border-radius: 6px;
            cursor: pointer;
            color: var(--text-muted);
            transition: all 0.2s;
        }

        .icon-btn:hover {
            background: var(--bg);
            color: var(--primary);
        }

        /* 状态显示 */
        #status-toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 24px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
            display: none;
            z-index: 100;
        }

        .toast-error { background: #fee2e2; color: #991b1b; }
        .toast-success { background: #dcfce7; color: #166534; }

        /* 加载动画 */
        .spinner {
            width: 18px;
            height: 18px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
            display: none;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .loading .spinner { display: block; }
        .loading .btn-text { display: none; }

        @media (max-width: 768px) {
            .editor-grid { grid-template-columns: 1fr; }
            .editor-pane:first-child { border-right: none; border-bottom: 1px solid var(--border); }
            .toolbar { flex-wrap: wrap; }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <header class="header">
            <div class="logo">
                <i data-lucide="languages" style="color: var(--accent)"></i>
                <span>DeepL Pro</span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted)">Cloudflare Worker Edge</div>
        </header>

        <div class="toolbar">
            <select id="sourceLang">
                <option value="">自动检测</option>
                <option value="ZH">中文</option>
                <option value="EN">英语</option>
                <option value="JA">日语</option>
                <option value="KO">韩语</option>
                <option value="FR">法语</option>
                <option value="DE">德语</option>
                <option value="ES">西班牙语</option>
            </select>

            <button class="swap-btn" onclick="swapLanguages()" title="交换语言">
                <i data-lucide="arrow-left-right" size="18"></i>
            </button>

            <select id="targetLang">
                <option value="ZH">中文</option>
                <option value="EN-US" selected>英语 (美)</option>
                <option value="EN-GB">英语 (英)</option>
                <option value="JA">日语</option>
                <option value="KO">韩语</option>
                <option value="FR">法语</option>
                <option value="DE">德语</option>
                <option value="ES">西班牙语</option>
            </select>
        </div>

        <div class="editor-grid">
            <div class="editor-pane">
                <textarea id="sourceText" placeholder="在此输入或粘贴文本..."></textarea>
                <div class="pane-footer">
                    <button class="icon-btn" onclick="clearText()" title="清除">
                        <i data-lucide="x" size="16"></i>
                    </button>
                </div>
            </div>
            <div class="editor-pane" style="background: #fafafa">
                <textarea id="translatedText" placeholder="翻译结果..." readonly></textarea>
                <div class="pane-footer">
                    <button class="icon-btn" onclick="copyResult()" title="复制结果">
                        <i data-lucide="copy" size="16"></i>
                    </button>
                </div>
            </div>
        </div>

        <div class="action-bar">
            <button id="translateBtn" class="btn-primary" onclick="doTranslate()">
                <div class="spinner"></div>
                <span class="btn-text">立即翻译</span>
                <i data-lucide="arrow-right" class="btn-text" size="18"></i>
            </button>
        </div>
    </div>

    <div id="status-toast"></div>

    <script>
        // 初始化图标
        lucide.createIcons();

        function showToast(msg, type) {
            const toast = document.getElementById('status-toast');
            toast.textContent = msg;
            toast.className = type === 'success' ? 'toast-success' : 'toast-error';
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 3000);
        }

        function clearText() {
            document.getElementById('sourceText').value = '';
            document.getElementById('translatedText').value = '';
        }

        async function copyResult() {
            const text = document.getElementById('translatedText').value;
            if (!text) return;
            await navigator.clipboard.writeText(text);
            showToast('已复制到剪贴板', 'success');
        }

        function swapLanguages() {
            const src = document.getElementById('sourceLang');
            const tgt = document.getElementById('targetLang');
            const temp = src.value;
            // 如果源是“自动”，交换时设为常用语言（如中文）
            src.value = tgt.value.includes('EN') ? 'EN' : tgt.value;
            tgt.value = temp || 'ZH';
        }

        async function doTranslate() {
            const sourceText = document.getElementById('sourceText').value.trim();
            const targetLang = document.getElementById('targetLang').value;
            const sourceLang = document.getElementById('sourceLang').value;
            
            const btn = document.getElementById('translateBtn');
            const output = document.getElementById('translatedText');

            if (!sourceText) {
                showToast('请输入需要翻译的内容', 'error');
                return;
            }

            // 锁定状态
            btn.disabled = true;
            btn.classList.add('loading');

            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: sourceText,
                        target_lang: targetLang,
                        source_lang: sourceLang || undefined,
                    }),
                });

                const data = await response.json();

                if (!response.ok) throw new Error(data.error || '翻译请求失败');

                if (data.translations && data.translations.length > 0) {
                    output.value = data.translations[0].text;
                } else {
                    throw new Error('未返回有效结果');
                }
            } catch (error) {
                console.error(error);
                showToast(error.message, 'error');
            } finally {
                // 确保无论如何都会恢复按钮状态
                btn.disabled = false;
                btn.classList.remove('loading');
            }
        }

        // 快捷键支持
        document.getElementById('sourceText').addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                doTranslate();
            }
        });
    </script>
</body>
</html>`;
}