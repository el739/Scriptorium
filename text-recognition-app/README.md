# OCR 文字识别与 AI 校对应用

一个基于 Web 的 OCR 文字识别应用，使用 OCR.space 进行图片文字识别，然后通过 LLM API 进行智能校对。

## 功能特点

- 支持多种图片格式（JPG、PNG、GIF）和 PDF 文件
- 使用 OCR.space Engine 2 进行高精度文字识别
- 自动检测语言
- AI 智能校对识别结果
- 直观的拖拽上传界面
- **支持 Ctrl+V 粘贴剪贴板图片** ⭐
- 实时预览上传的图片
- 一键复制识别和校对结果

## 技术栈

### 前端
- HTML5
- CSS3（绿色-黄色渐变主题）
- Vanilla JavaScript

### 后端
- Node.js
- Express.js
- Multer（文件上传）
- Axios（HTTP 请求）

### API 服务
- **OCR.space**：OCR 识别服务（Engine 2，自动语言检测）
- **LLM API**：AI 校对服务（支持 OpenRouter、OpenAI 或任何兼容 OpenAI 格式的 API）

## 安装步骤

### 1. 克隆或下载项目

```bash
cd text-recognition-app
```

### 2. 安装依赖

```bash
npm install
```

### 3. 配置 API 密钥

复制 `.env.example` 文件为 `.env`：

```bash
copy .env.example .env
```

编辑 `.env` 文件，填入你的 API 密钥：

```env
# OCR.space API Key
# 获取地址: https://ocr.space/ocrapi/freekey
OCR_SPACE_API_KEY=你的_ocr_space_api_密钥

# LLM API 配置
# API Key
LLM_API_KEY=你的_llm_api_密钥

# API Base URL (支持 OpenRouter、OpenAI、或任何兼容 OpenAI 格式的 API)
# OpenRouter: https://openrouter.ai/api/v1
# OpenAI: https://api.openai.com/v1
# 自定义: http://your-api-server/v1
LLM_API_BASE_URL=https://openrouter.ai/api/v1

# 模型名称
# OpenRouter 示例: zyphra/glm-4.5v, anthropic/claude-3.5-sonnet, openai/gpt-4
# OpenAI 示例: gpt-4, gpt-3.5-turbo
# 自定义模型: 你的模型名称
LLM_MODEL=zyphra/glm-4.5v

# 服务器端口（可选）
PORT=3000
```

#### 获取 API 密钥

**OCR.space API Key：**
1. 访问 https://ocr.space/ocrapi/freekey
2. 输入邮箱地址注册
3. 在邮箱中查收 API Key

免费额度：
- 25,000 次/月
- 文件大小限制：1 MB
- PDF 页数限制：3 页

**LLM API Key：**

使用 OpenRouter：
1. 访问 https://openrouter.ai/keys
2. 注册并登录账户
3. 创建新的 API Key

使用 OpenAI：
1. 访问 https://platform.openai.com/api-keys
2. 创建新的 API Key
3. 修改 `LLM_API_BASE_URL` 为 `https://api.openai.com/v1`
4. 修改 `LLM_MODEL` 为 `gpt-4` 或 `gpt-3.5-turbo`

使用自定义 API：
1. 确保你的 API 服务兼容 OpenAI 格式
2. 设置 `LLM_API_BASE_URL` 为你的 API 地址
3. 设置 `LLM_MODEL` 为你的模型名称

### 4. 启动应用

开发模式（自动重启）：
```bash
npm run dev
```

生产模式：
```bash
npm start
```

### 5. 访问应用

打开浏览器访问：http://localhost:3000

## 使用说明

### 上传图片的三种方式

1. **点击上传**
   - 点击上传区域选择文件
   - 支持 JPG、PNG、GIF、PDF 格式
   - 文件大小限制：1 MB

2. **拖拽上传**
   - 直接拖拽图片到上传区域
   - 松开鼠标即可上传

3. **粘贴上传** ⭐ 新功能
   - 复制图片到剪贴板（截图、复制图片文件等）
   - 在页面任意位置按 `Ctrl+V`（Windows/Linux）或 `Cmd+V`（Mac）
   - 图片会自动加载并显示预览

### 识别与校对

1. 上传成功后，点击"开始识别"按钮
2. 等待 OCR 识别和 AI 校对完成
3. 左侧显示 OCR 原始识别结果
4. 右侧显示 AI 校对后的结果
5. 点击"复制"按钮可复制相应内容

## 项目结构

```
text-recognition-app/
├── public/                 # 前端静态文件
│   ├── index.html         # 主页面
│   ├── style.css          # 样式文件
│   └── script.js          # 前端 JavaScript
├── server.js              # Node.js 服务器
├── package.json           # 项目配置
├── .env.example           # 环境变量示例
├── .env                   # 环境变量（需自行创建）
├── API-DOC.md            # OCR.space API 文档
└── README.md             # 项目说明文档
```

## API 端点

### POST /api/ocr

上传图片进行 OCR 识别和 AI 校对。

**请求：**
- Content-Type: `multipart/form-data`
- Body: `file` - 图片或 PDF 文件

**响应：**
```json
{
  "ocrText": "OCR识别的原始文本",
  "proofreadText": "AI校对后的文本"
}
```

### GET /api/health

健康检查端点。

**响应：**
```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00.000Z"
}
```

## 配置说明

### OCR.space 配置

在 server.js 中配置的参数：

```javascript
{
  language: 'auto',           // 自动检测语言
  OCREngine: '2',            // 使用 Engine 2
  isOverlayRequired: 'false', // 不返回坐标信息
  detectOrientation: 'true',  // 自动旋转图片
  scale: 'true'              // 放大低分辨率图片
}
```

### LLM API 配置

可通过环境变量配置：

```javascript
{
  apiKey: process.env.LLM_API_KEY,           // API 密钥
  baseURL: process.env.LLM_API_BASE_URL,     // API Base URL
  model: process.env.LLM_MODEL,              // 模型名称
  temperature: 0.3,                          // 较低的温度保证稳定性
  max_tokens: 4000                           // 最大返回长度
}
```

支持的 API 服务：
- **OpenRouter**：`https://openrouter.ai/api/v1`（默认）
- **OpenAI**：`https://api.openai.com/v1`
- **自定义 API**：任何兼容 OpenAI 格式的 API 服务

## 常见问题

### 1. 识别不出文字

- 确保图片清晰度足够
- 图片文字不要太小
- 尝试放大图片后再上传

### 2. API 调用失败

- 检查 API Key 是否正确配置
- 确认网络连接正常
- 查看是否超出免费额度

### 3. 文件上传失败

- 确认文件大小不超过 1 MB
- 确认文件格式正确
- 尝试压缩图片后再上传

### 4. Ctrl+V 粘贴不工作

- 确认剪贴板中有图片内容
- 尝试重新截图或复制图片
- 检查浏览器是否支持剪贴板 API

## 依赖项

```json
{
  "axios": "^1.6.0",
  "dotenv": "^16.3.1",
  "express": "^4.18.2",
  "form-data": "^4.0.0",
  "multer": "^1.4.5-lts.1"
}
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.1.0 (2025-01-11)
- 新增 Ctrl+V 粘贴剪贴板图片功能
- 支持配置 LLM API Base URL 和模型名称
- 优化用户界面提示

### v1.0.0 (2025-01-11)
- 初始版本发布
- 支持图片和 PDF 文字识别
- 集成 AI 智能校对功能
- 绿色-黄色渐变主题界面
