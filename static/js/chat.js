/**
 * 聊天页面功能模块
 * 处理聊天界面的所有交互逻辑
 */

class ChatManager {
    constructor() {
        this.currentSessionId = null;
        this.messages = [];
        this.isTyping = false;
        this.strategy = 'balanced'; // 默认策略
        
        this.init();
    }

    /**
     * 初始化聊天管理器
     */
    init() {
        this.bindEvents();
        // this.loadChatHistory(); // 暂时注释掉，后端未实现对应接口
        this.setupAutoResize();
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 发送按钮点击事件
        Utils.DOM.on('#sendButton', 'click', () => this.sendMessage());
        
        // 输入框回车事件
        Utils.DOM.on('#messageInput', 'keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 输入框输入事件
        Utils.DOM.on('#messageInput', 'input', () => {
            this.updateSendButton();
        });

        // 快速操作按钮
        Utils.DOM.getAll('.quick-action-btn').forEach(btn => {
            Utils.DOM.on(btn, 'click', (e) => {
                const action = e.target.dataset.action;
                this.handleQuickAction(action);
            });
        });

        // 策略选择按钮
        Utils.DOM.getAll('.strategy-btn').forEach(btn => {
            Utils.DOM.on(btn, 'click', (e) => {
                const strategy = e.target.dataset.strategy;
                this.setStrategy(strategy);
            });
        });

        // 清空聊天按钮
        Utils.DOM.on('#clearChatBtn', 'click', () => this.clearChat());

        // 新建会话按钮
        Utils.DOM.on('#newSessionBtn', 'click', () => this.newSession());

        // 消息操作按钮委托事件
        Utils.DOM.on('#chatMessages', 'click', (e) => {
            if (e.target.classList.contains('message-action-btn')) {
                const action = e.target.dataset.action;
                const messageId = e.target.closest('.message').dataset.messageId;
                this.handleMessageAction(action, messageId);
            }
        });
    }

    /**
     * 设置输入框自动调整高度
     */
    setupAutoResize() {
        const input = Utils.DOM.get('#messageInput');
        if (input) {
            input.addEventListener('input', () => {
                input.style.height = 'auto';
                input.style.height = Math.min(input.scrollHeight, 120) + 'px';
            });
        }
    }

    /**
     * 发送消息
     */
    async sendMessage() {
        const input = Utils.DOM.get('#messageInput');
        const message = input.value.trim();
        
        if (!message || this.isTyping) return;

        // 添加用户消息到界面
        this.addMessage('user', message);
        
        // 清空输入框
        input.value = '';
        input.style.height = 'auto';
        this.updateSendButton();

        // 显示打字指示器
        this.showTypingIndicator();

        try {
            // 发送消息到服务器
            const response = await Utils.HTTP.post('/api/chat', {
                message: message,
                session_id: this.currentSessionId,
                strategy: this.strategy
            });

            // 隐藏打字指示器
            this.hideTypingIndicator();

            // 添加助手回复
            if (response.success) {
                this.addMessage('assistant', response.message, response.message_id);
                this.currentSessionId = response.session_id;
                this.updateSessionsList();
            } else {
                this.showError('发送消息失败：' + response.error);
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.showError('网络错误，请稍后重试');
            console.error('Send message error:', error);
        }
    }

    /**
     * 添加消息到聊天界面
     * @param {string} role - 角色 (user/assistant)
     * @param {string} content - 消息内容
     * @param {string} messageId - 消息ID
     */
    addMessage(role, content, messageId = null) {
        const messagesContainer = Utils.DOM.get('#chatMessages');
        if (!messagesContainer) {
            console.error('Messages container not found');
            return;
        }
        
        const messageId_ = messageId || Utils.String.generateId();
        
        const messageElement = Utils.DOM.create('div', {
            className: `message ${role}`,
            'data-message-id': messageId_
        });

        const avatar = Utils.DOM.create('div', {
            className: 'message-avatar'
        }, role === 'user' ? 'U' : 'AI');

        const contentElement = Utils.DOM.create('div', {
            className: 'message-content'
        });

        // 处理消息内容（支持Markdown）
        contentElement.innerHTML = this.formatMessageContent(content);

        const timeElement = Utils.DOM.create('div', {
            className: 'message-time'
        }, Utils.String.formatTime(new Date()));

        const actionsElement = Utils.DOM.create('div', {
            className: 'message-actions'
        });

        // 添加消息操作按钮
        if (role === 'assistant') {
            actionsElement.appendChild(Utils.DOM.create('button', {
                className: 'message-action-btn',
                'data-action': 'copy'
            }, '复制'));

            actionsElement.appendChild(Utils.DOM.create('button', {
                className: 'message-action-btn',
                'data-action': 'regenerate'
            }, '重新生成'));
        }

        messageElement.appendChild(avatar);
        messageElement.appendChild(contentElement);
        contentElement.appendChild(timeElement);
        contentElement.appendChild(actionsElement);

        messagesContainer.appendChild(messageElement);
        
        // 滚动到底部
        this.scrollToBottom();

        // 保存消息
        this.messages.push({
            id: messageId_,
            role: role,
            content: content,
            timestamp: new Date().toISOString()
        });
    }

    /**
     * 格式化消息内容
     * @param {string} content - 原始内容
     * @returns {string} - 格式化后的HTML
     */
    formatMessageContent(content) {
        // 简单的Markdown支持
        let formatted = Utils.String.escapeHtml(content);
        
        // 代码块
        formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
        });
        
        // 行内代码
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // 粗体
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // 斜体
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // 换行
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }

    /**
     * 显示打字指示器
     */
    showTypingIndicator() {
        this.isTyping = true;
        
        const container = Utils.DOM.get('#chatMessages');
        if (!container) {
            console.error('Messages container not found');
            return;
        }
        const indicator = Utils.DOM.create('div', {
            className: 'typing-indicator',
            id: 'typingIndicator'
        });

        const avatar = Utils.DOM.create('div', {
            className: 'message-avatar'
        }, 'AI');

        const dots = Utils.DOM.create('div', {
            className: 'typing-dots'
        });

        for (let i = 0; i < 3; i++) {
            dots.appendChild(Utils.DOM.create('div', {
                className: 'typing-dot'
            }));
        }

        indicator.appendChild(avatar);
        indicator.appendChild(dots);
        container.appendChild(indicator);
        
        this.scrollToBottom();
    }

    /**
     * 隐藏打字指示器
     */
    hideTypingIndicator() {
        this.isTyping = false;
        const indicator = Utils.DOM.get('#typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * 更新发送按钮状态
     */
    updateSendButton() {
        const input = Utils.DOM.get('#messageInput');
        const button = Utils.DOM.get('#sendButton');
        
        if (input && button) {
            const hasContent = input.value.trim().length > 0;
            button.disabled = !hasContent || this.isTyping;
        }
    }

    /**
     * 处理快速操作
     * @param {string} action - 操作类型
     */
    handleQuickAction(action) {
        const input = Utils.DOM.get('#messageInput');
        
        const quickActions = {
            'explain': '请解释一下',
            'summarize': '请总结一下',
            'translate': '请翻译成中文',
            'code': '请写一段代码'
        };

        if (quickActions[action]) {
            input.value = quickActions[action];
            input.focus();
            this.updateSendButton();
        }
    }

    /**
     * 设置策略
     * @param {string} strategy - 策略类型
     */
    setStrategy(strategy) {
        this.strategy = strategy;
        
        // 更新按钮状态
        Utils.DOM.getAll('.strategy-btn').forEach(btn => {
            Utils.DOM.removeClass(btn, 'active');
        });
        
        const activeBtn = Utils.DOM.get(`[data-strategy="${strategy}"]`);
        if (activeBtn) {
            Utils.DOM.addClass(activeBtn, 'active');
        }
    }

    /**
     * 处理消息操作
     * @param {string} action - 操作类型
     * @param {string} messageId - 消息ID
     */
    async handleMessageAction(action, messageId) {
        const message = this.messages.find(m => m.id === messageId);
        if (!message) return;

        switch (action) {
            case 'copy':
                try {
                    await navigator.clipboard.writeText(message.content);
                    this.showSuccess('已复制到剪贴板');
                } catch (error) {
                    this.showError('复制失败');
                }
                break;
                
            case 'regenerate':
                // 重新生成回复
                this.regenerateMessage(messageId);
                break;
        }
    }

    /**
     * 重新生成消息
     * @param {string} messageId - 消息ID
     */
    async regenerateMessage(messageId) {
        // 找到要重新生成的消息
        const messageIndex = this.messages.findIndex(m => m.id === messageId);
        if (messageIndex === -1) return;

        // 找到上一条用户消息
        let userMessage = null;
        for (let i = messageIndex - 1; i >= 0; i--) {
            if (this.messages[i].role === 'user') {
                userMessage = this.messages[i];
                break;
            }
        }

        if (!userMessage) return;

        // 移除当前消息
        const messageElement = Utils.DOM.get(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            messageElement.remove();
        }
        this.messages.splice(messageIndex, 1);

        // 显示打字指示器
        this.showTypingIndicator();

        try {
            // 重新发送请求
            const response = await Utils.HTTP.post('/api/chat/regenerate', {
                message: userMessage.content,
                session_id: this.currentSessionId,
                strategy: this.strategy
            });

            this.hideTypingIndicator();

            if (response.success) {
                this.addMessage('assistant', response.message, response.message_id);
            } else {
                this.showError('重新生成失败：' + response.error);
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.showError('网络错误，请稍后重试');
            console.error('Regenerate message error:', error);
        }
    }

    /**
     * 清空聊天
     */
    async clearChat() {
        const confirmed = await Utils.Modal.confirm('确定要清空当前聊天记录吗？', '清空聊天');
        if (confirmed) {
            const container = Utils.DOM.get('#chatMessages');
            if (container) {
                container.innerHTML = '';
            }
            this.messages = [];
            this.currentSessionId = null;
        }
    }

    /**
     * 新建会话
     */
    newSession() {
        // 直接清空聊天界面，不显示确认对话框
        const container = Utils.DOM.get('#chatMessages');
        if (container) {
            container.innerHTML = '';
        }
        this.messages = [];
        this.currentSessionId = null;
        this.showSuccess('已创建新会话');
    }

    /**
     * 加载聊天历史
     */
    async loadChatHistory() {
        try {
            const response = await Utils.HTTP.get('/api/chat/history');
            if (response.success && response.messages) {
                response.messages.forEach(msg => {
                    this.addMessage(msg.role, msg.content, msg.id);
                });
                this.currentSessionId = response.session_id;
            }
        } catch (error) {
            console.error('Load chat history error:', error);
        }
    }

    /**
     * 更新会话列表
     */
    async updateSessionsList() {
        try {
            const response = await Utils.HTTP.get('/api/sessions');
            if (response.success) {
                // 更新侧边栏的会话列表
                const sessionsList = Utils.DOM.get('#sessionsList');
                if (sessionsList) {
                    sessionsList.innerHTML = '';
                    response.sessions.forEach(session => {
                        const sessionElement = this.createSessionElement(session);
                        sessionsList.appendChild(sessionElement);
                    });
                }
            }
        } catch (error) {
            console.error('Update sessions list error:', error);
        }
    }

    /**
     * 创建会话元素
     * @param {Object} session - 会话数据
     * @returns {Element}
     */
    createSessionElement(session) {
        const element = Utils.DOM.create('div', {
            className: 'session-item',
            'data-session-id': session.id
        });

        const title = Utils.DOM.create('div', {
            className: 'session-title'
        }, Utils.String.truncate(session.title, 30));

        const time = Utils.DOM.create('div', {
            className: 'session-time'
        }, Utils.String.formatTime(session.updated_at));

        element.appendChild(title);
        element.appendChild(time);

        // 点击切换会话
        Utils.DOM.on(element, 'click', () => {
            this.loadSession(session.id);
        });

        return element;
    }

    /**
     * 加载指定会话
     * @param {string} sessionId - 会话ID
     */
    async loadSession(sessionId) {
        try {
            const response = await Utils.HTTP.get(`/api/sessions/${sessionId}`);
            if (response.success) {
                // 清空当前聊天
                const container = Utils.DOM.get('#chatMessages');
                if (container) {
                    container.innerHTML = '';
                }
                this.messages = [];

                // 加载会话消息
                response.messages.forEach(msg => {
                    this.addMessage(msg.role, msg.content, msg.id);
                });

                this.currentSessionId = sessionId;
            }
        } catch (error) {
            this.showError('加载会话失败');
            console.error('Load session error:', error);
        }
    }

    /**
     * 滚动到底部
     */
    scrollToBottom() {
        const container = Utils.DOM.get('#messagesContainer');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    /**
     * 显示成功消息
     * @param {string} message - 消息内容
     */
    showSuccess(message) {
        this.showToast(message, 'success');
    }

    /**
     * 显示错误消息
     * @param {string} message - 消息内容
     */
    showError(message) {
        this.showToast(message, 'error');
    }

    /**
     * 显示Toast通知
     * @param {string} message - 消息内容
     * @param {string} type - 类型
     */
    showToast(message, type = 'info') {
        const toast = Utils.DOM.create('div', {
            className: `toast ${type}`
        }, message);

        document.body.appendChild(toast);

        // 显示动画
        setTimeout(() => {
            Utils.DOM.addClass(toast, 'show');
        }, 100);

        // 自动隐藏
        setTimeout(() => {
            Utils.DOM.removeClass(toast, 'show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.chatManager = new ChatManager();
});