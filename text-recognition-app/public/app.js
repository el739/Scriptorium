// DOM elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const previewSection = document.getElementById('previewSection');
const imagePreview = document.getElementById('imagePreview');
const clearBtn = document.getElementById('clearBtn');
const processBtn = document.getElementById('processBtn');
const statusMessage = document.getElementById('statusMessage');
const resultsSection = document.getElementById('resultsSection');
const ocrResult = document.getElementById('ocrResult');
const proofreadResult = document.getElementById('proofreadResult');

// State
let currentImageFile = null;
let currentImageBase64 = null;

// Show status message
function showStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.className = `status-message show ${type}`;
    setTimeout(() => {
        statusMessage.classList.remove('show');
    }, 5000);
}

// Handle image selection
function handleImageSelect(file) {
    if (!file || !file.type.startsWith('image/')) {
        showStatus('请选择有效的图片文件', 'error');
        return;
    }

    currentImageFile = file;

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
        currentImageBase64 = e.target.result;
        imagePreview.src = e.target.result;
        uploadArea.style.display = 'none';
        previewSection.style.display = 'block';
        processBtn.disabled = false;
        resultsSection.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

// Click to upload
uploadArea.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleImageSelect(file);
    }
});

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');

    const file = e.dataTransfer.files[0];
    if (file) {
        handleImageSelect(file);
    }
});

// Paste from clipboard (Ctrl+V)
document.addEventListener('paste', (e) => {
    const items = e.clipboardData.items;

    for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
            e.preventDefault();
            const file = items[i].getAsFile();
            handleImageSelect(file);
            showStatus('已从剪贴板粘贴图片', 'success');
            break;
        }
    }
});

// Clear image
clearBtn.addEventListener('click', () => {
    currentImageFile = null;
    currentImageBase64 = null;
    imagePreview.src = '';
    uploadArea.style.display = 'block';
    previewSection.style.display = 'none';
    processBtn.disabled = true;
    resultsSection.style.display = 'none';
    fileInput.value = '';
});

// Process image
processBtn.addEventListener('click', async () => {
    if (!currentImageFile) {
        showStatus('请先选择图片', 'error');
        return;
    }

    // Disable button and show loading
    processBtn.disabled = true;
    processBtn.querySelector('.btn-text').textContent = '处理中...';
    processBtn.querySelector('.spinner').style.display = 'inline-block';

    // Clear previous results
    ocrResult.value = '';
    proofreadResult.value = '';

    try {
        // Step 1: OCR processing
        showStatus('正在进行 OCR 识别...', 'info');

        const formData = new FormData();
        formData.append('image', currentImageFile);

        const ocrResponse = await fetch('/api/ocr', {
            method: 'POST',
            body: formData
        });

        const ocrData = await ocrResponse.json();

        if (!ocrResponse.ok) {
            throw new Error(ocrData.error || 'OCR 处理失败');
        }

        if (!ocrData.success) {
            throw new Error('OCR 处理失败');
        }

        const ocrText = ocrData.ocrText;
        ocrResult.value = ocrText;

        // Show results immediately after OCR completes
        resultsSection.style.display = 'grid';
        showStatus('OCR 识别完成，正在进行 LLM 校对...', 'info');

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Step 2: LLM proofreading with streaming
        await streamProofread(currentImageBase64, ocrText);

        showStatus('处理完成！', 'success');

    } catch (error) {
        console.error('Error:', error);
        showStatus(`错误: ${error.message}`, 'error');

        // Show partial results if OCR succeeded
        if (ocrResult.value) {
            resultsSection.style.display = 'grid';
        }
    } finally {
        // Re-enable button
        processBtn.disabled = false;
        processBtn.querySelector('.btn-text').textContent = '开始识别';
        processBtn.querySelector('.spinner').style.display = 'none';
    }
});

// Stream proofreading with real-time display
async function streamProofread(imageBase64, ocrText) {
    return new Promise(async (resolve, reject) => {
        try {
            const response = await fetch('/api/proofread', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    imageBase64: imageBase64,
                    ocrText: ocrText
                })
            });

            if (!response.ok) {
                throw new Error('LLM 校对请求失败');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    resolve();
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                // Keep the last incomplete line in buffer
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);

                        if (data === '[DONE]') {
                            resolve();
                            return;
                        }

                        try {
                            const parsed = JSON.parse(data);

                            if (parsed.error) {
                                throw new Error(parsed.error);
                            }

                            if (parsed.content) {
                                // Append content to textarea in real-time
                                proofreadResult.value += parsed.content;
                                // Auto-scroll to bottom
                                proofreadResult.scrollTop = proofreadResult.scrollHeight;
                            }
                        } catch (e) {
                            if (e.message !== 'Unexpected end of JSON input') {
                                console.error('Parse error:', e);
                            }
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Stream error:', error);
            reject(error);
        }
    });
}

// Copy text to clipboard
function copyText(textareaId) {
    const textarea = document.getElementById(textareaId);
    textarea.select();
    document.execCommand('copy');
    showStatus('已复制到剪贴板', 'success');
}

// Keyboard shortcut hint
console.log('提示: 使用 Ctrl+V 可以直接粘贴剪贴板中的图片');
