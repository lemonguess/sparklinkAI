// SparkLink AI 前端应用
class SparkLinkApp {
    constructor() {
        this.currentSessionId = null;
        this.currentKnowledgeBaseId = null;
        this.sessions = [];
        this.knowledgeBases = [];
        this.documents = [];
        // 文档进度轮询
        this.docPollingTimer = null;
        this.docPollingInterval = 2000; // 2s 轮询
        this.messageCache = new Map(); // 缓存会话消息，避免重复加载

        this.settings = {
            maxTokens: 2000,
            temperature: 0.7,
            searchTopK: 5,
            similarityThreshold: 0.7,
            selectedKnowledgeBase: null
        };
        this.currentReader = null; // 用于停止流式输出
        this.currentRequestId = null; // 用于停止流式输出
        
        this.init();
    }
    
    updateThinkContent(messageElement, thinkContent) {
        const thinkContainer = messageElement.querySelector('.thinking-container');
        if (thinkContainer) {
            // 显示思考容器
            thinkContainer.style.display = 'block';

            // 确保折叠内容区域可见
            const contentEl = thinkContainer.querySelector('.collapsible-content');
            if (contentEl) {
                contentEl.style.display = 'block';
            }
            // 设置展开状态，配合 .collapsible.expanded 样式
            thinkContainer.classList.add('expanded');
            
            // 获取思考文本容器并追加内容
            const thinkingText = thinkContainer.querySelector('.thinking-text');
            if (thinkingText) {
                const currentContent = thinkingText.textContent || '';
                thinkingText.textContent = currentContent + thinkContent;
            }
        }
        this.scrollToBottom();
    }
    
    updateSourceContent(messageElement, sourceData) {
        if (!sourceData) return;

        let itemsHtml = '';
        const knowledge = sourceData.knowledge_sources || sourceData.knowledge_results || [];
        const web = sourceData.web_search_results || sourceData.web_results || [];

        if (Array.isArray(knowledge) && knowledge.length > 0) {
            itemsHtml += knowledge.map(item => {
                const title = item.title || item.content || '知识库';
                const rawUrl = item.source_path || item.url || '';
                const url = (typeof rawUrl === 'string') ? rawUrl.replace(/[\s`]/g, '') : '';
                return url
                    ? `<div class=\"source-item\"><i class=\"fas fa-database\"></i> <a href=\"${url}\" target=\"_blank\" rel=\"noopener noreferrer\">${title}</a></div>`
                    : `<div class=\"source-item\"><i class=\"fas fa-database\"></i> ${title}</div>`;
            }).join('');
        }

        if (Array.isArray(web) && web.length > 0) {
            itemsHtml += web.map(item => {
                const title = item.title || item.url || '网络搜索';
                const rawUrl = item.source_path || item.url || '';
                const url = (typeof rawUrl === 'string') ? rawUrl.replace(/[\s`]/g, '') : '';
                return url
                    ? `<div class=\"source-item\"><i class=\"fas fa-globe\"></i> <a href=\"${url}\" target=\"_blank\" rel=\"noopener noreferrer\">${title}</a></div>`
                    : `<div class=\"source-item\"><i class=\"fas fa-globe\"></i> ${title}</div>`;
            }).join('');
        }

        if (!itemsHtml && typeof sourceData === 'string') {
            itemsHtml = `<div class="source-item">${sourceData}</div>`;
        }

        let sourcesContainer = messageElement.querySelector('.sources-container');
        if (!sourcesContainer) {
            sourcesContainer = document.createElement('div');
            sourcesContainer.className = 'collapsible sources-container expanded';
            sourcesContainer.innerHTML = `
                <div class=\"collapsible-header\"><h4>信息来源</h4><span class=\"toggle-icon\">▼</span></div>
                <div class=\"collapsible-content\"></div>
            `;
            const messageContent = messageElement.querySelector('.message-content');
            const messageTime = messageElement.querySelector('.message-time');
            if (messageContent) {
                messageContent.insertBefore(sourcesContainer, messageTime || null);
            }
        }

        const contentEl = sourcesContainer.querySelector('.collapsible-content');
        if (contentEl && itemsHtml) {
            contentEl.insertAdjacentHTML('beforeend', itemsHtml);
            sourcesContainer.style.display = 'block';
            contentEl.style.display = 'block';
            sourcesContainer.classList.add('expanded');
        }

        this.scrollToBottom();
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

    // 折叠展开功能
    bindCollapsibleEvents() {
        document.querySelectorAll('.section-header.collapsible').forEach(header => {
            header.addEventListener('click', (e) => {
                // 避免点击按钮时触发折叠
                if (e.target.closest('.btn-icon') || e.target.closest('.header-actions')) {
                    return;
                }
                
                const targetId = header.dataset.target;
                const targetElement = document.getElementById(targetId);
                const collapseIcon = header.querySelector('.collapse-icon');
                
                if (targetElement && collapseIcon) {
                    // 切换折叠状态
                    header.classList.toggle('collapsed');
                    targetElement.classList.toggle('collapsed');
                    
                    // 保存折叠状态到localStorage
                    const isCollapsed = header.classList.contains('collapsed');
                    localStorage.setItem(`sidebar-${targetId}-collapsed`, isCollapsed);
                }
            });
        });
        
        // 恢复折叠状态
        this.restoreCollapsibleStates();
    }

    restoreCollapsibleStates() {
        document.querySelectorAll('.section-header.collapsible').forEach(header => {
            const targetId = header.dataset.target;
            const targetElement = document.getElementById(targetId);
            const collapseIcon = header.querySelector('.collapse-icon');
            
            if (targetElement && collapseIcon) {
                const isCollapsed = localStorage.getItem(`sidebar-${targetId}-collapsed`) === 'true';
                
                if (isCollapsed) {
                    header.classList.add('collapsed');
                    targetElement.classList.add('collapsed');
                }
            }
        });
    }

    // 确保指定区域展开
    ensureSectionExpanded(sectionId) {
        const header = document.querySelector(`[data-target="${sectionId}"]`);
        const targetElement = document.getElementById(sectionId);
        
        if (header && targetElement) {
            // 移除折叠状态
            header.classList.remove('collapsed');
            targetElement.classList.remove('collapsed');
            
            // 更新localStorage状态
            localStorage.setItem(`sidebar-${sectionId}-collapsed`, 'false');
        }
    }
    
    bindEvents() {
        // 发送消息 - 这些元素在新界面中已移除，需要检查是否存在
        const sendBtn = document.getElementById('sendBtn');
        const messageInput = document.getElementById('messageInput');
        const stopBtn = document.getElementById('stopBtn');
        const newSessionBtn = document.getElementById('newSessionBtn');
        const clearChatBtn = document.getElementById('clearChatBtn');
        
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        if (messageInput) {
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // 自动调整输入框高度
            messageInput.addEventListener('input', (e) => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            });
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopGeneration());
        }
        
        if (newSessionBtn) {
            newSessionBtn.addEventListener('click', () => this.createNewSession());
        }
        
        if (clearChatBtn) {
            clearChatBtn.addEventListener('click', () => this.clearChat());
        }
        
        // 搜索策略按钮事件
        this.bindStrategyButtons();
        
        // 上传文档
        const uploadDocBtn = document.getElementById('uploadDocBtn');
        if (uploadDocBtn) {
            uploadDocBtn.addEventListener('click', () => this.showUploadModal());
        }
        
        // 添加文本
        const addTextBtn = document.getElementById('addTextBtn');
        if (addTextBtn) {
            addTextBtn.addEventListener('click', () => this.showAddTextModal());
        }
        
        // 刷新文档
        const refreshDocsBtn = document.getElementById('refreshDocsBtn');
        if (refreshDocsBtn) {
            refreshDocsBtn.addEventListener('click', () => this.loadDocuments());
        }
        
        // 知识召回检测 - 修复检索按钮
        const runTestBtn = document.getElementById('runTestBtn');
        if (runTestBtn) {
            runTestBtn.addEventListener('click', () => this.performKnowledgeRecall());
        }
        
        // 清空召回结果 - 修复清空按钮
        const clearResultsBtn = document.getElementById('clearResultsBtn');
        if (clearResultsBtn) {
            clearResultsBtn.addEventListener('click', () => this.clearRecallResults());
        }
        
        // 相似度滑块实时更新 - 修复滑块
        const testSimilarity = document.getElementById('testSimilarity');
        if (testSimilarity) {
            testSimilarity.addEventListener('input', (e) => {
                const valueElement = document.querySelector('.similarity-value');
                if (valueElement) {
                    valueElement.textContent = parseFloat(e.target.value).toFixed(2);
                }
            });
        }

        // 回车直接触发知识召回 - 修复输入框
        const testQuery = document.getElementById('testQuery');
        if (testQuery) {
            testQuery.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.performKnowledgeRecall();
                }
            });
        }
        
        // 新建知识库
        const newKnowledgeBaseBtn = document.getElementById('newKnowledgeBaseBtn');
        if (newKnowledgeBaseBtn) {
            newKnowledgeBaseBtn.addEventListener('click', () => this.showNewKnowledgeBaseModal());
        }
        
        // 设置
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.showSettingsModal());
        }
        
        // 模态框事件
        this.bindModalEvents();
        
        // 文件上传事件
        this.bindFileUploadEvents();
        
        // 折叠展开功能
        this.bindCollapsibleEvents();

        // 聊天消息区域折叠事件委托（与 chat.js 保持一致）
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            messagesContainer.addEventListener('click', (e) => {
                const headerEl = e.target.closest('.collapsible-header');
                if (headerEl) {
                    const container = headerEl.parentElement;
                    const contentEl = container.querySelector('.collapsible-content');
                    const isExpanded = container.classList.toggle('expanded');
                    if (contentEl) {
                        contentEl.style.display = isExpanded ? 'block' : 'none';
                    }
                    headerEl.classList.toggle('expanded', isExpanded);
                    e.stopPropagation();
                    return;
                }
            });
        }
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
        
        // 文本上传模态框按钮
        document.getElementById('cancelTextBtn').addEventListener('click', () => {
            document.getElementById('addTextModal').style.display = 'none';
        });
        
        document.getElementById('confirmTextBtn').addEventListener('click', () => this.uploadText());
        
        // 设置按钮事件
        document.getElementById('saveSettingsBtn').addEventListener('click', () => this.saveSettings());
        document.getElementById('resetSettingsBtn').addEventListener('click', () => this.resetSettings());
        
        // 知识库刷新按钮事件
        document.getElementById('refreshKbListBtn').addEventListener('click', () => this.loadKnowledgeBasesForSettings());
        
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
            const response = await fetch('/api/v1/kb/group/get_groups', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
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
                        <button class="btn-icon" onclick="app.editKnowledgeBase('${kb.id}', '${kb.group_name}')" title="编辑">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-icon" onclick="app.deleteKnowledgeBase('${kb.id}', '${kb.group_name}')" title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        // 添加点击事件选择知识库
        knowledgeList.querySelectorAll('.knowledge-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.knowledge-item-actions')) {
                    const kbId = item.dataset.id; // 保持为字符串，避免被转成数字
                    this.selectKnowledgeBase(kbId);
                }
            });
        });
    }
    
    // 选择知识库
    async selectKnowledgeBase(kbId) {
        this.currentKnowledgeBaseId = kbId;
        
        // 切换到知识库管理界面
        this.showKnowledgeContainer();
        
        // 更新知识库列表显示
        this.renderKnowledgeBases();
        
        // 更新文档面板标题
        const selectedKb = this.knowledgeBases.find(kb => kb.id === kbId);
        const kbTitle = document.getElementById('selectedKbName');
        if (kbTitle && selectedKb) {
            kbTitle.textContent = selectedKb.group_name;
        }
        
        // 隐藏欢迎面板
        const welcomePanel = document.getElementById('welcomePanel');
        if (welcomePanel) {
            welcomePanel.style.display = 'none';
        }
        
        // 显示文档面板（包含知识召回检测区域）
        const documentPanel = document.getElementById('documentPanel');
        if (documentPanel) {
            documentPanel.style.display = 'block';
        }
        
        // 显示知识召回检测面板
        const testPanel = document.querySelector('.knowledge-test-panel');
        if (testPanel) {
            testPanel.style.display = 'flex';
        }
        
        // 加载该知识库的文档
        await this.loadDocuments();
    }
    
    // 更新单个文档的状态和进度
    async updateDocumentStatus(taskId) {
        try {
            const response = await fetch('/api/v1/kb/group/detail', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    group_id: String(this.currentKnowledgeBaseId)
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    const updatedDocuments = result.data.documents || [];
                    const updatedDoc = updatedDocuments.find(d => d.task_id === taskId);
                    
                    if (updatedDoc) {
                        // 更新本地文档数据
                        const docIndex = this.documents.findIndex(d => d.task_id === taskId);
                        if (docIndex !== -1) {
                            this.documents[docIndex] = updatedDoc;
                        }
                        
                        // 只更新这个特定文档的DOM元素
                        this.updateSingleDocumentElement(updatedDoc);
                        
                        return updatedDoc;
                    }
                }
            }
        } catch (error) {
            console.error('Error updating document status:', error);
        }
        return null;
    }
    
    // 更新单个文档元素的DOM
    updateSingleDocumentElement(doc) {
        const documentElement = document.querySelector(`[data-id="${doc.task_id}"]`);
        if (!documentElement) return;
        
        // 更新状态文本
        const statusSpan = documentElement.querySelector('.document-meta span:first-child');
        if (statusSpan) {
            statusSpan.textContent = `状态: ${this.getStatusText(doc.status)}`;
        }
        
        // 更新进度条
        const progressFill = documentElement.querySelector('.progress-fill');
        if (progressFill) {
            progressFill.style.width = `${doc.progress || 0}%`;
        }
        
        // 更新进度文本
        const progressText = documentElement.querySelector('.progress-text');
        if (progressText) {
            progressText.textContent = `${doc.progress || 0}%`;
        }
        
        // 更新错误信息
        const existingError = documentElement.querySelector('.document-error');
        if (existingError) {
            existingError.remove();
        }
        
        if (doc.error_message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'document-error';
            errorDiv.textContent = `错误: ${doc.error_message}`;
            documentElement.querySelector('.document-info').appendChild(errorDiv);
        }
    }
    
    // 优化的轮询机制，只更新进行中的文档
    async pollInProgressDocuments() {
        const inProgressDocs = this.documents.filter(d => ['pending', 'processing'].includes(d.status));
        
        if (inProgressDocs.length === 0) {
            // 没有进行中的文档，停止轮询
            if (this.docPollingTimer) {
                clearInterval(this.docPollingTimer);
                this.docPollingTimer = null;
            }
            return;
        }
        
        // 并发更新所有进行中的文档
        const updatePromises = inProgressDocs.map(doc => this.updateDocumentStatus(doc.task_id));
        await Promise.all(updatePromises);
        
        // 检查是否还有进行中的文档
        const stillInProgress = this.documents.some(d => ['pending', 'processing'].includes(d.status));
        if (!stillInProgress && this.docPollingTimer) {
            clearInterval(this.docPollingTimer);
            this.docPollingTimer = null;
        }
    }

    // 加载文档列表
    async loadDocuments() {
        if (!this.currentKnowledgeBaseId) {
            return;
        }
        
        // 加载态与按钮禁用
        const documentList = document.getElementById('documentList');
        const refreshBtn = document.getElementById('refreshDocsBtn');
        if (documentList) {
            documentList.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> 正在加载文档...</div>';
        }
        if (refreshBtn) refreshBtn.disabled = true;
        
        try {
            // 使用POST请求和JSON请求体
            const response = await fetch('/api/v1/kb/group/detail', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    group_id: String(this.currentKnowledgeBaseId) // 确保为字符串
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.documents = result.data.documents || [];
                    // 更新标题显示文档数量
                    const kbTitle = document.getElementById('selectedKbName');
                    const selectedKb = this.knowledgeBases.find(kb => kb.id === String(this.currentKnowledgeBaseId));
                    if (kbTitle && selectedKb) {
                        kbTitle.textContent = `${selectedKb.group_name}（${this.documents.length} 个文档）`;
                    }
                    this.renderDocuments();
                    // 根据文档状态决定是否轮询
                    const hasInProgress = this.documents.some(d => ['pending','processing'].includes(d.status));
                    if (hasInProgress) {
                        if (!this.docPollingTimer) {
                            this.docPollingTimer = setInterval(() => {
                                if (!this.currentKnowledgeBaseId) return;
                                this.pollInProgressDocuments(); // 使用优化的轮询方法
                            }, this.docPollingInterval);
                        }
                    } else if (this.docPollingTimer) {
                        clearInterval(this.docPollingTimer);
                        this.docPollingTimer = null;
                    }

                } else {
                    console.error('Failed to load documents:', result.message);
                    this.showToast(result.message || '加载文档失败', 'error');
                    if (documentList) {
                        documentList.innerHTML = '<div class="empty-state">加载文档失败，请稍后重试</div>';
                    }
                }
            } else {
                console.error('Failed to load documents');
                this.showToast('加载文档失败', 'error');
                if (documentList) {
                    documentList.innerHTML = '<div class="empty-state">加载文档失败，请检查网络</div>';
                }
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            this.showToast('加载文档失败', 'error');
            if (documentList) {
                documentList.innerHTML = '<div class="empty-state">加载异常，请稍后重试</div>';
            }
        } finally {
            if (refreshBtn) refreshBtn.disabled = false;
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
            <div class="document-item" data-id="${doc.task_id}">
                <div class="document-info">
                    <div class="document-name">${doc.doc_name || '未命名文档'}</div>
                    <div class="document-meta">
                        <span>状态: ${this.getStatusText(doc.status)}</span>
                        <span>类型: ${doc.doc_type || '未知'}</span>
                        <span>进度: ${doc.progress || 0}%</span>
                        <span>创建时间: ${this.formatTime(doc.created_at)}</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${(doc.progress || 0)}%"></div>
                    </div>
                    <div class="progress-text">${doc.progress || 0}%</div>
                    ${doc.error_message ? `<div class="document-error">错误: ${doc.error_message}</div>` : ''}
                </div>
                <div class="document-card-actions">
                    <button class="btn-icon" onclick="app.deleteDocument('${doc.doc_id}', '${doc.doc_name}')" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    // 获取状态文本
    getStatusText(status) {
        const statusMap = {
            'pending': '待处理',
            'processing': '处理中',
            'completed': '已完成',
            'failed': '失败'
        };
        return statusMap[status] || status;
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
        const confirmed = await Utils.Modal.confirm(`确定要删除文档 "${docName}" 吗？`, '删除文档');
        if (!confirmed) return;
        
        try {
            const response = await fetch(`/api/v1/kb/document/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    doc_id: docId
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showToast('文档删除成功', 'success');
                    await this.loadDocuments(); // 重新加载文档列表
                } else {
                    this.showToast(result.message || '文档删除失败', 'error');
                }
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
        
        if (kbSelect) {
            kbSelect.innerHTML = '<option value="">选择知识库</option>' + 
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
        try {
            // 调用API创建新会话
            const response = await fetch('/api/v1/chat/create_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: 'admin123456789abcdef0123456789ab', // 使用默认用户ID
                    title: '新会话'
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    // 创建成功，设置当前会话ID
                    this.currentSessionId = result.data.id;
                    
                    // 确保会话区域展开
                    this.ensureSectionExpanded('sessionsList');
                    
                    // 重新加载会话列表
                    await this.loadSessions();
                    
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
                    const sessionTitleElement = document.getElementById('currentSessionTitle');
                    if (sessionTitleElement) {
                        sessionTitleElement.textContent = result.data.title;
                    }
                    
                    // 聚焦到输入框
                    const messageInput = document.getElementById('messageInput');
                    if (messageInput) {
                        messageInput.focus();
                    }
                    
                    this.showToast('新会话创建成功', 'success');
                } else {
                    this.showToast(result.message || '创建会话失败', 'error');
                }
            } else {
                const error = await response.json();
                this.showToast(error.detail || '创建会话失败', 'error');
            }
        } catch (error) {
            console.error('创建新会话失败:', error);
            this.showToast('创建会话失败', 'error');
        }
    }
    
    async selectSession(sessionId) {
        this.currentSessionId = sessionId;
        this.renderSessions();
        
        const session = this.sessions.find(s => s.id === sessionId);
        if (session) {
            const titleElement = document.getElementById('currentSessionTitle');
            if (titleElement) {
                titleElement.innerHTML = `<i class="fas fa-comments"></i> ${session.title}`;
            }
        }

        // 切换到聊天界面
        this.showChatContainer();
        
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

    // 安全的DOM元素更新方法
    safeUpdateElement(elementId, content, retryCount = 0) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = content;
            console.log(`成功更新元素 ${elementId}:`, content);
            return true;
        } else if (retryCount < 3) {
            console.warn(`元素 ${elementId} 未找到，${100}ms后重试 (${retryCount + 1}/3)`);
            setTimeout(() => {
                this.safeUpdateElement(elementId, content, retryCount + 1);
            }, 100);
        } else {
            console.error(`无法找到元素 ${elementId}，已重试3次`);
            return false;
        }
    }

    updateSessionTitleWithAnimation(sessionId, newTitle) {
        console.log('执行updateSessionTitleWithAnimation:', sessionId, newTitle);
        console.log('当前会话ID:', this.currentSessionId);
        
        // 更新本地会话数据
        const session = this.sessions.find(s => s.id === sessionId);
        if (session) {
            console.log('找到会话:', session);
            session.title = newTitle;
            
            // 如果是当前会话，更新当前会话标题显示
            if (sessionId === this.currentSessionId) {
                console.log('正在更新当前会话标题');
                
                // 使用安全的DOM更新方法，包含重试机制
                const updateWithAnimation = () => {
                    const currentTitleElement = document.getElementById('currentSessionTitle');
                    if (currentTitleElement) {
                        console.log('开始更新标题动画');
                        // 添加渐变动画效果
                        currentTitleElement.style.transition = 'opacity 0.3s ease';
                        currentTitleElement.style.opacity = '0.5';
                        
                        setTimeout(() => {
                            console.log('设置新标题:', newTitle);
                            currentTitleElement.textContent = newTitle;
                            currentTitleElement.style.opacity = '1';
                        }, 150);
                        return true;
                    }
                    return false;
                };
                
                // 如果第一次尝试失败，使用重试机制
                if (!updateWithAnimation()) {
                    console.warn('首次更新失败，使用重试机制');
                    setTimeout(() => {
                        if (!updateWithAnimation()) {
                            console.error('重试后仍无法更新标题');
                            // 降级方案：直接使用safeUpdateElement
                            this.safeUpdateElement('currentSessionTitle', newTitle);
                        }
                    }, 100);
                }
            } else {
                console.log('不是当前会话，跳过标题更新');
            }
            
            // 更新会话列表中的标题，带动画效果
            const titleElement = document.querySelector(`.session-title[data-session-id="${sessionId}"]`);
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
        const confirmed = await Utils.Modal.confirm(`确定要删除会话"${sessionTitle}"吗？\n\n注意：此操作将永久删除会话及其所有消息，无法恢复。`, '删除会话');
        if (!confirmed) return;
        
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
            this.addMessageToChat(message.role, message.content, message.created_at, message.sources, message.thinking_process);
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
                title: '新会话',
                created_at: currentTime,
                updated_at: currentTime,
                is_first: true
            };
            
            // 添加到会话列表最前面
            this.sessions.unshift(currentSession);
            this.currentSessionId = sessionId;
            isFirstMessage = true;
            
            // 更新UI显示
            console.log('准备更新UI显示，设置标题为: 新会话');
            
            // 使用安全的DOM更新方法
            this.safeUpdateElement('currentSessionTitle', '新会话');
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
            // 获取当前选中的搜索策略
            const activeBtn = document.querySelector('.strategy-btn.active');
            let searchStrategy = "auto"; // 默认值
            
            if (activeBtn) {
                searchStrategy = activeBtn.dataset.strategy;
            } else {
                // 如果没有按钮被选中，检查是否有多个按钮被选中（hybrid模式）
                const selectedBtns = document.querySelectorAll('.strategy-btn.selected');
                if (selectedBtns.length === 2) {
                    // 检查是否同时选中了知识库和联网
                    const hasKnowledge = Array.from(selectedBtns).some(btn => btn.dataset.strategy === 'knowledge_only');
                    const hasWeb = Array.from(selectedBtns).some(btn => btn.dataset.strategy === 'web_only');
                    if (hasKnowledge && hasWeb) {
                        searchStrategy = "hybrid";
                    }
                } else if (selectedBtns.length === 1) {
                    searchStrategy = selectedBtns[0].dataset.strategy;
                } else {
                    searchStrategy = "none";
                }
            }
            
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
                    search_strategy: searchStrategy,
                    max_tokens: this.settings.maxTokens,
                    temperature: this.settings.temperature,
                    search_top_k: this.settings.searchTopK,
                    similarity_threshold: this.settings.similarityThreshold,
                    group_id: this.settings.selectedKnowledgeBase
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
                                // 如果还没有创建助手消息元素，现在创建
                                if (!assistantMessageElement) {
                                    assistantMessageElement = this.createAssistantMessageElement();
                                }
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
                            } else if (data.type === 'title_update') {
                                // 处理异步标题更新事件
                                console.log('收到title_update事件:', data);
                                this.updateSessionTitleWithAnimation(data.session_id, data.title);
                            } else if (data.type === 'content') {
                                // 追加内容
                                fullResponse += data.content;
                                if (assistantMessageElement) {
                                    this.updateMessageContent(assistantMessageElement, fullResponse);
                                }
                            } else if (data.type === 'think') {
                                // 处理思考内容
                                if (assistantMessageElement) {
                                    this.updateThinkContent(assistantMessageElement, data.content);
                                }
                            } else if (data.type === 'source') {
                                // 处理来源信息
                                if (assistantMessageElement && data.content) {
                                    this.updateSourceContent(assistantMessageElement, data.content);
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
    
    addMessageToChat(role, content, timestamp = null, sources = null, thinkingProcess = null) {
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
        
        // 构建思考过程HTML（统一折叠容器）
        let thinkingHtml = '';
        if (thinkingProcess && role === 'assistant') {
            thinkingHtml = `
                <div class="collapsible thinking-container expanded">
                    <div class="collapsible-header"><h4>思考过程</h4><span class="toggle-icon">▼</span></div>
                    <div class="collapsible-content">
                        <div class="thinking-text">${this.formatMessageContent(thinkingProcess)}</div>
                    </div>
                </div>
            `;
        }
        
        // 构建来源信息HTML（统一折叠容器）
        let sourcesHtml = '';
        if (sources && (sources.knowledge_sources?.length > 0 || sources.web_search_results?.length > 0)) {
            let items = '';
            if (sources.knowledge_sources?.length > 0) {
                items += (sources.knowledge_sources || []).map(source => {
                    const title = source.title || '知识库';
                    const rawUrl = source.source_path || source.url || '';
                    const url = (typeof rawUrl === 'string') ? rawUrl.replace(/[\s`]/g, '') : '';
                    return url
                        ? `<div class=\"source-item\"><i class=\"fas fa-database\"></i> <a href=\"${url}\" target=\"_blank\" rel=\"noopener noreferrer\">${title}</a></div>`
                        : `<div class=\"source-item\"><i class=\"fas fa-database\"></i> ${title}</div>`;
                }).join('');
            }
            if (sources.web_search_results?.length > 0) {
                items += (sources.web_search_results || []).map(source => {
                    const title = source.title || '网络搜索';
                    const rawUrl = source.source_path || source.url || '';
                    const url = (typeof rawUrl === 'string') ? rawUrl.replace(/[\s`]/g, '') : '';
                    return url
                        ? `<div class=\"source-item\"><i class=\"fas fa-globe\"></i> <a href=\"${url}\" target=\"_blank\" rel=\"noopener noreferrer\">${title}</a></div>`
                        : `<div class=\"source-item\"><i class=\"fas fa-globe\"></i> ${title}</div>`;
                }).join('');
            }
            if (items) {
                sourcesHtml = `
                    <div class=\"collapsible sources-container expanded\">
                        <div class=\"collapsible-header\"><h4>信息来源</h4><span class=\"toggle-icon\">▼</span></div>
                        <div class=\"collapsible-content\">${items}</div>
                    </div>
                `;
            }
        }
        
        messageElement.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                ${thinkingHtml}
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
                <div class="collapsible thinking-container expanded">
                    <div class="collapsible-header"><h4>思考过程</h4><span class="toggle-icon">▼</span></div>
                    <div class="collapsible-content">
                        <div class="thinking-text"></div>
                    </div>
                </div>
                <div class="message-text"></div>
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
        if (!sources || (!sources.knowledge_sources?.length && !sources.web_search_results?.length)) {
            return;
        }

        let items = '';
        if (sources.knowledge_sources?.length > 0) {
            items += (sources.knowledge_sources || []).map(source => {
                const title = source.title || '知识库';
                const rawUrl = source.source_path || source.url || '';
                const url = (typeof rawUrl === 'string') ? rawUrl.replace(/[\s`]/g, '') : '';
                return url
                    ? `<div class=\"source-item\"><i class=\"fas fa-database\"></i> <a href=\"${url}\" target=\"_blank\" rel=\"noopener noreferrer\">${title}</a></div>`
                    : `<div class=\"source-item\"><i class=\"fas fa-database\"></i> ${title}</div>`;
            }).join('');
        }
        if (sources.web_search_results?.length > 0) {
            items += (sources.web_search_results || []).map(source => {
                const title = source.title || '网络搜索';
                const rawUrl = source.source_path || source.url || '';
                const url = (typeof rawUrl === 'string') ? rawUrl.replace(/[\s`]/g, '') : '';
                return url
                    ? `<div class=\"source-item\"><i class=\"fas fa-globe\"></i> <a href=\"${url}\" target=\"_blank\" rel=\"noopener noreferrer\">${title}</a></div>`
                    : `<div class=\"source-item\"><i class=\"fas fa-globe\"></i> ${title}</div>`;
            }).join('');
        }

        if (!items) return;

        // 创建或查找来源容器并插入
        let sourcesContainer = messageElement.querySelector('.sources-container');
        if (!sourcesContainer) {
            sourcesContainer = document.createElement('div');
            sourcesContainer.className = 'collapsible sources-container expanded';
            sourcesContainer.innerHTML = `
                <div class=\"collapsible-header\"><h4>🔍 信息来源</h4><span class=\"toggle-icon\">▼</span></div>
                <div class=\"collapsible-content\"></div>
            `;
            const messageContent = messageElement.querySelector('.message-content');
            const messageTime = messageElement.querySelector('.message-time');
            if (messageContent) {
                messageContent.insertBefore(sourcesContainer, messageTime || null);
            }
        }

        const contentEl = sourcesContainer.querySelector('.collapsible-content');
        if (contentEl) {
            contentEl.insertAdjacentHTML('beforeend', items);
            sourcesContainer.style.display = 'block';
            contentEl.style.display = 'block';
            sourcesContainer.classList.add('expanded');
        }
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
    
    async clearChat() {
        if (!this.currentSessionId) return;
        
        const confirmed = await Utils.Modal.confirm('确定要清空当前会话的所有消息吗？', '清空会话');
        if (confirmed) {
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
        // 打开时预选当前知识库
        const kbSelect = document.getElementById('kbSelect');
        if (kbSelect && this.currentKnowledgeBaseId) {
            kbSelect.value = String(this.currentKnowledgeBaseId);
        }
        // 初始禁用上传按钮，直到选择文件
        const confirmUploadBtn = document.getElementById('confirmUploadBtn');
        if (confirmUploadBtn) confirmUploadBtn.disabled = true;
    }
    
    showAddTextModal() {
        // 清空表单
        document.getElementById('textTitle').value = '';
        document.getElementById('textContent').value = '';
        document.getElementById('textSourceUrl').value = '';
        
        // 检查是否有选中的知识库
        if (!this.currentKnowledgeBaseId) {
            this.showToast('请先选择一个知识库', 'warning');
            return;
        }
        
        document.getElementById('addTextModal').style.display = 'block';
    }

    async uploadText() {
        const title = document.getElementById('textTitle').value.trim();
        const content = document.getElementById('textContent').value.trim();
        const sourceUrl = document.getElementById('textSourceUrl').value.trim();
        const kbId = this.currentKnowledgeBaseId;
        
        if (!title) {
            this.showToast('请输入标题', 'warning');
            return;
        }
        
        if (!content) {
            this.showToast('请输入内容', 'warning');
            return;
        }
        
        if (!kbId) {
            this.showToast('请先选择一个知识库', 'warning');
            return;
        }
        
        try {
            const requestBody = {
                title: title,
                content: content,
                group_id: kbId
            };
            
            // 只有当source_url不为空时才添加到请求中
            if (sourceUrl) {
                requestBody.source_url = sourceUrl;
            }
            
            const response = await fetch('/api/v1/kb/tasks/post_process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showToast('文本添加成功', 'success');
                    document.getElementById('addTextModal').style.display = 'none';
                    
                    // 确保知识库区域展开
                    this.ensureSectionExpanded('knowledgeBasesList');
                    
                    // 如果当前选中的知识库就是上传的知识库，刷新文档列表
                    if (kbId === this.currentKnowledgeBaseId) {
                        await this.loadDocuments();
                    }
                } else {
                    this.showToast(result.message || '文本添加失败', 'error');
                }
            } else {
                const error = await response.json();
                this.showToast(error.detail || '文本添加失败', 'error');
            }
        } catch (error) {
            console.error('Error uploading text:', error);
            this.showToast('文本添加失败', 'error');
        }
    }

    async performKnowledgeRecall() {
        const query = document.getElementById('testQuery').value.trim();
        const topK = parseInt(document.getElementById('testTopK').value);
        const similarity = parseFloat(document.getElementById('testSimilarity').value);
        
        if (!query) {
            this.showToast('请输入查询内容', 'warning');
            return;
        }
        
        if (!this.currentKnowledgeBaseId) {
            this.showToast('请先选择知识库', 'warning');
            return;
        }

        // UI: 设置加载态与禁用相关控件
        const runTestBtnEl = document.getElementById('runTestBtn');
        const testQueryEl = document.getElementById('testQuery');
        const testTopKEl = document.getElementById('testTopK');
        const testSimilarityEl = document.getElementById('testSimilarity');
        const testResults = document.getElementById('testResults');
        const prevBtnHtml = runTestBtnEl ? runTestBtnEl.innerHTML : '';
        if (runTestBtnEl) {
            runTestBtnEl.disabled = true;
            runTestBtnEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 检索中';
        }
        if (testQueryEl) testQueryEl.disabled = true;
        if (testTopKEl) testTopKEl.disabled = true;
        if (testSimilarityEl) testSimilarityEl.disabled = true;
        if (testResults) {
            testResults.innerHTML = `
                <div class="loading">
                    <i class="fas fa-spinner fa-spin"></i> 正在检索，请稍候...
                </div>
            `;
        }
        
        try {
            const response = await fetch('/api/v1/kb/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    group_id: this.currentKnowledgeBaseId,
                    top_k: topK,
                    similarity_threshold: similarity
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    // API返回的数据结构是 {data: {results: [...], total: n}}
                    this.displayRecallResults(result.data.results || []);
                } else {
                    this.showToast(result.message || '检索失败', 'error');
                }
            } else {
                const error = await response.json();
                this.showToast(error.detail || '检索失败', 'error');
            }
        } catch (error) {
            console.error('Error performing knowledge recall:', error);
            this.showToast('检索失败', 'error');
            // 确保在错误情况下也清除加载状态
            const testResults = document.getElementById('testResults');
            if (testResults) {
                testResults.innerHTML = `
                    <div class="welcome-message">
                        <div class="welcome-icon">
                            <i class="fas fa-exclamation-triangle"></i>
                        </div>
                        <h3>检索失败</h3>
                        <p>请检查网络连接或稍后重试。</p>
                    </div>
                `;
            }
        } finally {
            if (runTestBtnEl) {
                runTestBtnEl.disabled = false;
                runTestBtnEl.innerHTML = prevBtnHtml || '检索';
            }
            if (testQueryEl) testQueryEl.disabled = false;
            if (testTopKEl) testTopKEl.disabled = false;
            if (testSimilarityEl) testSimilarityEl.disabled = false;
        }
    }

    displayRecallResults(results) {
        const testResults = document.getElementById('testResults');
        
        if (!results || results.length === 0) {
            testResults.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon">
                        <i class="fas fa-search"></i>
                    </div>
                    <h3>未检索到相关内容</h3>
                    <p>请尝试调整查询内容或降低相似度阈值。</p>
                </div>
            `;
            return;
        }
        
        testResults.innerHTML = results.map((result, index) => `
            <div class="result-item">
                <div class="result-header">
                    <div class="result-title">${result.title || '未命名文档'}</div>
                    <div class="result-score">${(result.score * 100).toFixed(1)}%</div>
                </div>
                <div class="result-content">${result.content}</div>
                <div class="result-meta">
                    <span><i class="fas fa-file"></i> ${result.title || '未知文档'}</span>
                    <span><i class="fas fa-clock"></i> ${this.formatTime(result.create_at)}</span>
                    <span><i class="fas fa-tag"></i> 片段 ${index + 1}</span>
                </div>
            </div>
        `).join('');
    }

    clearRecallResults() {
        const testResults = document.getElementById('testResults');
        testResults.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <i class="fas fa-search"></i>
                </div>
                <h3>知识召回检测</h3>
                <p>输入查询内容，检测知识库中相关的文档片段。</p>
            </div>
        `;
        
        // 清空查询输入框
        document.getElementById('recallQuery').value = '';
    }

    showNewKnowledgeBaseModal() {
        document.getElementById('newKnowledgeBaseModal').style.display = 'block';
        this.bindNewKnowledgeBaseEvents();
    }
    
    
    showSettingsModal() {
        // 加载知识库列表到设置模态框
        this.loadKnowledgeBasesForSettings();
        
        // 加载当前设置到表单
        document.getElementById('maxTokens').value = this.settings.maxTokens;
        document.getElementById('temperature').value = this.settings.temperature;
        document.getElementById('temperatureValue').textContent = this.settings.temperature;
        document.getElementById('searchTopK').value = this.settings.searchTopK;
        document.getElementById('similarityThreshold').value = this.settings.similarityThreshold;
        document.getElementById('similarityValue').textContent = this.settings.similarityThreshold;
        
        // 设置知识库选择
        const kbSelect = document.getElementById('knowledgeBaseSelect');
        if (kbSelect && this.settings.selectedKnowledgeBase) {
            kbSelect.value = this.settings.selectedKnowledgeBase;
        }
        
        document.getElementById('settingsModal').style.display = 'block';
    }

    // 加载知识库列表到设置模态框
    async loadKnowledgeBasesForSettings() {
        try {
            const response = await fetch('/api/v1/kb/group/get_groups', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: null // 使用默认用户ID
                })
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    const kbSelect = document.getElementById('knowledgeBaseSelect');
                    if (kbSelect) {
                        // 清空现有选项
                        kbSelect.innerHTML = '<option value="">请选择知识库</option>';
                        
                        // 添加知识库选项
                        result.data.forEach(kb => {
                            const option = document.createElement('option');
                            option.value = kb.id;
                            option.textContent = kb.group_name;
                            kbSelect.appendChild(option);
                        });
                        
                        // 设置当前选中的知识库
                        if (this.settings.selectedKnowledgeBase) {
                            kbSelect.value = this.settings.selectedKnowledgeBase;
                        }
                    }
                }
            }
        } catch (error) {
            console.error('加载知识库列表失败:', error);
            const kbSelect = document.getElementById('knowledgeBaseSelect');
            if (kbSelect) {
                kbSelect.innerHTML = '<option value="">加载失败</option>';
            }
        }
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

            // 根据是否选择文件，控制上传按钮可用性
            const confirmUploadBtn = document.getElementById('confirmUploadBtn');
            if (confirmUploadBtn) {
                confirmUploadBtn.disabled = !(fileInput && fileInput.files && fileInput.files.length > 0);
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
                // 传给后端的字段名与后端一致
                formData.append('group_id', this.currentKnowledgeBaseId);
                
                const response = await fetch('/api/v1/kb/tasks/file_process', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `上传文件 ${file.name} 失败`);
                }
                // 读取返回的 task_id 并插入占位文档
                const result = await response.json();
                if (result && result.success && result.data && result.data.task_id) {
                    const placeholder = {
                        task_id: result.data.task_id,
                        doc_name: file.name,
                        status: 'pending',
                        progress: 0,
                        doc_type: (file.name.split('.').pop() || '').toUpperCase(),
                        created_at: Date.now() / 1000
                    };
                    this.documents.unshift(placeholder);
                    this.renderDocuments();
                    // 确保开启轮询
                    if (!this.docPollingTimer) {
                        this.docPollingTimer = setInterval(() => {
                            if (!this.currentKnowledgeBaseId) return;
                            this.loadDocuments();
                        }, this.docPollingInterval);
                    }
                }
                
                // 更新进度
                const progress = ((i + 1) / fileArray.length) * 100;
                this.updateUploadProgress(progress, `正在上传 ${file.name}...`);
            }
            
            this.showToast('文件上传成功', 'success');
            
            // 确保知识库区域展开
            this.ensureSectionExpanded('knowledgeBasesList');
            
            // 上传成功后刷新当前知识库文档
            await this.loadDocuments();
            this.hideUploadModal();
        } catch (error) {
            console.error('Error uploading files:', error);
            this.showToast(error.message || '文件上传失败', 'error');
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
        // 重置上传按钮为禁用，避免误点
        const confirmUploadBtn = document.getElementById('confirmUploadBtn');
        if (confirmUploadBtn) confirmUploadBtn.disabled = true;
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
    
    
    hideNewKnowledgeBaseModal() {
        document.getElementById('newKnowledgeBaseModal').style.display = 'none';
        
        // 重置表单
        document.getElementById('kbGroupName').value = '';
        const descriptionField = document.getElementById('kbDescription');
        if (descriptionField) {
            descriptionField.value = '';
        }
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
                })
            });
            
            if (!groupResponse.ok) {
                throw new Error('创建知识库失败');
            }
            
            this.showToast('知识库创建成功', 'success');
            
            // 确保知识库区域展开
            this.ensureSectionExpanded('knowledgeBasesList');
            
            // 刷新知识库列表
            await this.loadKnowledgeBases();
            this.hideNewKnowledgeBaseModal();
            
        } catch (error) {
            console.error('创建知识库失败:', error);
            this.showToast('创建知识库失败: ' + error.message, 'error');
        }
    }
    
    
    async editKnowledgeBase(id, currentName) {
        const newName = prompt('请输入新的知识库名称:', currentName);
        if (!newName || newName === currentName) return;
        
        try {
            const response = await fetch(`/api/v1/kb/group/update_group`, {
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
        const confirmed = await Utils.Modal.confirm(`确定要删除知识库"${name}"吗？此操作不可恢复。`, '删除知识库');
        if (!confirmed) return;
        
        try {
            const response = await fetch(`/api/v1/kb/group/delete_group`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    group_id: id
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showToast('知识库删除成功', 'success');
                await this.loadKnowledgeBases();
            } else {
                this.showToast(result.message || '删除失败', 'error');
            }
            
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
        
        // 保存知识库选择
        const kbSelect = document.getElementById('knowledgeBaseSelect');
        if (kbSelect) {
            this.settings.selectedKnowledgeBase = kbSelect.value || null;
        }
        
        localStorage.setItem('sparklink_settings', JSON.stringify(this.settings));
        document.getElementById('settingsModal').style.display = 'none';
        this.showToast('设置已保存', 'success');
    }
    
    resetSettings() {
        this.settings = {
            maxTokens: 2000,
            temperature: 0.7,
            searchTopK: 5,
            similarityThreshold: 0.7,
            selectedKnowledgeBase: null
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
        // 创建新的 toast 元素，与 chat.js 保持一致
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // 显示动画
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // 自动隐藏
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
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

    // 页面切换方法
    showChatContainer() {
        const chatContainer = document.getElementById('chatContainer');
        const knowledgeContainer = document.getElementById('knowledgeContainer');
        
        if (chatContainer) {
            chatContainer.style.display = 'block';
        }
        if (knowledgeContainer) {
            knowledgeContainer.style.display = 'none';
        }
    }

    showKnowledgeContainer() {
        const chatContainer = document.getElementById('chatContainer');
        const knowledgeContainer = document.getElementById('knowledgeContainer');
        
        if (chatContainer) {
            chatContainer.style.display = 'none';
        }
        if (knowledgeContainer) {
            knowledgeContainer.style.display = 'block';
        }
    }

    // 搜索策略按钮事件绑定
    bindStrategyButtons() {
        const knowledgeBtn = document.getElementById('knowledgeBtn');
        const webBtn = document.getElementById('webBtn');
        const autoBtn = document.getElementById('autoBtn');

        if (knowledgeBtn) {
            knowledgeBtn.addEventListener('click', () => this.handleStrategyButtonClick('knowledge'));
        }
        
        if (webBtn) {
            webBtn.addEventListener('click', () => this.handleStrategyButtonClick('web'));
        }
        
        if (autoBtn) {
            autoBtn.addEventListener('click', () => this.handleStrategyButtonClick('auto'));
        }
    }

    // 处理策略按钮点击
    handleStrategyButtonClick(buttonType) {
        const knowledgeBtn = document.getElementById('knowledgeBtn');
        const webBtn = document.getElementById('webBtn');
        const autoBtn = document.getElementById('autoBtn');

        if (buttonType === 'auto') {
            // 选择AUTO时，取消其他按钮选择
            if (knowledgeBtn) knowledgeBtn.classList.remove('active');
            if (webBtn) webBtn.classList.remove('active');
            if (autoBtn) autoBtn.classList.add('active');
        } else {
            // 选择知识库或联网时，取消AUTO选择
            if (autoBtn) autoBtn.classList.remove('active');
            
            if (buttonType === 'knowledge') {
                if (knowledgeBtn) {
                    knowledgeBtn.classList.toggle('active');
                }
            } else if (buttonType === 'web') {
                if (webBtn) {
                    webBtn.classList.toggle('active');
                }
            }
        }
    }
}

// 快速消息功能
function sendQuickMessage(message) {
    const messageInput = document.getElementById('messageInput');
    messageInput.value = message;
    app.sendMessage();
}

// 思考过程折叠/展开函数
function toggleThinking(button) {
    // 兼容旧内联按钮：触发其所在容器的 header 点击，由事件委托处理折叠
    const headerEl = button.closest('.collapsible-container')?.querySelector('.collapsible-header');
    if (headerEl) {
        headerEl.click();
    }
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