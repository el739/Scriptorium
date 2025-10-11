require('dotenv').config();
const express = require('express');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// 配置multer用于文件上传
const storage = multer.memoryStorage();
const upload = multer({
    storage: storage,
    limits: {
        fileSize: 1024 * 1024 // 1MB限制
    },
    fileFilter: (req, file, cb) => {
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
        if (allowedTypes.includes(file.mimetype)) {
            cb(null, true);
        } else {
            cb(new Error('不支持的文件类型'));
        }
    }
});

// 静态文件服务
app.use(express.static('public'));
app.use(express.json());

// OCR识别端点
app.post('/api/ocr', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: '请上传文件' });
        }

        console.log('开始OCR识别...');

        // 第一步：OCR.space识别
        const ocrText = await performOCR(req.file);

        if (!ocrText) {
            return res.status(400).json({ error: '未能识别出文字内容' });
        }

        console.log('OCR识别完成，文本长度:', ocrText.length);

        // 第二步：AI校对
        let proofreadText = '';
        try {
            proofreadText = await proofreadWithAI(ocrText);
            console.log('AI校对完成');
        } catch (aiError) {
            console.error('AI校对失败:', aiError.message);
            // 即使AI校对失败，也返回OCR结果
            proofreadText = '校对失败: ' + aiError.message;
        }

        res.json({
            ocrText: ocrText,
            proofreadText: proofreadText
        });

    } catch (error) {
        console.error('OCR处理错误:', error);
        res.status(500).json({
            error: error.message || '识别过程中出现错误'
        });
    }
});

// 调用OCR.space API
async function performOCR(file) {
    const formData = new FormData();
    formData.append('file', file.buffer, {
        filename: file.originalname,
        contentType: file.mimetype
    });
    formData.append('language', 'auto');
    formData.append('OCREngine', '2');
    formData.append('isOverlayRequired', 'false');
    formData.append('detectOrientation', 'true');
    formData.append('scale', 'true');

    try {
        const response = await axios.post('https://api.ocr.space/parse/image', formData, {
            headers: {
                ...formData.getHeaders(),
                'apikey': process.env.OCR_SPACE_API_KEY
            },
            timeout: 30000
        });

        if (response.data.IsErroredOnProcessing) {
            throw new Error('OCR识别失败: ' + (response.data.ErrorMessage || '未知错误'));
        }

        if (!response.data.ParsedResults || response.data.ParsedResults.length === 0) {
            throw new Error('未能解析图片内容');
        }

        const parsedText = response.data.ParsedResults[0].ParsedText;

        if (!parsedText || parsedText.trim() === '') {
            throw new Error('未识别到文字内容');
        }

        return parsedText.trim();

    } catch (error) {
        if (error.response) {
            console.error('OCR API错误:', error.response.data);
            throw new Error('OCR API错误: ' + (error.response.data.ErrorMessage || error.response.statusText));
        } else if (error.request) {
            throw new Error('无法连接到OCR服务');
        } else {
            throw error;
        }
    }
}

// 使用 LLM API 进行校对
async function proofreadWithAI(text) {
    // 从环境变量读取配置
    const apiKey = process.env.LLM_API_KEY;
    const baseURL = process.env.LLM_API_BASE_URL || 'https://openrouter.ai/api/v1';
    const model = process.env.LLM_MODEL || 'zyphra/glm-4.5v';

    if (!apiKey) {
        throw new Error('LLM_API_KEY 未配置');
    }

    // 构建 API URL
    const apiURL = baseURL.endsWith('/chat/completions')
        ? baseURL
        : `${baseURL.replace(/\/$/, '')}/chat/completions`;

    try {
        const response = await axios.post(apiURL, {
            model: model,
            messages: [
                {
                    role: 'system',
                    content: '你是一个专业的文字校对助手。请仔细检查OCR识别出的文本，纠正其中的错别字、标点符号错误、格式问题等，保持原文的意思和结构。对于识别错误的数学公式，使用latex格式给出。由于原文的排版，换行符会根据原文的排版来，而不符合人类的阅读习惯，也请你移除不需要的换行符。只返回校对后的文本内容，不要添加任何解释或说明。'
                },
                {
                    role: 'user',
                    content: `请校对以下OCR识别的文本：\n\n${text}`
                }
            ],
            temperature: 0.3,
            max_tokens: 4000
        }, {
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json',
                'HTTP-Referer': 'http://localhost:3000',
                'X-Title': 'OCR Proofreading App'
            },
            timeout: 60000
        });

        if (!response.data.choices || response.data.choices.length === 0) {
            throw new Error('AI未返回有效响应');
        }

        const proofreadText = response.data.choices[0].message.content.trim();
        return proofreadText;

    } catch (error) {
        if (error.response) {
            console.error('LLM API错误:', error.response.data);
            throw new Error('AI校对失败: ' + (error.response.data.error?.message || error.response.statusText));
        } else if (error.request) {
            throw new Error('无法连接到AI服务');
        } else {
            throw error;
        }
    }
}

// 健康检查端点
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString()
    });
});

// 启动服务器
app.listen(PORT, () => {
    console.log(`服务器运行在 http://localhost:${PORT}`);
    console.log(`OCR.space API Key: ${process.env.OCR_SPACE_API_KEY ? '已配置' : '未配置'}`);
    console.log(`LLM API Key: ${process.env.LLM_API_KEY ? '已配置' : '未配置'}`);
    console.log(`LLM API Base URL: ${process.env.LLM_API_BASE_URL || 'https://openrouter.ai/api/v1'}`);
    console.log(`LLM Model: ${process.env.LLM_MODEL || 'zyphra/glm-4.5v'}`);
});

// 错误处理中间件
app.use((error, req, res, next) => {
    console.error('服务器错误:', error);
    res.status(500).json({
        error: error.message || '服务器内部错误'
    });
});
