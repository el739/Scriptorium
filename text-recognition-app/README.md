# 图片文字识别应用

这是一个基于LLM的图片文字识别应用，使用OpenRouter API进行文字提取。

## 功能特点

- 前端界面友好，支持拖拽上传和点击上传
- 支持 JPG, PNG, WEBP 格式的图片
- 使用 OpenRouter API 进行文字识别
- 支持复制识别结果
- 支持 Ctrl+V 直接粘贴剪贴板中的图片
- 响应式设计，适配移动端

## 技术栈

### 后端
- Node.js
- Express.js
- Multer (文件上传)
- Axios (API 请求)
- dotenv (环境变量管理)

### 前端
- HTML5
- CSS3
- JavaScript (ES6+)
- Fetch API

## 安装和运行

### 1. 安装依赖

```bash
cd text-recognition-app
npm install
cp .env.example .env
```

### 2. 配置环境变量

在 `.env` 文件中填入你的 OpenRouter API 密钥和模型：
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
PORT=3000
OPENROUTER_MODEL=qwen/qwen2.5-vl-72b-instruct:free
```

### 3. 运行应用

开发模式：
```bash
npm run dev
```

生产模式：
```bash
npm start
```

应用将在 `http://localhost:3000` 运行。

## 使用说明

1. 打开浏览器访问 `http://localhost:3000`
2. 点击上传区域选择图片，或拖拽图片到上传区域
3. 点击"上传并识别"按钮
4. 等待识别完成，查看结果
5. 可以点击"复制文字"按钮复制识别结果

## API 接口

### 上传并识别图片

```
POST /api/extract-text
```

**请求:**
- Content-Type: `multipart/form-data`
- 参数: `image` (图片文件)

**响应:**
```json
{
  "success": true,
  "text": "识别出的文字内容"
}
```

## 项目结构

```
text-recognition-app/
├── public/              # 前端静态文件
│   ├── index.html       # 主页面
│   ├── style.css        # 样式文件
│   └── script.js        # 前端逻辑
├── uploads/             # 上传文件临时存储目录
├── server.js            # 后端服务器
├── .env                 # 环境变量配置
├── package.json         # 项目依赖
└── README.md            # 项目说明文档
```

## 注意事项

1. 上传的图片文件大小不能超过10MB
2. 支持的图片格式：JPG, PNG, WEBP
3. 识别过程需要网络连接
4. 上传的图片会在识别完成后自动删除

## 故障排除

### API 密钥问题
如果遇到 API 密钥相关的错误，请检查：
1. `.env` 文件中的 `OPENROUTER_API_KEY` 是否正确设置
2. API 密钥是否有足够的权限

### 文件上传问题
如果文件上传失败，请检查：
1. 文件格式是否为 JPG, PNG, WEBP
2. 文件大小是否超过 10MB 限制

### 识别结果不准确
如果识别结果不准确，可以尝试：
1. 使用更高分辨率的图片
2. 确保图片中的文字清晰可见
3. 确保图片没有过度的倾斜或变形

## 许可证

本项目仅供学习和参考使用。
