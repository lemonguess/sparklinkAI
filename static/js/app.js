// SparkLink AI 前端应用
class SparkLinkApp {
    constructor() {
        this.currentSessionId = null;
        this.currentKnowledgeBaseId = null;
        this.sessions = [];
        this.knowledgeBases = [];
        this.documents = [];
        this.messageCache = new Map(); // 缓存会话消息，避免重复加载
        this.settings = {
            maxTokens: 2000,
            temperature: 0.7,
            searchTopK: 5,
            similarityThreshold: 0.7
        };
        this.currentReader = null; // 用于停止流式输出
        this.currentRequestId = null; // 用于停止流式输出
        
        this.init();
    }
    
    // 生成UUID（符合uuid4.hex格式）
    generateUUID() {
        return 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'.replace(/[x]/g, function() {
            return (Math.random() * 16 | 0).toString(16);
        });
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
        
        // 移除定期检查系统状态，仅在页面刷新时调用
        // setInterval(() => this.checkSystemStatus(), 30000);
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
        
        // 停止生成
        document.getElementById('stopBtn').addEventListener('click', () => this.stopGeneration());
        
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
        
        // 刷新文档
        document.getElementById('refreshDocsBtn').addEventListener('click', () => this.loadDocuments());
        
        // 新建知识库
        document.getElementById('newKnowledgeBaseBtn').addEventListener('click', () => this.showNewKnowledgeBaseModal());
        
        // 知识库检索测试
        document.getElementById('testKnowledgeBtn').addEventListener('click', () => this.showTestKnowledgeModal());
        
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
            const response = await fetch('/api/v1/chat/sessions?user_id=admin123456789abcdef0123456789ab');
            if (response.ok) {
                const data = await response.json();
                this.sessions = data.data || [];
                // 按updated_at时间字符串倒序排列
                this.sessions.sort((a, b) => {
                    return new Date(b.updated_at) - new Date(a.updated_at);
                });
                this.renderSessions();
            }
        } catch (error) {
            console.error('加载会话失败:', error);
        }
    }
    
    async loadKnowledgeBases() {
        try {
            const response = await fetch('/api/v1/kb/group/get_groups?user_id=test_user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
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
                <div class="session-content">
                    <div class="session-title" data-session-id="${session.id}">${session.title}</div>
                    <div class="session-time">${this.formatTime(session.updated_at)}</div>
                </div>
                <div class="session-actions">
                    <button class="edit-title-btn" data-session-id="${session.id}" title="编辑标题">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="delete-session-btn" data-session-id="${session.id}" title="删除会话">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            // 点击会话内容区域选择会话
            const sessionContent = sessionElement.querySelector('.session-content');
            sessionContent.addEventListener('click', () => this.selectSession(session.id));
            
            // 点击编辑按钮
            const editBtn = sessionElement.querySelector('.edit-title-btn');
            editBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.editSessionTitle(session.id, session.title);
            });
            
            // 点击删除按钮
            const deleteBtn = sessionElement.querySelector('.delete-session-btn');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteSession(session.id, session.title);
            });
            
            sessionsList.appendChild(sessionElement);
        });
    }
    
    renderKnowledgeBases() {
        const knowledgeList = document.getElementById('knowledgeList');
        if (!knowledgeList) return;
        
        if (this.knowledgeBases.length === 0) {
            knowledgeList.innerHTML = '<div class="empty-state">暂无知识库</div>';
            return;
        }
        
        knowledgeList.innerHTML = this.knowledgeBases.map(kb => `
            <div class="knowledge-item ${this.currentKnowledgeBaseId === kb.id ? 'active' : ''}" data-id="${kb.id}">
                <div class="knowledge-item-header">
                    <div class="knowledge-item-title">${kb.group_name}</div>
                    <div class="knowledge-item-actions">
                        <button class="btn-icon" onclick="app.editKnowledgeBase(${kb.id}, '${kb.group_name}')" title="编辑">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-icon" onclick="app.deleteKnowledgeBase(${kb.id}, '${kb.group_name}')" title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="knowledge-item-info">
                    <span>文档: ${kb.doc_name || '未命名'}</span>
                    <span class="knowledge-item-count">ID: ${kb.id}</span>
                </div>
            </div>
        `).join('');
        
        // 添加点击事件选择知识库
        knowledgeList.querySelectorAll('.knowledge-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.knowledge-item-actions')) {
                    const kbId = parseInt(item.dataset.id);
                    this.selectKnowledgeBase(kbId);
                }
            });
        });
    }
    
    // 选择知识库
    async selectKnowledgeBase(kbId) {
        this.currentKnowledgeBaseId = kbId;
        
        // 更新知识库列表显示
        this.renderKnowledgeBases();
        
        // 更新文档面板标题
        const selectedKb = this.knowledgeBases.find(kb => kb.id === kbId);
        const kbTitle = document.getElementById('selectedKbTitle');
        if (kbTitle && selectedKb) {
            kbTitle.textContent = selectedKb.group_name;
        }
        
        // 显示文档面板
        const documentPanel = document.getElementById('documentPanel');
        if (documentPanel) {
            documentPanel.style.display = 'block';
        }
        
        // 加载该知识库的文档
        await this.loadDocuments();
    }
    
    // 加载文档列表
    async loadDocuments() {
        if (!this.currentKnowledgeBaseId) {
            return;
        }
        
        try {
            const response = await fetch(`/api/knowledge_base/${this.currentKnowledgeBaseId}/documents`);
            if (response.ok) {
                this.documents = await response.json();
                this.renderDocuments();
            } else {
                console.error('Failed to load documents');
                this.showToast('加载文档失败', 'error');
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            this.showToast('加载文档失败', 'error');
        }
    }
    
    // 渲染文档列表
    renderDocuments() {
        const documentList = document.getElementById('documentList');
        if (!documentList) return;
        
        if (this.documents.length === 0) {
            documentList.innerHTML = '<div class="empty-state">暂无文档</div>';
            return;
        }
        
        documentList.innerHTML = this.documents.map(doc => `
            <div class="document-item" data-id="${doc.id}">
                <div class="document-info">
                    <div class="document-name">${doc.name}</div>
                    <div class="document-meta">
                        <span>大小: ${this.formatFileSize(doc.size || 0)}</span>
                        <span>上传时间: ${this.formatTime(doc.created_at)}</span>
                    </div>
                </div>
                <div class="document-actions">
                    <button class="btn-icon" onclick="app.deleteDocument(${doc.id}, '${doc.name}')" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // 删除文档
    async deleteDocument(docId, docName) {
        if (!confirm(`确定要删除文档 "${docName}" 吗？`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/documents/${docId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.showToast('文档删除成功', 'success');
                await this.loadDocuments(); // 重新加载文档列表
            } else {
                this.showToast('文档删除失败', 'error');
            }
        } catch (error) {
            console.error('Error deleting document:', error);
            this.showToast('文档删除失败', 'error');
        }
    }

    updateKnowledgeBaseSelect() {
        const kbSelect = document.getElementById('kbSelect');
        const testKbSelect = document.getElementById('testKbSelect');
        
        if (kbSelect) {
            kbSelect.innerHTML = '<option value="">选择知识库</option>' + 
                this.knowledgeBases.map(kb => 
                    `<option value="${kb.id}">${kb.group_name}</option>`
                ).join('');
        }
        
        if (testKbSelect) {
            testKbSelect.innerHTML = '<option value="">全部知识库</option>' + 
                this.knowledgeBases.map(kb => 
                    `<option value="${kb.id}">${kb.group_name}</option>`
                ).join('');
        }
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
        // 清空当前会话选择
        this.currentSessionId = null;
        this.renderSessions();
        
        // 清空聊天界面，显示欢迎消息
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <i class="fas fa-robot"></i>
                </div>
                <h3>开始新的对话</h3>
                <p>您可以问我任何问题，我会尽力帮助您。</p>
            </div>
        `;
        
        // 更新会话标题
        document.getElementById('currentSessionTitle').textContent = '新会话';
        
        // 聚焦到输入框
        document.getElementById('messageInput').focus();
        
        this.showToast('准备开始新对话', 'success');
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
    
    editSessionTitle(sessionId, currentTitle) {
        const titleElement = document.querySelector(`[data-session-id="${sessionId}"].session-title`);
        if (!titleElement) return;
        
        // 创建输入框
        const input = document.createElement('input');
        input.type = 'text';
        input.value = currentTitle;
        input.className = 'session-title-input';
        input.maxLength = 200;
        
        // 替换标题元素
        titleElement.style.display = 'none';
        titleElement.parentNode.insertBefore(input, titleElement);
        
        // 聚焦并选中文本
        input.focus();
        input.select();
        
        // 处理保存
        const saveTitle = async () => {
            const newTitle = input.value.trim();
            if (newTitle && newTitle !== currentTitle) {
                await this.updateSessionTitle(sessionId, newTitle);
            }
            // 恢复显示
            input.remove();
            titleElement.style.display = 'block';
        };
        
        // 处理取消
        const cancelEdit = () => {
            input.remove();
            titleElement.style.display = 'block';
        };
        
        // 绑定事件
        input.addEventListener('blur', saveTitle);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveTitle();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelEdit();
            }
        });
    }

    updateSessionTitleWithAnimation(sessionId, newTitle) {
        console.log('执行updateSessionTitleWithAnimation:', sessionId, newTitle);
        // 更新本地会话数据
        const session = this.sessions.find(s => s.id === sessionId);
        if (session) {
            console.log('找到会话:', session);
            session.title = newTitle;
            
            // 如果是当前会话，更新当前会话标题显示
            if (sessionId === this.currentSessionId) {
                const currentTitleElement = document.getElementById('currentSessionTitle');
                if (currentTitleElement) {
                    // 添加渐变动画效果
                    currentTitleElement.style.transition = 'opacity 0.3s ease';
                    currentTitleElement.style.opacity = '0.5';
                    
                    setTimeout(() => {
                        currentTitleElement.textContent = newTitle;
                        currentTitleElement.style.opacity = '1';
                    }, 150);
                }
            }
            
            // 更新会话列表中的标题，带动画效果
            const sessionElement = document.querySelector(`[data-session-id="${sessionId}"]`);
            if (sessionElement) {
                const titleElement = sessionElement.querySelector('.session-title');
                if (titleElement) {
                    // 添加闪烁动画效果
                    titleElement.style.transition = 'all 0.3s ease';
                    titleElement.style.backgroundColor = '#e3f2fd';
                    titleElement.style.transform = 'scale(1.02)';
                    
                    setTimeout(() => {
                        titleElement.textContent = newTitle;
                        setTimeout(() => {
                            titleElement.style.backgroundColor = '';
                            titleElement.style.transform = 'scale(1)';
                        }, 300);
                    }, 150);
                }
            }
        }
    }
    
    async updateSessionTitle(sessionId, newTitle) {
        try {
            const response = await fetch('/api/v1/chat/sessions/update_title', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    title: newTitle
                })
            });
            
            const result = await response.json();
            if (result.success) {
                // 更新本地会话数据
                const session = this.sessions.find(s => s.id === sessionId);
                if (session) {
                    session.title = newTitle;
                }
                // 重新渲染会话列表
                this.renderSessions();
                this.showToast('标题修改成功', 'success');
            } else {
                this.showToast(result.message || '修改标题失败', 'error');
            }
        } catch (error) {
            console.error('修改会话标题失败:', error);
            this.showToast('修改标题失败', 'error');
        }
    }
    
    async deleteSession(sessionId, sessionTitle) {
        if (!confirm(`确定要删除会话"${sessionTitle}"吗？\n\n注意：此操作将永久删除会话及其所有消息，无法恢复。`)) {
            return;
        }
        
        try {
            const response = await fetch('/api/v1/chat/sessions/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: sessionId
                })
            });
            
            const result = await response.json();
            if (result.success) {
                // 从本地会话列表中移除
                this.sessions = this.sessions.filter(s => s.id !== sessionId);
                
                // 如果删除的是当前会话，清空聊天界面
                if (this.currentSessionId === sessionId) {
                    this.currentSessionId = null;
                    const chatMessages = document.getElementById('chatMessages');
                    chatMessages.innerHTML = `
                        <div class="welcome-message">
                            <div class="welcome-icon">
                                <i class="fas fa-robot"></i>
                            </div>
                            <h3>欢迎使用 SparkLink AI</h3>
                            <p>我是您的智能助手，可以帮您进行对话、搜索知识库、获取信息等。</p>
                        </div>
                    `;
                    document.getElementById('currentSessionTitle').textContent = '选择或创建一个会话开始聊天';
                }
                
                // 清除消息缓存
                this.messageCache.delete(sessionId);
                
                // 重新渲染会话列表
                this.renderSessions();
                this.showToast('会话删除成功', 'success');
            } else {
                this.showToast(result.message || '删除会话失败', 'error');
            }
        } catch (error) {
            console.error('删除会话失败:', error);
            this.showToast('删除会话失败', 'error');
        }
    }
    
    async loadSessionMessages(sessionId) {
        try {
            // 检查缓存
            if (this.messageCache.has(sessionId)) {
                this.renderMessages(this.messageCache.get(sessionId));
                return;
            }
            
            const response = await fetch(`/api/v1/chat/sessions/${sessionId}/messages`);
            if (response.ok) {
                const data = await response.json();
                const messages = data.data || [];
                // 缓存消息
                this.messageCache.set(sessionId, messages);
                this.renderMessages(messages);
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
        
        // 获取当前会话信息或创建新会话
        let sessionId = this.currentSessionId;
        let currentSession = this.sessions.find(s => s.id === sessionId);
        let isFirstMessage = false;
        
        // 如果没有选中会话，创建临时会话对象
        if (!sessionId || !currentSession) {
            sessionId = this.generateUUID();
            const currentTime = new Date().toISOString().replace('T', ' ').slice(0, 19);
            
            currentSession = {
                id: sessionId,
                title: '',
                created_at: currentTime,
                updated_at: currentTime,
                is_first: true
            };
            
            // 添加到会话列表最前面
            this.sessions.unshift(currentSession);
            this.currentSessionId = sessionId;
            isFirstMessage = true;
            
            // 更新UI显示
            document.getElementById('currentSessionTitle').textContent = '新会话';
            this.renderSessions();
        }
        
        // 清空输入框
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        // 添加用户消息到界面
        this.addMessageToChat('user', message);
        
        // 显示打字指示器
        this.showTypingIndicator();
        
        // 禁用发送按钮，显示停止按钮
        const sendButton = document.getElementById('sendBtn');
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        // 显示停止按钮
        const stopButton = document.getElementById('stopBtn');
        if (stopButton) {
            stopButton.style.display = 'inline-block';
        }
        
        // 禁用输入框
        messageInput.disabled = true;
        
        try {
            const useKnowledgeBase = document.getElementById('useKnowledgeBase').checked;
            const useWebSearch = document.getElementById('useWebSearch').checked;
            
            // 使用流式接口
            const response = await fetch('/api/v1/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId,
                    session_name: currentSession ? currentSession.title : '',
                    is_first: isFirstMessage,
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
            this.currentReader = reader; // 保存reader引用用于停止
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
                            
                            if (data.type === 'request_id') {
                                this.currentRequestId = data.request_id;
                            } else if (data.type === 'start') {
                                // 创建助手消息元素
                                assistantMessageElement = this.createAssistantMessageElement();
                            } else if (data.type === 'session_info') {
                                // 更新会话信息
                                this.currentSessionId = data.session_id;
                                
                                // 如果是首次消息，更新本地会话对象
                                if (isFirstMessage) {
                                    const localSession = this.sessions.find(s => s.id === data.session_id);
                                    if (localSession) {
                                        localSession.title = data.session_name || localSession.title;
                                        localSession.updated_at = data.updated_at || localSession.updated_at;
                                        localSession.is_first = false; // 移除首次标记
                                        document.getElementById('currentSessionTitle').textContent = localSession.title;
                                    }
                                } else {
                                    // 刷新会话列表但不重新加载消息
                                    await this.loadSessions();
                                    // 找到会话并更新标题
                                    const session = this.sessions.find(s => s.id === data.session_id);
                                    if (session) {
                                        document.getElementById('currentSessionTitle').textContent = session.title;
                                    }
                                }
                                
                                // 清空欢迎消息（如果存在）
                                const welcomeMessage = document.querySelector('.welcome-message');
                                if (welcomeMessage) {
                                    welcomeMessage.remove();
                                }
                            } else if (data.type === 'title') {
                                // 处理标题更新事件
                                console.log('收到title事件:', data);
                                this.updateSessionTitleWithAnimation(data.session_id, data.title);
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
                                // 清除当前会话的缓存，确保下次加载时获取最新消息
                                if (this.currentSessionId) {
                                    this.messageCache.delete(this.currentSessionId);
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
        } finally {
            this.currentReader = null; // 清除reader引用
            this.currentRequestId = null; // 清除request_id
            this.resetChatUI();
        }
    }
    
    resetChatUI() {
        // 恢复发送按钮状态
        const sendButton = document.getElementById('sendBtn');
        sendButton.disabled = false;
        sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        
        // 隐藏停止按钮
        const stopButton = document.getElementById('stopBtn');
        if (stopButton) {
            stopButton.style.display = 'none';
        }
        
        // 恢复输入框状态
        const messageInput = document.getElementById('messageInput');
        messageInput.disabled = false;
        messageInput.focus();
    }
    
    async stopGeneration() {
        if (this.currentRequestId) {
            try {
                await fetch('/api/v1/chat/stop', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ request_id: this.currentRequestId })
                });
                this.showToast('已发送停止请求');
            } catch (error) {
                console.error('停止请求失败:', error);
                this.showToast('停止请求失败', 'error');
            }
        }
        if (this.currentReader) {
            this.currentReader.cancel('用户手动停止');
        }
        this.resetChatUI();
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
    
    showNewKnowledgeBaseModal() {
        document.getElementById('newKnowledgeBaseModal').style.display = 'block';
        this.bindNewKnowledgeBaseEvents();
    }
    
    showTestKnowledgeModal() {
        document.getElementById('testKnowledgeModal').style.display = 'block';
        this.bindTestKnowledgeEvents();
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
        console.log("fileInput in uploadFiles:", fileInput);
        
        // 检查元素是否存在
        if (!fileInput) {
            this.showToast('文件输入元素未找到', 'error');
            return;
        }
        
        if (!this.currentKnowledgeBaseId) {
            this.showToast('请先选择知识库', 'error');
            return;
        }
        
        const files = fileInput.files;
        
        // 检查files是否存在
        if (!files || files.length === 0) {
            this.showToast('请选择要上传的文件', 'warning');
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
                formData.append('knowledge_base_id', this.currentKnowledgeBaseId);
                
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
            await this.loadDocuments(); // 重新加载文档列表
            await this.loadKnowledgeBases(); // 刷新知识库列表
            
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
    
    bindNewKnowledgeBaseEvents() {
        // 选项卡切换
        const tabBtns = document.querySelectorAll('#newKnowledgeBaseModal .tab-btn');
        const tabContents = document.querySelectorAll('#newKnowledgeBaseModal .tab-content');
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.dataset.tab;
                
                // 更新按钮状态
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // 更新内容显示
                tabContents.forEach(content => {
                    content.classList.remove('active');
                    if (content.id === tabName + 'Tab') {
                        content.classList.add('active');
                    }
                });
            });
        });
        
        // 文件上传区域
        const uploadArea = document.getElementById('newKbUploadArea');
        const fileInput = document.getElementById('newKbFileInput');
        
        if (uploadArea && fileInput) {
            uploadArea.addEventListener('click', () => fileInput.click());
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
                fileInput.files = e.dataTransfer.files;
            });
        }
        
        // 按钮事件
        document.getElementById('createKbBtn').addEventListener('click', () => this.createKnowledgeBase());
        document.getElementById('cancelNewKbBtn').addEventListener('click', () => this.hideNewKnowledgeBaseModal());
    }
    
    bindTestKnowledgeEvents() {
        // 相似度滑块
        const similaritySlider = document.getElementById('testSimilarity');
        const similarityValue = document.getElementById('testSimilarityValue');
        
        if (similaritySlider && similarityValue) {
            similaritySlider.addEventListener('input', () => {
                similarityValue.textContent = similaritySlider.value;
            });
        }
        
        // 按钮事件
        document.getElementById('runTestBtn').addEventListener('click', () => this.runKnowledgeTest());
        document.getElementById('cancelTestBtn').addEventListener('click', () => this.hideTestKnowledgeModal());
    }
    
    hideNewKnowledgeBaseModal() {
        document.getElementById('newKnowledgeBaseModal').style.display = 'none';
        
        // 重置表单
        document.getElementById('kbGroupName').value = '';
        const descriptionField = document.getElementById('kbDescription');
        if (descriptionField) {
            descriptionField.value = '';
        }
    }
    
    hideTestKnowledgeModal() {
        document.getElementById('testKnowledgeModal').style.display = 'none';
        
        // 重置表单
        document.getElementById('testKbSelect').value = '';
        document.getElementById('testQuery').value = '';
        document.getElementById('testTopK').value = '5';
        document.getElementById('testSimilarity').value = '0.7';
        document.getElementById('testSimilarityValue').textContent = '0.7';
        
        // 隐藏结果
        document.getElementById('testResults').style.display = 'none';
        document.getElementById('testResultsList').innerHTML = '';
    }
    
    async createKnowledgeBase() {
        const groupName = document.getElementById('kbGroupName').value.trim();
        const description = document.getElementById('kbDescription').value.trim();
        
        if (!groupName) {
            this.showToast('请输入知识库名称', 'error');
            return;
        }
        
        try {
            // 创建知识库分组（仅创建分组）
            const groupResponse = await fetch('/api/v1/kb/group/create_group', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    group_name: groupName,
                    description: description || '',
                    user_id: 'test_user'
                })
            });
            
            if (!groupResponse.ok) {
                throw new Error('创建知识库失败');
            }
            
            this.showToast('知识库创建成功', 'success');
            
            // 刷新知识库列表
            await this.loadKnowledgeBases();
            this.hideNewKnowledgeBaseModal();
            
        } catch (error) {
            console.error('创建知识库失败:', error);
            this.showToast('创建知识库失败: ' + error.message, 'error');
        }
    }
    
    async runKnowledgeTest() {
        const query = document.getElementById('testQuery').value.trim();
        const groupId = document.getElementById('testKbSelect').value;
        const topK = parseInt(document.getElementById('testTopK').value);
        const similarity = parseFloat(document.getElementById('testSimilarity').value);
        
        if (!query) {
            this.showToast('请输入查询内容', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/v1/kb/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    user_id: 'test_user',
                    group_id: groupId ? parseInt(groupId) : null,
                    top_k: topK,
                    similarity_threshold: similarity
                })
            });
            
            if (!response.ok) {
                throw new Error('检索失败');
            }
            
            const data = await response.json();
            this.displayTestResults(data.data || []);
            
        } catch (error) {
            console.error('知识库检索失败:', error);
            this.showToast('检索失败: ' + error.message, 'error');
        }
    }
    
    displayTestResults(results) {
        const resultsContainer = document.getElementById('testResults');
        const resultsList = document.getElementById('testResultsList');
        
        if (results.length === 0) {
            resultsList.innerHTML = '<div class="no-results">未找到相关内容</div>';
        } else {
            resultsList.innerHTML = results.map(result => `
                <div class="result-item">
                    <div class="result-header">
                        <div class="result-title">${result.title || '未命名'}</div>
                        <div class="result-score">${(result.score * 100).toFixed(1)}%</div>
                    </div>
                    <div class="result-content">${result.content.substring(0, 200)}${result.content.length > 200 ? '...' : ''}</div>
                    <div class="result-meta">
                        <span>来源: ${result.source_path || '未知'}</span>
                        <span class="result-group">分组ID: ${result.group_id || '未知'}</span>
                    </div>
                </div>
            `).join('');
        }
        
        resultsContainer.style.display = 'block';
    }
    
    async editKnowledgeBase(id, currentName) {
        const newName = prompt('请输入新的知识库名称:', currentName);
        if (!newName || newName === currentName) return;
        
        try {
            const response = await fetch(`/api/v1/kb/group/update_group?user_id=test_user`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    group_id: id,
                    group_name: newName
                })
            });
            
            if (!response.ok) {
                throw new Error('更新失败');
            }
            
            this.showToast('知识库更新成功', 'success');
            await this.loadKnowledgeBases();
            
        } catch (error) {
            console.error('更新知识库失败:', error);
            this.showToast('更新失败: ' + error.message, 'error');
        }
    }
    
    async deleteKnowledgeBase(id, name) {
        if (!confirm(`确定要删除知识库"${name}"吗？此操作不可恢复。`)) return;
        
        try {
            const response = await fetch(`/api/v1/kb/group/delete_group?user_id=test_user`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    group_id: id
                })
            });
            
            if (!response.ok) {
                throw new Error('删除失败');
            }
            
            this.showToast('知识库删除成功', 'success');
            await this.loadKnowledgeBases();
            
        } catch (error) {
            console.error('删除知识库失败:', error);
            this.showToast('删除失败: ' + error.message, 'error');
        }
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