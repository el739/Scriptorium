# DeepL Cloudflare 翻译服务

一个部署在 Cloudflare Workers 上的 DeepL 翻译 Web 应用，提供简洁的界面和 API 接口。

## 功能特性

- 🚀 基于 Cloudflare Workers，全球边缘部署，访问速度快
- 🌍 支持 DeepL API 的所有语言对
- 🎨 美观的现代化 Web 界面
- 🔌 提供 RESTful API 接口
- 💰 支持 DeepL 免费版和专业版 API
- 📱 响应式设计，支持移动端

## 前置要求

1. [Node.js](https://nodejs.org/) (推荐 v18 或更高版本)
2. [Cloudflare 账号](https://dash.cloudflare.com/sign-up)
3. [DeepL API Key](https://www.deepl.com/pro-api)

## 获取 DeepL API Key

1. 访问 [DeepL API 页面](https://www.deepl.com/pro-api)
2. 注册账号（免费版每月 50 万字符额度）
3. 在控制台获取 API Key
   - 免费版 API Key 格式：`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx`
   - 专业版 API Key 格式：`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

## 安装步骤

### 1. 安装依赖

```bash
npm install
```

### 2. 登录 Cloudflare

```bash
npx wrangler login
```

### 3. 配置 DeepL API Key

将 API Key 设置为环境变量（secret）：

```bash
npx wrangler secret put DEEPL_API_KEY
```

然后在提示时输入你的 DeepL API Key。

### 4. 本地开发

```bash
npm run dev
```

访问 http://localhost:8787 查看应用。

### 5. 部署到 Cloudflare

```bash
npm run deploy
```

部署成功后，你会得到一个类似 `https://deepl-translator.your-subdomain.workers.dev` 的 URL。

## API 使用说明

### 翻译文本

**请求：**

```bash
POST /api/translate
Content-Type: application/json

{
  "text": "Hello, world!",
  "target_lang": "ZH",
  "source_lang": "EN"  // 可选，不提供则自动检测
}
```

**响应：**

```json
{
  "translations": [
    {
      "detected_source_language": "EN",
      "text": "你好，世界！"
    }
  ]
}
```

### 获取支持的语言

**请求：**

```bash
GET /api/languages
```

**响应：**

```json
[
  {
    "language": "ZH",
    "name": "Chinese"
  },
  {
    "language": "EN",
    "name": "English"
  }
  // ... 更多语言
]
```

## 支持的语言代码

### 常用语言

- `ZH` - 中文
- `EN-US` - 英语（美国）
- `EN-GB` - 英语（英国）
- `JA` - 日语
- `KO` - 韩语
- `FR` - 法语
- `DE` - 德语
- `ES` - 西班牙语
- `RU` - 俄语
- `PT-BR` - 葡萄牙语（巴西）
- `PT-PT` - 葡萄牙语（葡萄牙）
- `IT` - 意大利语

完整的语言列表请参考 [DeepL 官方文档](https://www.deepl.com/docs-api/translate-text)。

## 使用示例

### 使用 Web 界面

1. 打开部署后的 URL
2. 选择源语言和目标语言
3. 输入要翻译的文本
4. 点击"翻译"按钮或按 Ctrl+Enter

### 使用 API

#### cURL

```bash
curl -X POST https://your-worker.workers.dev/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "target_lang": "ZH"
  }'
```

#### JavaScript

```javascript
const response = await fetch('https://your-worker.workers.dev/api/translate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    text: 'Hello, world!',
    target_lang: 'ZH',
  }),
});

const data = await response.json();
console.log(data.translations[0].text);
```

#### Python

```python
import requests

response = requests.post(
    'https://your-worker.workers.dev/api/translate',
    json={
        'text': 'Hello, world!',
        'target_lang': 'ZH'
    }
)

result = response.json()
print(result['translations'][0]['text'])
```

## 项目结构

```
deepl-cloudflare/
├── src/
│   └── index.js          # Worker 主代码
├── package.json          # 项目配置
├── wrangler.toml         # Cloudflare Workers 配置
└── README.md            # 说明文档
```

## 常见问题

### 1. API Key 无效

确保你的 API Key 格式正确：
- 免费版以 `:fx` 结尾
- 检查是否有多余的空格

### 2. 翻译失败

- 检查网络连接
- 确认 API Key 额度是否用完
- 查看 Cloudflare Workers 日志：`npx wrangler tail`

### 3. 本地开发无法访问

确保运行 `npm run dev` 后访问正确的端口（默认 8787）。

## 自定义配置

### 修改 Worker 名称

编辑 `wrangler.toml`：

```toml
name = "your-custom-name"
```

### 添加自定义域名

在 Cloudflare Dashboard 中：
1. 进入 Workers & Pages
2. 选择你的 Worker
3. 点击 "Settings" > "Triggers"
4. 添加自定义域名

## 许可证

MIT

## 相关链接

- [DeepL API 文档](https://www.deepl.com/docs-api)
- [Cloudflare Workers 文档](https://developers.cloudflare.com/workers/)
- [Wrangler CLI 文档](https://developers.cloudflare.com/workers/wrangler/)
