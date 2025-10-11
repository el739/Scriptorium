// DOM元素
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const previewSection = document.getElementById('previewSection');
const imagePreview = document.getElementById('imagePreview');
const changeImageBtn = document.getElementById('changeImageBtn');
const recognizeBtn = document.getElementById('recognizeBtn');
const resultsSection = document.getElementById('resultsSection');
const ocrResult = document.getElementById('ocrResult');
const proofreadResult = document.getElementById('proofreadResult');
const copyOcrBtn = document.getElementById('copyOcrBtn');
const copyProofreadBtn = document.getElementById('copyProofreadBtn');
const errorMessage = document.getElementById('errorMessage');

let selectedFile = null;

// 上传区域点击事件
uploadArea.addEventListener('click', () => {
    fileInput.click();
});

// 文件选择事件
fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
});

// 拖拽事件
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
    handleFileSelect(e.dataTransfer.files[0]);
});

// 更换图片按钮
changeImageBtn.addEventListener('click', () => {
    fileInput.click();
});

// 识别按钮
recognizeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    hideError();
    await performOCR();
});

// 复制按钮
copyOcrBtn.addEventListener('click', () => {
    copyToClipboard(ocrResult.textContent);
});

copyProofreadBtn.addEventListener('click', () => {
    copyToClipboard(proofreadResult.textContent);
});

// 监听全局粘贴事件（Ctrl+V）
document.addEventListener('paste', (e) => {
    // 检查是否有剪贴板项
    const items = e.clipboardData?.items;
    if (!items) return;

    // 遍历剪贴板项，查找图片
    for (let i = 0; i < items.length; i++) {
        const item = items[i];

        // 检查是否为图片类型
        if (item.type.indexOf('image') !== -1) {
            e.preventDefault();

            // 获取图片文件
            const file = item.getAsFile();
            if (file) {
                // 创建一个带有适当名称的新文件
                const renamedFile = new File(
                    [file],
                    `pasted-image-${Date.now()}.png`,
                    { type: file.type }
                );

                handleFileSelect(renamedFile);
                showSuccess('图片已从剪贴板粘贴');
            }
            break;
        }
    }
});

// 处理文件选择
function handleFileSelect(file) {
    if (!file) return;

    // 验证文件类型
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
    if (!validTypes.includes(file.type)) {
        showError('请选择有效的图片文件（JPG、PNG、GIF）或 PDF 文件');
        return;
    }

    // 验证文件大小（1MB）
    if (file.size > 1024 * 1024) {
        showError('文件大小不能超过 1MB');
        return;
    }

    selectedFile = file;

    // 显示预览
    if (file.type !== 'application/pdf') {
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            uploadArea.style.display = 'none';
            previewSection.style.display = 'block';
            recognizeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    } else {
        // PDF文件不显示预览，只显示文件名
        imagePreview.style.display = 'none';
        uploadArea.style.display = 'none';
        previewSection.style.display = 'block';
        previewSection.insertAdjacentHTML('afterbegin',
            `<div class="pdf-placeholder">
                <p>已选择 PDF 文件：${file.name}</p>
            </div>`
        );
        recognizeBtn.disabled = false;
    }
}

// 执行OCR识别
async function performOCR() {
    const btnText = recognizeBtn.querySelector('.btn-text');
    const spinner = recognizeBtn.querySelector('.spinner');

    // 禁用按钮并显示加载状态
    recognizeBtn.disabled = true;
    btnText.textContent = '识别中...';
    spinner.style.display = 'inline-block';

    // 显示结果区域
    resultsSection.style.display = 'grid';
    ocrResult.innerHTML = '<p class="placeholder">正在识别...</p>';
    proofreadResult.innerHTML = '<p class="placeholder">等待校对...</p>';
    copyOcrBtn.style.display = 'none';
    copyProofreadBtn.style.display = 'none';

    try {
        // 创建FormData
        const formData = new FormData();
        formData.append('file', selectedFile);

        // 调用OCR API
        const response = await fetch('/api/ocr', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '识别失败');
        }

        const data = await response.json();

        // 显示OCR结果
        if (data.ocrText) {
            ocrResult.textContent = data.ocrText;
            ocrResult.classList.add('fade-in');
            copyOcrBtn.style.display = 'block';
        } else {
            ocrResult.innerHTML = '<p class="placeholder" style="color: var(--error-color);">未识别到文字</p>';
        }

        // 显示校对结果
        if (data.proofreadText) {
            proofreadResult.textContent = data.proofreadText;
            proofreadResult.classList.add('fade-in');
            copyProofreadBtn.style.display = 'block';
        } else {
            proofreadResult.innerHTML = '<p class="placeholder" style="color: var(--error-color);">校对失败</p>';
        }

    } catch (error) {
        console.error('OCR Error:', error);
        showError(error.message || '识别过程中出现错误，请重试');
        ocrResult.innerHTML = '<p class="placeholder" style="color: var(--error-color);">识别失败</p>';
        proofreadResult.innerHTML = '<p class="placeholder" style="color: var(--error-color);">校对失败</p>';
    } finally {
        // 恢复按钮状态
        recognizeBtn.disabled = false;
        btnText.textContent = '开始识别';
        spinner.style.display = 'none';
    }
}

// 复制到剪贴板
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showSuccess('已复制到剪贴板');
    } catch (error) {
        console.error('Copy failed:', error);
        showError('复制失败，请手动复制');
    }
}

// 显示错误消息
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

// 隐藏错误消息
function hideError() {
    errorMessage.style.display = 'none';
}

// 显示成功消息
function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.style.cssText = `
        position: fixed;
        top: 2rem;
        right: 2rem;
        background: var(--success-color);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: var(--shadow-lg);
        z-index: 1000;
        animation: fadeIn 0.3s ease;
    `;
    successDiv.textContent = message;
    document.body.appendChild(successDiv);

    setTimeout(() => {
        successDiv.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => successDiv.remove(), 300);
    }, 2000);
}
