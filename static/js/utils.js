/**
 * 通用工具函数模块
 * 包含项目中常用的工具函数和辅助方法
 */

// DOM 操作工具
const DOMUtils = {
    /**
     * 获取元素
     * @param {string} selector - CSS选择器
     * @returns {Element|null}
     */
    get(selector) {
        return document.querySelector(selector);
    },

    /**
     * 获取所有匹配的元素
     * @param {string} selector - CSS选择器
     * @returns {NodeList}
     */
    getAll(selector) {
        return document.querySelectorAll(selector);
    },

    /**
     * 创建元素
     * @param {string} tag - 标签名
     * @param {Object} attributes - 属性对象
     * @param {string} content - 内容
     * @returns {Element}
     */
    create(tag, attributes = {}, content = '') {
        const element = document.createElement(tag);
        
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'innerHTML') {
                element.innerHTML = value;
            } else {
                element.setAttribute(key, value);
            }
        });
        
        if (content) {
            element.textContent = content;
        }
        
        return element;
    },

    /**
     * 添加事件监听器
     * @param {Element|string} element - 元素或选择器
     * @param {string} event - 事件类型
     * @param {Function} handler - 事件处理函数
     */
    on(element, event, handler) {
        const el = typeof element === 'string' ? this.get(element) : element;
        if (el) {
            el.addEventListener(event, handler);
        }
    },

    /**
     * 移除事件监听器
     * @param {Element|string} element - 元素或选择器
     * @param {string} event - 事件类型
     * @param {Function} handler - 事件处理函数
     */
    off(element, event, handler) {
        const el = typeof element === 'string' ? this.get(element) : element;
        if (el) {
            el.removeEventListener(event, handler);
        }
    },

    /**
     * 切换类名
     * @param {Element|string} element - 元素或选择器
     * @param {string} className - 类名
     */
    toggleClass(element, className) {
        const el = typeof element === 'string' ? this.get(element) : element;
        if (el) {
            el.classList.toggle(className);
        }
    },

    /**
     * 添加类名
     * @param {Element|string} element - 元素或选择器
     * @param {string} className - 类名
     */
    addClass(element, className) {
        const el = typeof element === 'string' ? this.get(element) : element;
        if (el) {
            el.classList.add(className);
        }
    },

    /**
     * 移除类名
     * @param {Element|string} element - 元素或选择器
     * @param {string} className - 类名
     */
    removeClass(element, className) {
        const el = typeof element === 'string' ? this.get(element) : element;
        if (el) {
            el.classList.remove(className);
        }
    }
};

// HTTP 请求工具
const HTTPUtils = {
    /**
     * 发送 GET 请求
     * @param {string} url - 请求URL
     * @param {Object} options - 请求选项
     * @returns {Promise}
     */
    async get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    },

    /**
     * 发送 POST 请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @param {Object} options - 请求选项
     * @returns {Promise}
     */
    async post(url, data = {}, options = {}) {
        return this.request(url, {
            ...options,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            body: JSON.stringify(data)
        });
    },

    /**
     * 发送 PUT 请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @param {Object} options - 请求选项
     * @returns {Promise}
     */
    async put(url, data = {}, options = {}) {
        return this.request(url, {
            ...options,
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            body: JSON.stringify(data)
        });
    },

    /**
     * 发送 DELETE 请求
     * @param {string} url - 请求URL
     * @param {Object} options - 请求选项
     * @returns {Promise}
     */
    async delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    },

    /**
     * 通用请求方法
     * @param {string} url - 请求URL
     * @param {Object} options - 请求选项
     * @returns {Promise}
     */
    async request(url, options = {}) {
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error('Request failed:', error);
            throw error;
        }
    },

    /**
     * 上传文件
     * @param {string} url - 上传URL
     * @param {File|FormData} file - 文件或FormData
     * @param {Function} onProgress - 进度回调
     * @returns {Promise}
     */
    async uploadFile(url, file, onProgress = null) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = file instanceof FormData ? file : new FormData();
            
            if (!(file instanceof FormData)) {
                formData.append('file', file);
            }
            
            if (onProgress) {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        onProgress(percentComplete);
                    }
                });
            }
            
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (e) {
                        resolve(xhr.responseText);
                    }
                } else {
                    reject(new Error(`Upload failed: ${xhr.status}`));
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed'));
            });
            
            xhr.open('POST', url);
            xhr.send(formData);
        });
    }
};

// 存储工具
const StorageUtils = {
    /**
     * 设置本地存储
     * @param {string} key - 键
     * @param {*} value - 值
     */
    setLocal(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Failed to set localStorage:', error);
        }
    },

    /**
     * 获取本地存储
     * @param {string} key - 键
     * @param {*} defaultValue - 默认值
     * @returns {*}
     */
    getLocal(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Failed to get localStorage:', error);
            return defaultValue;
        }
    },

    /**
     * 移除本地存储
     * @param {string} key - 键
     */
    removeLocal(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('Failed to remove localStorage:', error);
        }
    },

    /**
     * 清空本地存储
     */
    clearLocal() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('Failed to clear localStorage:', error);
        }
    },

    /**
     * 设置会话存储
     * @param {string} key - 键
     * @param {*} value - 值
     */
    setSession(key, value) {
        try {
            sessionStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Failed to set sessionStorage:', error);
        }
    },

    /**
     * 获取会话存储
     * @param {string} key - 键
     * @param {*} defaultValue - 默认值
     * @returns {*}
     */
    getSession(key, defaultValue = null) {
        try {
            const item = sessionStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Failed to get sessionStorage:', error);
            return defaultValue;
        }
    },

    /**
     * 移除会话存储
     * @param {string} key - 键
     */
    removeSession(key) {
        try {
            sessionStorage.removeItem(key);
        } catch (error) {
            console.error('Failed to remove sessionStorage:', error);
        }
    }
};

// 字符串工具
const StringUtils = {
    /**
     * 生成随机ID
     * @param {number} length - 长度
     * @returns {string}
     */
    generateId(length = 8) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    },

    /**
     * 截断文本
     * @param {string} text - 文本
     * @param {number} maxLength - 最大长度
     * @param {string} suffix - 后缀
     * @returns {string}
     */
    truncate(text, maxLength, suffix = '...') {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - suffix.length) + suffix;
    },

    /**
     * 转义HTML
     * @param {string} text - 文本
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 格式化文件大小
     * @param {number} bytes - 字节数
     * @returns {string}
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * 格式化时间
     * @param {Date|string|number} date - 日期
     * @returns {string}
     */
    formatTime(date) {
        const d = new Date(date);
        const now = new Date();
        const diff = now - d;
        
        const minute = 60 * 1000;
        const hour = minute * 60;
        const day = hour * 24;
        
        if (diff < minute) {
            return '刚刚';
        } else if (diff < hour) {
            return Math.floor(diff / minute) + '分钟前';
        } else if (diff < day) {
            return Math.floor(diff / hour) + '小时前';
        } else if (diff < day * 7) {
            return Math.floor(diff / day) + '天前';
        } else {
            return d.toLocaleDateString('zh-CN');
        }
    }
};

// 验证工具
const ValidationUtils = {
    /**
     * 验证邮箱
     * @param {string} email - 邮箱
     * @returns {boolean}
     */
    isEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    },

    /**
     * 验证URL
     * @param {string} url - URL
     * @returns {boolean}
     */
    isUrl(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    },

    /**
     * 验证手机号
     * @param {string} phone - 手机号
     * @returns {boolean}
     */
    isPhone(phone) {
        const regex = /^1[3-9]\d{9}$/;
        return regex.test(phone);
    },

    /**
     * 验证是否为空
     * @param {*} value - 值
     * @returns {boolean}
     */
    isEmpty(value) {
        return value === null || value === undefined || value === '' || 
               (Array.isArray(value) && value.length === 0) ||
               (typeof value === 'object' && Object.keys(value).length === 0);
    }
};

// 防抖和节流工具
const ThrottleUtils = {
    /**
     * 防抖函数
     * @param {Function} func - 函数
     * @param {number} wait - 等待时间
     * @returns {Function}
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * 节流函数
     * @param {Function} func - 函数
     * @param {number} limit - 限制时间
     * @returns {Function}
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// 模态框工具
const ModalUtils = {
    /**
     * 显示确认对话框
     * @param {string} message - 确认消息
     * @param {string} title - 标题（可选）
     * @param {Object} options - 选项
     * @returns {Promise<boolean>} - 用户选择结果
     */
    async confirm(message, title = '确认操作', options = {}) {
        return new Promise((resolve) => {
            // 创建模态框HTML
            const modalId = 'confirm-modal-' + Date.now();
            const modalHtml = `
                <div class="modal confirm-modal" id="${modalId}" tabindex="-1" role="dialog" aria-labelledby="${modalId}-title" aria-hidden="true">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3 id="${modalId}-title">
                                <span class="icon">⚠️</span>
                                ${title}
                            </h3>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-cancel" data-action="cancel">取消</button>
                            <button type="button" class="btn btn-confirm" data-action="confirm">确认</button>
                        </div>
                    </div>
                </div>
            `;

            // 添加到页面
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modalElement = document.getElementById(modalId);
            
            // 绑定事件
            const confirmBtn = modalElement.querySelector('[data-action="confirm"]');
            const cancelBtn = modalElement.querySelector('[data-action="cancel"]');
            
            const handleConfirm = () => {
                modalElement.style.display = 'none';
                modalElement.remove();
                resolve(true);
            };

            const handleCancel = () => {
                modalElement.style.display = 'none';
                modalElement.remove();
                resolve(false);
            };
            
            confirmBtn.addEventListener('click', handleConfirm);
            cancelBtn.addEventListener('click', handleCancel);

            // 点击背景关闭
            modalElement.addEventListener('click', (e) => {
                if (e.target === modalElement) {
                    handleCancel();
                }
            });

            // ESC键关闭
            const handleKeydown = (e) => {
                if (e.key === 'Escape') {
                    handleCancel();
                    document.removeEventListener('keydown', handleKeydown);
                }
            };
            document.addEventListener('keydown', handleKeydown);

            // 显示模态框
            modalElement.style.display = 'block';
            
            // 聚焦到取消按钮（更安全的默认选择）
            setTimeout(() => {
                cancelBtn.focus();
            }, 100);
        });
    },

    /**
     * 显示警告对话框
     * @param {string} message - 警告消息
     * @param {string} title - 标题（可选）
     * @returns {Promise<void>}
     */
    async alert(message, title = '提示') {
        return new Promise((resolve) => {
            const modalId = 'alert-modal-' + Date.now();
            const modalHtml = `
                <div class="modal fade" id="${modalId}" tabindex="-1" role="dialog" aria-labelledby="${modalId}-title" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-centered" role="document">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="${modalId}-title">${title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="关闭"></button>
                            </div>
                            <div class="modal-body">
                                <p class="mb-0">${message}</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-primary" data-bs-dismiss="modal">确定</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modalElement = document.getElementById(modalId);
            
            const modal = new bootstrap.Modal(modalElement, {
                backdrop: 'static',
                keyboard: false
            });

            const okBtn = modalElement.querySelector('[data-bs-dismiss="modal"]');
            okBtn.addEventListener('click', () => {
                modal.hide();
                resolve();
            });

            modalElement.addEventListener('hidden.bs.modal', () => {
                modalElement.remove();
            });

            modal.show();
        });
    }
};

// 导出所有工具
window.Utils = {
    DOM: DOMUtils,
    HTTP: HTTPUtils,
    Storage: StorageUtils,
    String: StringUtils,
    Validation: ValidationUtils,
    Throttle: ThrottleUtils,
    Modal: ModalUtils
};

// 兼容性检查
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.Utils;
}