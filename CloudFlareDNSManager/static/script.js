// 全局变量
let currentZoneId = null;
let currentDomain = null;
let currentRecordId = null;

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 绑定事件监听器
    bindEventListeners();
    
    // 初始化页面
    loadZones();
});

// 绑定事件监听器
function bindEventListeners() {
    // 刷新域名列表按钮
    document.getElementById('refresh-zones').addEventListener('click', loadZones);
    
    // 返回域名列表按钮
    document.getElementById('back-to-zones').addEventListener('click', showZonesSection);
    
    // 添加记录按钮
    document.getElementById('add-record').addEventListener('click', showAddRecordModal);
    
    // 刷新记录按钮
    document.getElementById('refresh-records').addEventListener('click', loadDNSRecords);
    
    // 记录表单提交
    document.getElementById('record-form').addEventListener('submit', handleRecordFormSubmit);
    
    // 模态框关闭按钮
    const closeButtons = document.querySelectorAll('.close');
    closeButtons.forEach(button => {
        button.addEventListener('click', closeModals);
    });
    
    // 点击模态框外部关闭
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModals();
            }
        });
    });
    
    // 取消删除按钮
    document.getElementById('cancel-delete').addEventListener('click', closeModals);
    
    // 确认删除按钮
    document.getElementById('confirm-delete').addEventListener('click', handleDeleteRecord);
}

// 显示通知
function showNotification(message, type = 'success') {
    // 移除现有的通知
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 创建新通知
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// 关闭所有模态框
function closeModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
}

// 显示加载状态
function showLoading(element) {
    element.innerHTML = '<span class="loading"></span>加载中...';
}

// 显示域名区域
function showZonesSection() {
    document.getElementById('zones-section').style.display = 'block';
    document.getElementById('records-section').style.display = 'none';
}

// 显示记录区域
function showRecordsSection() {
    document.getElementById('zones-section').style.display = 'none';
    document.getElementById('records-section').style.display = 'block';
}

// 加载域名列表
async function loadZones() {
    const zonesContainer = document.getElementById('zones-container');
    showLoading(zonesContainer);
    
    try {
        const response = await fetch('/api/zones');
        const zones = await response.json();
        
        if (zones.length === 0) {
            zonesContainer.innerHTML = '<p>未找到域名</p>';
            return;
        }
        
        renderZones(zones);
    } catch (error) {
        console.error('加载域名失败:', error);
        zonesContainer.innerHTML = '<p class="error">加载域名失败，请检查网络连接和API配置</p>';
        showNotification('加载域名失败', 'error');
    }
}

// 渲染域名列表
function renderZones(zones) {
    const zonesContainer = document.getElementById('zones-container');
    
    zonesContainer.innerHTML = zones.map(zone => `
        <div class="card">
            <h3><i class="fas fa-globe"></i> ${zone.name}</h3>
            <p><strong>ID:</strong> ${zone.id}</p>
            <p><strong>状态:</strong> ${zone.status}</p>
            <p><strong>激活:</strong> ${zone.activated ? '是' : '否'}</p>
            <div class="actions">
                <button class="btn btn-primary" onclick="viewDNSRecords('${zone.id}', '${zone.name}')">
                    <i class="fas fa-list"></i> 查看记录
                </button>
            </div>
        </div>
    `).join('');
}

// 查看DNS记录
async function viewDNSRecords(zoneId, domain) {
    currentZoneId = zoneId;
    currentDomain = domain;
    
    // 显示域名信息
    document.getElementById('domain-info').innerHTML = `
        <h3><i class="fas fa-info-circle"></i> 当前域名: ${domain}</h3>
        <p>Zone ID: ${zoneId}</p>
    `;
    
    // 显示记录区域
    showRecordsSection();
    
    // 加载DNS记录
    await loadDNSRecords();
}

// 加载DNS记录
async function loadDNSRecords() {
    if (!currentZoneId) return;
    
    const recordsContainer = document.getElementById('records-container');
    showLoading(recordsContainer);
    
    try {
        const response = await fetch(`/api/zones/${currentZoneId}/dns_records`);
        const records = await response.json();
        
        if (records.length === 0) {
            recordsContainer.innerHTML = '<p>未找到DNS记录</p>';
            return;
        }
        
        renderDNSRecords(records);
    } catch (error) {
        console.error('加载DNS记录失败:', error);
        recordsContainer.innerHTML = '<p class="error">加载DNS记录失败，请检查网络连接</p>';
        showNotification('加载DNS记录失败', 'error');
    }
}

// 渲染DNS记录
function renderDNSRecords(records) {
    const recordsContainer = document.getElementById('records-container');
    
    // 清除card-container类，添加专门的类
    recordsContainer.className = 'records-container';
    
    // 创建表格
    let tableHTML = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>类型</th>
                        <th>名称</th>
                        <th>内容</th>
                        <th>TTL</th>
                        <th>代理</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    records.forEach(record => {
        const proxied = record.proxied ? '是' : '否';
        tableHTML += `
            <tr>
                <td>${record.type}</td>
                <td>${record.name}</td>
                <td>${record.content}</td>
                <td>${record.ttl}</td>
                <td>${proxied}</td>
                <td>
                    <button class="btn btn-warning" onclick="showEditRecordModal('${record.id}', '${record.type}', '${record.name}', '${record.content}', ${record.ttl}, ${record.proxied})">
                        <i class="fas fa-edit"></i> 编辑
                    </button>
                    <button class="btn btn-danger" onclick="showDeleteRecordModal('${record.id}', '${record.type}', '${record.name}', '${record.content}')">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                </td>
            </tr>
        `;
    });
    
    tableHTML += `
                </tbody>
            </table>
        </div>
    `;
    
    recordsContainer.innerHTML = tableHTML;
}

// 显示添加记录模态框
function showAddRecordModal() {
    if (!currentZoneId) return;
    
    // 重置表单
    document.getElementById('record-form').reset();
    document.getElementById('zone-id').value = currentZoneId;
    document.getElementById('record-id').value = '';
    document.getElementById('modal-title').textContent = '添加DNS记录';
    
    // 显示模态框
    document.getElementById('record-modal').style.display = 'block';
}

// 显示编辑记录模态框
function showEditRecordModal(recordId, type, name, content, ttl, proxied) {
    if (!currentZoneId) return;
    
    // 填充表单数据
    document.getElementById('zone-id').value = currentZoneId;
    document.getElementById('record-id').value = recordId;
    document.getElementById('record-type').value = type;
    document.getElementById('record-name').value = name;
    document.getElementById('record-content').value = content;
    document.getElementById('record-ttl').value = ttl;
    document.getElementById('record-proxied').checked = proxied;
    document.getElementById('modal-title').textContent = '编辑DNS记录';
    
    // 显示模态框
    document.getElementById('record-modal').style.display = 'block';
}

// 显示删除记录模态框
function showDeleteRecordModal(recordId, type, name, content) {
    currentRecordId = recordId;
    
    // 显示记录信息
    document.getElementById('delete-record-info').textContent = 
        `${type} ${name} -> ${content}`;
    
    // 显示模态框
    document.getElementById('delete-modal').style.display = 'block';
}

// 处理记录表单提交
async function handleRecordFormSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const zoneId = document.getElementById('zone-id').value;
    const recordId = document.getElementById('record-id').value;
    const type = document.getElementById('record-type').value;
    const name = document.getElementById('record-name').value;
    const content = document.getElementById('record-content').value;
    const ttl = parseInt(document.getElementById('record-ttl').value);
    const proxied = document.getElementById('record-proxied').checked;
    
    // 构造请求数据
    const data = {
        type,
        name,
        content,
        ttl,
        proxied
    };
    
    try {
        let response;
        
        if (recordId) {
            // 更新记录
            response = await fetch(`/api/zones/${zoneId}/dns_records/${recordId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        } else {
            // 创建记录
            response = await fetch(`/api/zones/${zoneId}/dns_records`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(recordId ? '记录更新成功' : '记录创建成功');
            closeModals();
            loadDNSRecords();
        } else {
            showNotification(recordId ? '记录更新失败' : '记录创建失败', 'error');
        }
    } catch (error) {
        console.error('保存记录失败:', error);
        showNotification('保存记录失败，请检查网络连接', 'error');
    }
}

// 处理删除记录
async function handleDeleteRecord() {
    if (!currentZoneId || !currentRecordId) return;
    
    try {
        const response = await fetch(`/api/zones/${currentZoneId}/dns_records/${currentRecordId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('记录删除成功');
            closeModals();
            loadDNSRecords();
        } else {
            showNotification('记录删除失败', 'error');
        }
    } catch (error) {
        console.error('删除记录失败:', error);
        showNotification('删除记录失败，请检查网络连接', 'error');
    }
}
