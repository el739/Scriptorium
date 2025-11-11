require('dotenv').config();
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Configure multer for file uploads
const upload = multer({
  dest: 'uploads/',
  limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

// Create uploads directory if it doesn't exist
if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads');
}

// OCR endpoint
app.post('/api/ocr', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No image file provided' });
    }

    // Call OCR.space API
    const formData = new FormData();

    // Get file extension from original filename or mimetype
    let filename = req.file.originalname;
    if (!path.extname(filename)) {
      // If no extension, try to determine from mimetype
      const mimeToExt = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/bmp': '.bmp',
        'image/tiff': '.tiff',
        'image/webp': '.webp'
      };
      const ext = mimeToExt[req.file.mimetype] || '.jpg';
      filename = `image${ext}`;
    }

    formData.append('file', fs.createReadStream(req.file.path), {
      filename: filename,
      contentType: req.file.mimetype
    });
    formData.append('apikey', process.env.OCR_SPACE_API_KEY);
    formData.append('language', 'auto');
    formData.append('OCREngine', '2');
    formData.append('isTable', 'true');
    formData.append('detectOrientation', 'true');

    const ocrResponse = await axios.post('https://api.ocr.space/parse/image', formData, {
      headers: formData.getHeaders(),
      maxContentLength: Infinity,
      maxBodyLength: Infinity
    });

    // Clean up uploaded file
    fs.unlinkSync(req.file.path);

    if (ocrResponse.data.IsErroredOnProcessing) {
      return res.status(500).json({
        error: 'OCR processing failed',
        details: ocrResponse.data.ErrorMessage
      });
    }

    const ocrText = ocrResponse.data.ParsedResults?.[0]?.ParsedText || '';

    res.json({
      success: true,
      ocrText: ocrText,
      fullResponse: ocrResponse.data
    });

  } catch (error) {
    console.error('OCR Error:', error.message);

    // Clean up file if it exists
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }

    res.status(500).json({
      error: 'OCR processing failed',
      details: error.message
    });
  }
});

// LLM proofreading endpoint
app.post('/api/proofread', async (req, res) => {
  try {
    const { imageBase64, ocrText } = req.body;

    if (!imageBase64 || !ocrText) {
      return res.status(400).json({ error: 'Missing required parameters' });
    }

    const llmBaseUrl = process.env.LLM_BASE_URL || 'https://api.openai.com/v1';
    const llmApiKey = process.env.LLM_API_KEY;
    const llmModel = process.env.LLM_MODEL || 'gpt-4o';

    if (!llmApiKey) {
      return res.status(400).json({ error: 'LLM API key not configured in server environment' });
    }

    // Prepare the LLM request
    const messages = [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: `请校对以下OCR识别的文本。这是机器OCR识别的结果，可能存在错误。请根据图片内容进行校对和修正，返回准确的文本内容。

机器OCR识别结果：
${ocrText}

请直接返回校对后的准确文本，遵守如下规则：
1、机器ocr会包含许多不应该的换行（这是由原图片的排版引起的），请你在理解语意的基础上，删除这些换行，使得当文字所处的文本框的长宽发生改变时，文字仍然能够正确地显示
2、如果有复杂的数学公式，使用$或$$包裹起来，以latex格式输出。仅对复杂的数学公式做这样的操作，简单的公式不要。`
          },
          {
            type: 'image_url',
            image_url: {
              url: imageBase64.startsWith('data:') ? imageBase64 : `data:image/png;base64,${imageBase64}`
            }
          }
        ]
      }
    ];

    // Set headers for Server-Sent Events
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Call LLM API with streaming
    const llmResponse = await axios.post(
      `${llmBaseUrl}/chat/completions`,
      {
        model: llmModel,
        messages: messages,
        max_tokens: 4096,
        stream: true
      },
      {
        headers: {
          'Authorization': `Bearer ${llmApiKey}`,
          'Content-Type': 'application/json'
        },
        responseType: 'stream'
      }
    );

    // Forward the stream to client
    llmResponse.data.on('data', (chunk) => {
      const lines = chunk.toString().split('\n').filter(line => line.trim() !== '');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);

          if (data === '[DONE]') {
            res.write(`data: [DONE]\n\n`);
            continue;
          }

          try {
            const parsed = JSON.parse(data);
            const content = parsed.choices?.[0]?.delta?.content;

            if (content) {
              res.write(`data: ${JSON.stringify({ content })}\n\n`);
            }
          } catch (e) {
            // Ignore parsing errors
          }
        }
      }
    });

    llmResponse.data.on('end', () => {
      res.write(`data: [DONE]\n\n`);
      res.end();
    });

    llmResponse.data.on('error', (error) => {
      console.error('Stream Error:', error);
      res.write(`data: ${JSON.stringify({ error: 'Stream error' })}\n\n`);
      res.end();
    });

  } catch (error) {
    console.error('LLM Error:', error.response?.data || error.message);

    // If headers not sent yet, send error as JSON
    if (!res.headersSent) {
      res.status(500).json({
        error: 'LLM proofreading failed',
        details: error.response?.data?.error?.message || error.message
      });
    } else {
      // If streaming already started, send error as SSE
      res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
      res.end();
    }
  }
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    ocrConfigured: !!process.env.OCR_SPACE_API_KEY,
    llmConfigured: !!process.env.LLM_API_KEY
  });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log(`OCR API configured: ${!!process.env.OCR_SPACE_API_KEY}`);
  console.log(`LLM API configured: ${!!process.env.LLM_API_KEY}`);
});
