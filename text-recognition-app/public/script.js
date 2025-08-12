// 获取DOM元素
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const previewSection = document.getElementById('previewSection');
const imagePreview = document.getElementById('imagePreview');
const resultSection = document.getElementById('resultSection');
const resultText = document.getElementById('resultText');
const copyBtn = document.getElementById('copyBtn');
const loading = document.getElementById('loading');
const errorMessage = document.getElementById('errorMessage');
const errorMsg = errorMessage.querySelector('p');

let selectedFile = null;

// 事件监听器
uploadArea.addEventListener('click', () => {
    fileInput.click();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    if (e.dataTransfer.files.length) {
        handleFileSelect(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFileSelect(e.target.files[0]);
    }
});

uploadBtn.addEventListener('click', uploadAndRecognize);

copyBtn.addEventListener('click', copyToClipboard);

// 处理文件选择
function handleFileSelect(file) {
    // 检查文件类型
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showError('请选择有效的图片文件 (JPG, PNG, WEBP)');
        return;
    }
    
    // 检查文件大小 (最大10MB)
    if (file.size > 10 * 1024 * 1024) {
        showError('文件大小不能超过10MB');
        return;
    }
    
    selectedFile = file;
    uploadBtn.disabled = false;
    
    // 显示图片预览
    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.src = e.target.result;
        previewSection.style.display = 'block';
    };
    reader.readAsDataURL(file);
    
    // 清除之前的错误和结果
    hideError();
    resultSection.style.display = 'none';
}

// 上传并识别图片
async function uploadAndRecognize() {
    if (!selectedFile) return;
    
    // 显示加载状态
    showLoading();
    hideError();
    
    try {
        const formData = new FormData();
        formData.append('image', selectedFile);
        
        const response = await fetch('/api/extract-text', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 显示结果
            resultText.value = data.text;
            resultSection.style.display = 'block';
        } else {
            showError(data.error || '识别失败，请重试');
        }
    } catch (error) {
        showError('网络错误，请检查连接后重试');
        console.error('Error:', error);
    } finally {
        hideLoading();
        // 重置selectedFile以便可以处理下一张图片
        selectedFile = null;
        uploadBtn.disabled = true;
    }
}

// 复制文字到剪贴板
function copyToClipboard() {
    resultText.select();
    document.execCommand('copy');
    
    // 显示复制成功提示
    const originalText = copyBtn.textContent;
    copyBtn.textContent = '已复制!';
    setTimeout(() => {
        copyBtn.textContent = originalText;
    }, 2000);
}

// 显示加载状态
function showLoading() {
    loading.style.display = 'block';
    uploadBtn.disabled = true;
}

// 隐藏加载状态
function hideLoading() {
    loading.style.display = 'none';
    // 不要在这里重新启用按钮，而是在处理新文件时启用
}

// 显示错误信息
function showError(message) {
    errorMsg.textContent = message;
    errorMessage.style.display = 'block';
}

// 隐藏错误信息
function hideError() {
    errorMessage.style.display = 'none';
}

// 处理剪贴板粘贴事件
document.addEventListener('paste', (e) => {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    
    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
            const blob = items[i].getAsFile();
            if (blob) {
                // 创建一个新的File对象，因为getAsFile返回的是Blob
                const file = new File([blob], `pasted-image-${Date.now()}.png`, { type: blob.type });
                handleFileSelect(file);
                break;
            }
        }
    }
});

// 监听Ctrl+V按键事件（作为额外的保障）
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'v') {
        // 提示用户可以粘贴图片
        console.log('Ctrl+V detected, waiting for paste event');
    }
});

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('图片文字识别应用已加载');
    
    // 添加提示信息到上传区域
    const hint = document.createElement('p');
    hint.className = 'hint';
    hint.textContent = '提示：也可以直接按 Ctrl+V 粘贴剪贴板中的图片';
    hint.style.marginTop = '10px';
    hint.style.fontSize = '0.9em';
    hint.style.color = '#666';
    
    const uploadContent = document.querySelector('.upload-content');
    if (uploadContent) {
        uploadContent.appendChild(hint);
    }
});
