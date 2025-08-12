const express = require('express');
const cors = require('cors');
const multer = require('multer');
const axios = require('axios');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// 配置 multer 用于处理文件上传
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, 'uploads/');
  },
  filename: function (req, file, cb) {
    cb(null, Date.now() + path.extname(file.originalname));
  }
});

const upload = multer({ storage: storage });

// 创建 uploads 目录（如果不存在）
if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads');
}

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static('public'));
app.use('/uploads', express.static('uploads'));

// 路由：处理图片上传和文字提取
app.post('/api/extract-text', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No image file provided' });
    }

    // 检查是否提供了 API 密钥
    const apiKey = process.env.OPENROUTER_API_KEY;
    if (!apiKey) {
      return res.status(500).json({ error: 'OpenRouter API key not configured' });
    }

    // 读取上传的图片文件并转换为 base64
    const imagePath = req.file.path;
    const imageBuffer = fs.readFileSync(imagePath);
    const base64Image = imageBuffer.toString('base64');
    
    // 获取模型配置
    const model = process.env.OPENROUTER_MODEL || 'qwen/qwen2.5-vl-72b-instruct:free';
    
    // 构建 OpenRouter API 请求
    const response = await axios.post('https://openrouter.ai/api/v1/chat/completions', {
      model: model,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: '请提取并识别这张图片中的所有文字内容。只返回识别出的文字，不要添加任何其他说明。'
            },
            {
              type: 'image_url',
              image_url: {
                url: `data:image/jpeg;base64,${base64Image}`
              }
            }
          ]
        }
      ],
      max_tokens: 1000
    }, {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      }
    });

    // 提取识别结果
    const extractedText = response.data.choices[0]?.message?.content || '未能识别出文字';

    // 删除上传的文件（可选）
    fs.unlinkSync(imagePath);

    // 返回结果
    res.json({ 
      success: true,
      text: extractedText
    });
  } catch (error) {
    console.error('Error extracting text:', error);
    res.status(500).json({ 
      success: false,
      error: '处理图片时发生错误: ' + (error.response?.data?.error?.message || error.message)
    });
  }
});

// 健康检查路由
app.get('/api/health', (req, res) => {
  res.json({ status: 'OK', message: 'Text Recognition API is running' });
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
  console.log(`API endpoint: http://localhost:${PORT}/api/extract-text`);
});
