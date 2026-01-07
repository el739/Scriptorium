// ==UserScript==
// @name         RelayPulse 服务商筛选器
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  服务商状态过滤器
// @author       You
// @match        https://relaypulse.top/*
// @icon         https://relaypulse.top/favicon.ico
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // 要显示的服务商列表
    const targetProviders = ['Anyrouter'];

    // 过滤表格行的函数
    function filterRows() {
        // 获取表格主体
        const tbody = document.querySelector('table tbody');
        if (!tbody) return;

        // 获取所有行
        const rows = tbody.querySelectorAll('tr');

        rows.forEach(row => {
            // 获取服务商单元格（第二列）
            const providerCell = row.querySelector('td:nth-child(2)');
            if (!providerCell) return;

            // 获取服务商名称
            const providerText = providerCell.textContent.trim();

            // 检查是否包含目标服务商
            let shouldShow = false;
            for (const provider of targetProviders) {
                if (providerText.includes(provider)) {
                    shouldShow = true;
                    break;
                }
            }

            // 显示或隐藏行
            if (shouldShow) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    // 等待页面加载完成
    function waitForTable() {
        const observer = new MutationObserver((mutations, obs) => {
            const table = document.querySelector('table tbody');
            if (table && table.children.length > 0) {
                filterRows();
                obs.disconnect();

                // 继续监听表格变化（比如数据刷新）
                const tableObserver = new MutationObserver(() => {
                    filterRows();
                });

                tableObserver.observe(table, {
                    childList: true,
                    subtree: true
                });
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // 页面加载完成后执行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', waitForTable);
    } else {
        waitForTable();
    }

    // 添加一个按钮来切换过滤
    function addToggleButton() {
        const button = document.createElement('button');
        button.textContent = '切换过滤';
        button.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 9999;
            padding: 10px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;

        let filterEnabled = true;

        button.addEventListener('click', () => {
            filterEnabled = !filterEnabled;
            const tbody = document.querySelector('table tbody');
            if (!tbody) return;

            const rows = tbody.querySelectorAll('tr');
            if (filterEnabled) {
                button.textContent = '切换过滤';
                button.style.backgroundColor = '#4CAF50';
                filterRows();
            } else {
                button.textContent = '显示所有服务商';
                button.style.backgroundColor = '#2196F3';
                rows.forEach(row => {
                    row.style.display = '';
                });
            }
        });

        document.body.appendChild(button);
    }

    // 添加切换按钮
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addToggleButton);
    } else {
        addToggleButton();
    }
})();
