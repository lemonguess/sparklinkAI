// SparkLink AI 前端应用
class SparkLinkApp {
    constructor() {
        this.currentSessionId = null;
        this.sessions = [];
        this.knowledgeBases = [];
        this.settings = {
            maxTokens: 2000,
            temperature: 0.7,
            searchTopK: 5,
            similarityThreshold: 0.7
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadSettings();
        
        // 异步加载数据，避免阻塞页面渲染
        setTimeout(() => {
            this.loadSessions();
            this.loadKnowledgeBases();
            this.checkSystemStatus();
            
            // 数据加载完成后隐藏加载指示器
            setTimeout(() => {
                this.hidePageLoader();
            }, 500);
        }, 100);
        
        // 定期检查系统状态
        setInterval(() => this.checkSystemStatus(), 30000);
    }
    
    hidePageLoader() {
        const loader = document.getElementById('pageLoader');
        if (loader) {
            loader.classList.add('fade-out');
            setTimeout(() => {
                loader.style.display = 'none';
            }, 500);
        }
    }
    
    bindEvents() {
        // 发送消息
        document.getElementById('sendBtn').addEventListener('click', () => this.sendMessage());
        document.getElementById('messageInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // 自动调整输入框高度
        document.getElementById('messageInput').addEventListener('input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
        });
        
        // 新建会话
        document.getElementById('newSessionBtn').addEventListener('click', () => this.createNewSession());
        
        // 清空聊天
        document.getElementById('clearChatBtn').addEventListener('click', () => this.clearChat());
        
        // 上传文档
        document.getElementById('uploadDocBtn').addEventListener('click', () => this.showUploadModal());
        
        // 设置
        document.getElementById('settingsBtn').addEventListener('click', () => this.showSettingsModal());
        
        // 模态框事件
        this.bindModalEvents();
        
        // 文件上传事件
        this.bindFileUploadEvents();
    }
    
    bindModalEvents() {
        // 关闭模态框
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').style.display = 'none';
            });
        });
        
        // 点击模态框外部关闭
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        });
        
        // 上传模态框按钮
        document.getElementById('cancelUploadBtn').addEventListener('click', () => {
            document.getElementById('uploadModal').style.display = 'none';
        });
        
        document.getElementById('confirmUploadBtn').addEventListener('click', () => this.uploadFiles());
        
        // 设置模态框按钮
        document.getElementById('saveSettingsBtn').addEventListener('click', () => this.saveSettings());
        document.getElementById('resetSettingsBtn').addEventListener('click', () => this.resetSettings());
        
        // 设置滑块值显示
        document.getElementById('temperature').addEventListener('input', (e) => {
            document.getElementById('temperatureValue').textContent = e.target.value;
        });
        
        document.getElementById('similarityThreshold').addEventListener('input', (e) => {
            document.getElementById('similarityValue').textContent = e.target.value;
        });
    }
    
    bindFileUploadEvents() {
        console.log("Binding file upload events...");
        // 使用事件委托，避免DOM重建问题
        document.addEventListener('click', (e) => {
            if (e.target.closest('#uploadArea') && !e.target.matches('#fileInput')) {
                const fileInput = document.getElementById('fileInput');
                if (fileInput) {
                    fileInput.click();
                }
            }
        });
        
        document.addEventListener('change', (e) => {
            if (e.target && e.target.id === 'fileInput' && e.target.files) {
                const files = Array.from(e.target.files);
                this.handleFileSelection(files);
            }
        });
        
        // 拖拽事件
        document.addEventListener('dragover', (e) => {
            if (e.target.closest('#uploadArea')) {
                e.preventDefault();
                e.target.closest('#uploadArea').classList.add('dragover');
            }
        });
        
        document.addEventListener('dragleave', (e) => {
            if (e.target.closest('#uploadArea')) {
                e.target.closest('#uploadArea').classList.remove('dragover');
            }
        });
        
        document.addEventListener('drop', (e) => {
            if (e.target.closest('#uploadArea')) {
                e.preventDefault();
                e.target.closest('#uploadArea').classList.remove('dragover');
                const files = Array.from(e.dataTransfer.files);
                this.handleFileSelection(files);
            }
        });
    }
    
    async loadSessions() {
        try {
            const response = await fetch('/api/v1/chat/sessions');
            if (response.ok) {
                const data = await response.json();
                this.sessions = data.data || [];
                this.renderSessions();
            }
        } catch (error) {
            console.error('加载会话失败:', error);
        }
    }
    
    async loadKnowledgeBases() {
        try {
            const response = await fetch('/api/v1/kb/knowledge-bases');
            if (response.ok) {
                const data = await response.json();
                this.knowledgeBases = data.data || [];
                this.renderKnowledgeBases();
                this.updateKnowledgeBaseSelect();
            }
        } catch (error) {
            console.error('加载知识库失败:', error);
        }
    }
    
    async checkSystemStatus() {
        try {
            const response = await fetch('/api/v1/system/status');
            if (response.ok) {
                const data = await response.json();
                this.updateSystemStatus(data.data);
            }
        } catch (error) {
            console.error('检查系统状态失败:', error);
        }
    }
    
    renderSessions() {
        const sessionsList = document.getElementById('sessionsList');
        sessionsList.innerHTML = '';
        
        this.sessions.forEach(session => {
            const sessionElement = document.createElement('div');
            sessionElement.className = `session-item ${session.id === this.currentSessionId ? 'active' : ''}`;
            sessionElement.innerHTML = `
                <div class="session-title">${session.title}</div>
                <div class="session-time">${this.formatTime(session.updated_at)}</div>
            `;
            
            sessionElement.addEventListener('click', () => this.selectSession(session.id));
            sessionsList.appendChild(sessionElement);
        });
    }
    
    renderKnowledgeBases() {
        const knowledgeList = document.getElementById('knowledgeList');
        knowledgeList.innerHTML = '';
        
        this.knowledgeBases.forEach(kb => {
            const kbElement = document.createElement('div');
            kbElement.className = 'knowledge-item';
            kbElement.innerHTML = `
                <div class="knowledge-title">${kb.name}</div>
                <div class="knowledge-info">${kb.document_count} 文档 · ${kb.chunk_count} 块</div>
            `;
            
            knowledgeList.appendChild(kbElement);
        });
    }
    
    updateKnowledgeBaseSelect() {
        const select = document.getElementById('kbSelect');
        select.innerHTML = '';
        
        this.knowledgeBases.forEach(kb => {
            const option = document.createElement('option');
            option.value = kb.id;
            option.textContent = kb.name;
            select.appendChild(option);
        });
    }
    
    updateSystemStatus(status) {
        const dbStatus = document.getElementById('dbStatus');
        const redisStatus = document.getElementById('redisStatus');
        const milvusStatus = document.getElementById('milvusStatus');
        
        dbStatus.textContent = status.database_status;
        dbStatus.className = `status-value status-${status.database_status}`;
        
        redisStatus.textContent = status.redis_status;
        redisStatus.className = `status-value status-${status.redis_status}`;
        
        milvusStatus.textContent = status.milvus_status;
        milvusStatus.className = `status-value status-${status.milvus_status}`;
    }
    
    async createNewSession() {
        try {
            const response = await fetch('/api/v1/chat/sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: '新会话',
                    user_id: 1 // 临时使用固定用户ID
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.sessions.unshift(data.data);
                this.renderSessions();
                this.selectSession(data.data.id);
                this.showToast('新会话创建成功', 'success');
            } else {
                const error = await response.json();
                this.showToast(error.detail || '创建会话失败', 'error');
            }
        } catch (error) {
            console.error('创建会话失败:', error);
            this.showToast('创建会话失败', 'error');
        }
    }
    
    async selectSession(sessionId) {
        this.currentSessionId = sessionId;
        this.renderSessions();
        
        const session = this.sessions.find(s => s.id === sessionId);
        if (session) {
            document.getElementById('currentSessionTitle').textContent = session.title;
        }
        
        // 加载会话消息
        await this.loadSessionMessages(sessionId);
    }
    
    async loadSessionMessages(sessionId) {
        try {
            const response = await fetch(`/api/v1/chat/sessions/${sessionId}/messages`);
            if (response.ok) {
                const data = await response.json();
                this.renderMessages(data.data || []);
            }
        } catch (error) {
            console.error('加载消息失败:', error);
        }
    }
    
    renderMessages(messages) {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = '';
        
        if (messages.length === 0) {
            chatMessages.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    <h3>开始新的对话</h3>
                    <p>您可以问我任何问题，我会尽力帮助您。</p>
                </div>
            `;
            return;
        }
        
        messages.forEach(message => {
            this.addMessageToChat(message.role, message.content, message.created_at, message.sources);
        });
        
        this.scrollToBottom();
    }
    
    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        if (!this.currentSessionId) {
            this.showToast('请先选择或创建一个会话', 'warning');
            return;
        }
        
        // 清空输入框
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        // 添加用户消息到界面
        this.addMessageToChat('user', message);
        
        // 显示打字指示器
        this.showTypingIndicator();
        
        try {
            const useKnowledgeBase = document.getElementById('useKnowledgeBase').checked;
            const useWebSearch = document.getElementById('useWebSearch').checked;
            
            // 使用流式接口
            const response = await fetch('/api/v1/chat/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.currentSessionId,
                    use_knowledge_base: useKnowledgeBase,
                    use_web_search: useWebSearch,
                    max_tokens: this.settings.maxTokens,
                    temperature: this.settings.temperature
                })
            });
            
            if (!response.ok) {
                this.hideTypingIndicator();
                const error = await response.text();
                this.addMessageToChat('assistant', '抱歉，处理您的请求时出现了错误：' + error);
                return;
            }
            
            // 处理流式响应
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantMessageElement = null;
            let fullResponse = '';
            let sources = null;
            
            this.hideTypingIndicator();
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'start') {
                                // 创建助手消息元素
                                assistantMessageElement = this.createAssistantMessageElement();
                            } else if (data.type === 'content') {
                                // 追加内容
                                fullResponse += data.content;
                                if (assistantMessageElement) {
                                    this.updateMessageContent(assistantMessageElement, fullResponse);
                                }
                            } else if (data.type === 'end') {
                                // 完成，添加来源信息
                                sources = {
                                    knowledge_sources: data.knowledge_sources || [],
                                    web_search_results: data.web_search_results || []
                                };
                                if (assistantMessageElement) {
                                    this.addSourcesToMessage(assistantMessageElement, sources);
                                }
                            } else if (data.type === 'error') {
                                this.addMessageToChat('assistant', '抱歉，处理您的请求时出现了错误：' + data.error);
                            }
                        } catch (e) {
                            console.error('解析SSE数据失败:', e);
                        }
                    }
                }
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            console.error('发送消息失败:', error);
            this.addMessageToChat('assistant', '抱歉，网络连接出现问题，请稍后重试。');
        }
    }
    
    addMessageToChat(role, content, timestamp = null, sources = null) {
        const chatMessages = document.getElementById('chatMessages');
        
        // 如果是第一条消息，清除欢迎信息
        const welcomeMessage = chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${role} fade-in`;
        
        const avatar = role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        const time = timestamp ? this.formatTime(timestamp) : this.formatTime(new Date().toISOString());
        
        let sourcesHtml = '';
        if (sources && (sources.knowledge_sources?.length > 0 || sources.web_search_results?.length > 0)) {
            sourcesHtml = '<div class="message-sources">';
            
            if (sources.knowledge_sources?.length > 0) {
                sourcesHtml += sources.knowledge_sources.map(source => 
                    `<div class="source-item"><i class="fas fa-database"></i> ${source.title || '知识库'}</div>`
                ).join('');
            }
            
            if (sources.web_search_results?.length > 0) {
                sourcesHtml += sources.web_search_results.map(source => 
                    `<div class="source-item"><i class="fas fa-globe"></i> ${source.title || '网络搜索'}</div>`
                ).join('');
            }
            
            sourcesHtml += '</div>';
        }
        
        messageElement.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${this.formatMessageContent(content)}</div>
                ${sourcesHtml}
                <div class="message-time">${time}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }
    
    showTypingIndicator() {
        const chatMessages = document.getElementById('chatMessages');
        const typingElement = document.createElement('div');
        typingElement.className = 'message assistant typing-message';
        typingElement.innerHTML = `
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(typingElement);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const typingMessage = document.querySelector('.typing-message');
        if (typingMessage) {
            typingMessage.remove();
        }
    }
    
    createAssistantMessageElement() {
        const chatMessages = document.getElementById('chatMessages');
        
        // 如果是第一条消息，清除欢迎信息
        const welcomeMessage = chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message assistant fade-in';
        
        const avatar = '<i class="fas fa-robot"></i>';
        const time = this.formatTime(new Date().toISOString());
        
        messageElement.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text"></div>
                <div class="message-sources"></div>
                <div class="message-time">${time}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        this.scrollToBottom();
        
        return messageElement;
    }
    
    updateMessageContent(messageElement, content) {
        const messageText = messageElement.querySelector('.message-text');
        if (messageText) {
            messageText.innerHTML = this.formatMessageContent(content);
        }
        this.scrollToBottom();
    }
    
    addSourcesToMessage(messageElement, sources) {
        const sourcesContainer = messageElement.querySelector('.message-sources');
        if (!sourcesContainer || (!sources.knowledge_sources?.length && !sources.web_search_results?.length)) {
            return;
        }
        
        let sourcesHtml = '';
        
        if (sources.knowledge_sources?.length > 0) {
            sourcesHtml += sources.knowledge_sources.map(source => 
                `<div class="source-item"><i class="fas fa-database"></i> ${source.title || '知识库'}</div>`
            ).join('');
        }
        
        if (sources.web_search_results?.length > 0) {
            sourcesHtml += sources.web_search_results.map(source => 
                `<div class="source-item"><i class="fas fa-globe"></i> ${source.title || '网络搜索'}</div>`
            ).join('');
        }
        
        sourcesContainer.innerHTML = sourcesHtml;
    }
    
    formatMessageContent(content) {
        // 使用marked.js进行Markdown渲染
        if (typeof marked !== 'undefined') {
            try {
                // 配置marked选项
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    sanitize: false
                });
                return marked.parse(content);
            } catch (e) {
                console.error('Markdown渲染失败:', e);
            }
        }
        
        // 降级到简单的格式化
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>')
            .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    }
    
    scrollToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    clearChat() {
        if (!this.currentSessionId) return;
        
        if (confirm('确定要清空当前会话的所有消息吗？')) {
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    <h3>会话已清空</h3>
                    <p>您可以开始新的对话。</p>
                </div>
            `;
            this.showToast('会话已清空', 'success');
        }
    }
    
    showUploadModal() {
        document.getElementById('uploadModal').style.display = 'block';
    }
    
    showSettingsModal() {
        // 加载当前设置到表单
        document.getElementById('maxTokens').value = this.settings.maxTokens;
        document.getElementById('temperature').value = this.settings.temperature;
        document.getElementById('temperatureValue').textContent = this.settings.temperature;
        document.getElementById('searchTopK').value = this.settings.searchTopK;
        document.getElementById('similarityThreshold').value = this.settings.similarityThreshold;
        document.getElementById('similarityValue').textContent = this.settings.similarityThreshold;
        
        document.getElementById('settingsModal').style.display = 'block';
    }
    
    handleFileSelection(files) {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');

        if (files.length > 0) {
            const fileNames = files.map(f => f.name).join(', ');
            
            // 只更新文本内容，不替换整个区域
            const p1 = uploadArea.querySelector('p:nth-of-type(1)');
            const p2 = uploadArea.querySelector('p:nth-of-type(2)');
            const icon = uploadArea.querySelector('.upload-icon');

            if(p1) p1.textContent = `已选择 ${files.length} 个文件`;
            if(p2) p2.textContent = fileNames;
            if(icon) icon.innerHTML = `<i class="fas fa-file-alt"></i>`;


            // 更新文件输入
            const dt = new DataTransfer();
            files.forEach(file => dt.items.add(file));
            if (fileInput) {
                fileInput.files = dt.files;
            }
        }
    }
    
    async uploadFiles() {
        console.log("uploadFiles called.");
        const fileInput = document.getElementById('fileInput');
        const kbSelect = document.getElementById('kbSelect');
        console.log("fileInput in uploadFiles:", fileInput);
        
        // 检查元素是否存在
        if (!fileInput) {
            this.showToast('文件输入元素未找到', 'error');
            return;
        }
        
        if (!kbSelect) {
            this.showToast('知识库选择元素未找到', 'error');
            return;
        }
        
        const files = fileInput.files;
        
        // 检查files是否存在
        if (!files || files.length === 0) {
            this.showToast('请选择要上传的文件', 'warning');
            return;
        }
        
        const knowledgeBaseId = kbSelect.value;
        if (!knowledgeBaseId) {
            this.showToast('请选择知识库', 'warning');
            return;
        }
        
        // 将FileList转换为数组，避免后续DOM操作影响
        const fileArray = Array.from(files);
        
        this.showUploadProgress();
        
        try {
            for (let i = 0; i < fileArray.length; i++) {
                const file = fileArray[i];
                const formData = new FormData();
                formData.append('file', file);
                formData.append('knowledge_base_id', knowledgeBaseId);
                
                const response = await fetch('/api/v1/kb/documents/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `上传文件 ${file.name} 失败`);
                }
                
                // 更新进度
                const progress = ((i + 1) / fileArray.length) * 100;
                this.updateUploadProgress(progress, `正在上传 ${file.name}...`);
            }
            
            this.showToast('文件上传成功', 'success');
            this.hideUploadModal();
            this.loadKnowledgeBases(); // 刷新知识库列表
            
        } catch (error) {
            console.error('上传失败:', error);
            this.showToast(error.message || '上传失败', 'error');
        } finally {
            this.hideUploadProgress();
        }
    }
    
    showUploadProgress() {
        document.getElementById('uploadProgress').style.display = 'block';
        document.getElementById('confirmUploadBtn').disabled = true;
    }
    
    updateUploadProgress(percent, text) {
        const progressFill = document.querySelector('.progress-fill');
        const progressText = document.querySelector('.progress-text');
        
        progressFill.style.width = percent + '%';
        progressText.textContent = text;
    }
    
    hideUploadProgress() {
        document.getElementById('uploadProgress').style.display = 'none';
        document.getElementById('confirmUploadBtn').disabled = false;
    }
    
    hideUploadModal() {
        console.log("hideUploadModal called, resetting uploadArea.");
        document.getElementById('uploadModal').style.display = 'none';
        // 重置上传区域
        const uploadArea = document.getElementById('uploadArea');
        uploadArea.innerHTML = `
            <div class="upload-icon">
                <i class="fas fa-cloud-upload-alt"></i>
            </div>
            <p>拖拽文件到此处或点击选择文件</p>
            <p class="upload-hint">支持 PDF, DOC, DOCX, TXT, MD 等格式</p>
            <input type="file" id="fileInput" multiple accept=".pdf,.doc,.docx,.txt,.md,.ppt,.pptx">
        `;
        this.bindFileUploadEvents();
    }
    
    saveSettings() {
        this.settings.maxTokens = parseInt(document.getElementById('maxTokens').value);
        this.settings.temperature = parseFloat(document.getElementById('temperature').value);
        this.settings.searchTopK = parseInt(document.getElementById('searchTopK').value);
        this.settings.similarityThreshold = parseFloat(document.getElementById('similarityThreshold').value);
        
        localStorage.setItem('sparklink_settings', JSON.stringify(this.settings));
        document.getElementById('settingsModal').style.display = 'none';
        this.showToast('设置已保存', 'success');
    }
    
    resetSettings() {
        this.settings = {
            maxTokens: 2000,
            temperature: 0.7,
            searchTopK: 5,
            similarityThreshold: 0.7
        };
        
        localStorage.removeItem('sparklink_settings');
        this.showSettingsModal(); // 重新显示设置
        this.showToast('设置已重置', 'success');
    }
    
    loadSettings() {
        const saved = localStorage.getItem('sparklink_settings');
        if (saved) {
            this.settings = { ...this.settings, ...JSON.parse(saved) };
        }
    }
    
    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type} show`;
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // 1分钟内
            return '刚刚';
        } else if (diff < 3600000) { // 1小时内
            return Math.floor(diff / 60000) + '分钟前';
        } else if (diff < 86400000) { // 24小时内
            return Math.floor(diff / 3600000) + '小时前';
        } else {
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString().slice(0, 5);
        }
    }
}

// 快速消息功能
function sendQuickMessage(message) {
    const messageInput = document.getElementById('messageInput');
    messageInput.value = message;
    app.sendMessage();
}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new SparkLinkApp();
});

// 全局错误处理
window.addEventListener('error', (e) => {
    console.error('全局错误:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('未处理的Promise拒绝:', e.reason);
});