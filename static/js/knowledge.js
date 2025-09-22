/**
 * 知识库管理页面功能模块
 * 处理文档管理和知识召回检测的所有交互逻辑
 */

class KnowledgeManager {
    constructor() {
        this.documents = [];
        this.selectedDocuments = [];
        this.isUploading = false;
        this.isRecalling = false;
        
        this.init();
    }

    /**
     * 初始化知识库管理器
     */
    init() {
        this.bindEvents();
        // this.loadDocuments(); // 暂时注释掉，后端未实现对应接口
        this.setupDragAndDrop();
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 新建知识库按钮
        Utils.DOM.on('#newKnowledgeBtn', 'click', () => this.showNewKnowledgeModal());

        // 上传文档按钮
        Utils.DOM.on('#uploadDocBtn', 'click', () => this.showUploadModal());

        // 上传文本按钮
        Utils.DOM.on('#uploadTextBtn', 'click', () => this.showTextUploadModal());

        // 刷新按钮
        Utils.DOM.on('#refreshDocsBtn', 'click', () => this.loadDocuments());

        // 知识召回测试按钮
        Utils.DOM.on('#recallTestBtn', 'click', () => this.performRecallTest());

        // 召回输入框回车事件
        Utils.DOM.on('#recallInput', 'keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.performRecallTest();
            }
        });

        // 文档列表点击事件委托
        Utils.DOM.on('#documentsList', 'click', (e) => {
            if (e.target.classList.contains('document-action-btn')) {
                const action = e.target.dataset.action;
                const docId = e.target.closest('.document-item').dataset.docId;
                this.handleDocumentAction(action, docId);
            } else if (e.target.closest('.document-item')) {
                const docItem = e.target.closest('.document-item');
                this.toggleDocumentSelection(docItem);
            }
        });

        // 模态框事件
        this.bindModalEvents();
    }

    /**
     * 绑定模态框事件
     */
    bindModalEvents() {
        // 新建知识库模态框
        Utils.DOM.on('#createKnowledgeBtn', 'click', () => this.createKnowledge());
        
        // 文档上传模态框
        Utils.DOM.on('#uploadFileBtn', 'click', () => this.uploadDocument());
        Utils.DOM.on('#documentFile', 'change', (e) => this.handleFileSelect(e));
        
        // 文本上传模态框
        Utils.DOM.on('#uploadTextContentBtn', 'click', () => this.uploadTextContent());
        
        // 关闭模态框
        Utils.DOM.getAll('.modal-close, .close').forEach(btn => {
            Utils.DOM.on(btn, 'click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    this.hideModal(modal.id);
                }
            });
        });

        // 点击模态框背景关闭
        Utils.DOM.getAll('.modal').forEach(modal => {
            Utils.DOM.on(modal, 'click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal.id);
                }
            });
        });
    }

    /**
     * 设置拖拽上传
     */
    setupDragAndDrop() {
        const uploadArea = Utils.DOM.get('#uploadArea');
        if (!uploadArea) return;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                Utils.DOM.addClass(uploadArea, 'dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                Utils.DOM.removeClass(uploadArea, 'dragover');
            });
        });

        uploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFiles(files);
            }
        });

        // 点击上传区域
        Utils.DOM.on(uploadArea, 'click', () => {
            const fileInput = Utils.DOM.get('#documentFile');
            if (fileInput) {
                fileInput.click();
            }
        });
    }

    /**
     * 加载文档列表
     */
    async loadDocuments() {
        try {
            const response = await Utils.HTTP.get('/api/knowledge/documents');
            if (response.success) {
                this.documents = response.documents;
                this.renderDocuments();
            } else {
                this.showError('加载文档列表失败：' + response.error);
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            console.error('Load documents error:', error);
        }
    }

    /**
     * 渲染文档列表
     */
    renderDocuments() {
        const container = Utils.DOM.get('#documentsList');
        if (!container) return;

        container.innerHTML = '';

        if (this.documents.length === 0) {
            const emptyState = Utils.DOM.create('div', {
                className: 'empty-state'
            });
            emptyState.innerHTML = `
                <div class="empty-icon">📄</div>
                <h3>暂无文档</h3>
                <p>点击上传按钮添加您的第一个文档</p>
            `;
            container.appendChild(emptyState);
            return;
        }

        this.documents.forEach(doc => {
            const docElement = this.createDocumentElement(doc);
            container.appendChild(docElement);
        });
    }

    /**
     * 创建文档元素
     * @param {Object} doc - 文档数据
     * @returns {Element}
     */
    createDocumentElement(doc) {
        const element = Utils.DOM.create('div', {
            className: 'document-item',
            'data-doc-id': doc.id
        });

        element.innerHTML = `
            <div class="document-header">
                <h4 class="document-title">${Utils.String.escapeHtml(doc.title)}</h4>
                <div class="document-actions">
                    <button class="document-action-btn" data-action="view" title="查看">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="document-action-btn" data-action="edit" title="编辑">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="document-action-btn" data-action="delete" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="document-meta">
                <span><i class="fas fa-file"></i> ${doc.type}</span>
                <span><i class="fas fa-hdd"></i> ${Utils.String.formatFileSize(doc.size)}</span>
                <span><i class="fas fa-clock"></i> ${Utils.String.formatTime(doc.created_at)}</span>
            </div>
            <p class="document-description">${Utils.String.escapeHtml(doc.description || '暂无描述')}</p>
        `;

        return element;
    }

    /**
     * 切换文档选择状态
     * @param {Element} docItem - 文档元素
     */
    toggleDocumentSelection(docItem) {
        const docId = docItem.dataset.docId;
        
        if (Utils.DOM.get(docItem).classList.contains('selected')) {
            Utils.DOM.removeClass(docItem, 'selected');
            this.selectedDocuments = this.selectedDocuments.filter(id => id !== docId);
        } else {
            Utils.DOM.addClass(docItem, 'selected');
            this.selectedDocuments.push(docId);
        }
    }

    /**
     * 处理文档操作
     * @param {string} action - 操作类型
     * @param {string} docId - 文档ID
     */
    async handleDocumentAction(action, docId) {
        const doc = this.documents.find(d => d.id === docId);
        if (!doc) return;

        switch (action) {
            case 'view':
                this.viewDocument(doc);
                break;
            case 'edit':
                this.editDocument(doc);
                break;
            case 'delete':
                this.deleteDocument(doc);
                break;
        }
    }

    /**
     * 查看文档
     * @param {Object} doc - 文档数据
     */
    async viewDocument(doc) {
        try {
            const response = await Utils.HTTP.get(`/api/knowledge/documents/${doc.id}/content`);
            if (response.success) {
                // 显示文档内容模态框
                this.showDocumentContentModal(doc, response.content);
            } else {
                this.showError('获取文档内容失败');
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            console.error('View document error:', error);
        }
    }

    /**
     * 编辑文档
     * @param {Object} doc - 文档数据
     */
    editDocument(doc) {
        // 显示编辑文档模态框
        this.showEditDocumentModal(doc);
    }

    /**
     * 删除文档
     * @param {Object} doc - 文档数据
     */
    async deleteDocument(doc) {
        const confirmed = await Utils.Modal.confirm(`确定要删除文档"${doc.title}"吗？此操作不可撤销。`, '删除文档');
        if (!confirmed) return;

        try {
            const response = await Utils.HTTP.delete(`/api/knowledge/documents/${doc.id}`);
            if (response.success) {
                this.showSuccess('文档删除成功');
                // this.loadDocuments(); // 暂时注释掉，后端未实现对应接口
            } else {
                this.showError('删除文档失败：' + (response.message || response.error));
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            console.error('Delete document error:', error);
        }
    }

    /**
     * 处理文件选择
     * @param {Event} e - 文件选择事件
     */
    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.handleFiles(files);
        }
    }

    /**
     * 处理文件上传
     * @param {FileList} files - 文件列表
     */
    async handleFiles(files) {
        for (let file of files) {
            await this.uploadFile(file);
        }
    }

    /**
     * 上传单个文件
     * @param {File} file - 文件对象
     */
    async uploadFile(file) {
        if (this.isUploading) return;

        // 验证文件类型和大小
        if (!this.validateFile(file)) {
            return;
        }

        this.isUploading = true;
        this.showUploadProgress(0);

        try {
            const response = await Utils.HTTP.uploadFile(
                '/api/knowledge/upload',
                file,
                (progress) => this.showUploadProgress(progress)
            );

            if (response.success) {
                this.showSuccess('文件上传成功');
                this.loadDocuments();
                this.hideModal('uploadModal');
            } else {
                this.showError('文件上传失败：' + response.error);
            }
        } catch (error) {
            this.showError('上传失败，请稍后重试');
            console.error('Upload file error:', error);
        } finally {
            this.isUploading = false;
            this.hideUploadProgress();
        }
    }

    /**
     * 验证文件
     * @param {File} file - 文件对象
     * @returns {boolean}
     */
    validateFile(file) {
        const allowedTypes = [
            'text/plain',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/markdown'
        ];

        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!allowedTypes.includes(file.type)) {
            this.showError('不支持的文件类型，请上传 TXT、PDF、DOC、DOCX 或 MD 文件');
            return false;
        }

        if (file.size > maxSize) {
            this.showError('文件大小不能超过 10MB');
            return false;
        }

        return true;
    }

    /**
     * 显示上传进度
     * @param {number} progress - 进度百分比
     */
    showUploadProgress(progress) {
        const progressBar = Utils.DOM.get('#uploadProgress');
        const progressText = Utils.DOM.get('#uploadProgressText');
        
        if (progressBar) {
            progressBar.style.width = progress + '%';
        }
        
        if (progressText) {
            progressText.textContent = `上传中... ${Math.round(progress)}%`;
        }

        const progressContainer = Utils.DOM.get('#uploadProgressContainer');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
    }

    /**
     * 隐藏上传进度
     */
    hideUploadProgress() {
        const progressContainer = Utils.DOM.get('#uploadProgressContainer');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }

    /**
     * 上传文本内容
     */
    async uploadTextContent() {
        const title = Utils.DOM.get('#textTitle').value.trim();
        const content = Utils.DOM.get('#textContent').value.trim();

        if (!title || !content) {
            this.showError('请填写标题和内容');
            return;
        }

        try {
            const response = await Utils.HTTP.post('/api/knowledge/upload-text', {
                title: title,
                content: content
            });

            if (response.success) {
                this.showSuccess('文本上传成功');
                this.loadDocuments();
                this.hideModal('textUploadModal');
                
                // 清空表单
                Utils.DOM.get('#textTitle').value = '';
                Utils.DOM.get('#textContent').value = '';
            } else {
                this.showError('文本上传失败：' + response.error);
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            console.error('Upload text error:', error);
        }
    }

    /**
     * 执行知识召回测试
     */
    async performRecallTest() {
        const query = Utils.DOM.get('#recallInput').value.trim();
        
        if (!query) {
            this.showError('请输入查询内容');
            return;
        }

        if (this.isRecalling) return;

        this.isRecalling = true;
        const button = Utils.DOM.get('#recallTestBtn');
        const originalText = button.textContent;
        button.textContent = '检索中...';
        button.disabled = true;

        try {
            const response = await Utils.HTTP.post('/api/knowledge/recall', {
                query: query,
                top_k: 5,
                include_metadata: true
            });

            if (response.success) {
                this.displayRecallResults(response.results);
            } else {
                this.showError('知识召回失败：' + response.error);
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            console.error('Recall test error:', error);
        } finally {
            this.isRecalling = false;
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    /**
     * 显示召回结果
     * @param {Array} results - 召回结果
     */
    displayRecallResults(results) {
        const container = Utils.DOM.get('#recallResults');
        if (!container) return;

        container.innerHTML = '';

        if (results.length === 0) {
            const emptyState = Utils.DOM.create('div', {
                className: 'empty-state'
            });
            emptyState.innerHTML = `
                <div class="empty-icon">🔍</div>
                <h4>未找到相关内容</h4>
                <p>请尝试使用其他关键词</p>
            `;
            container.appendChild(emptyState);
            return;
        }

        results.forEach((result, index) => {
            const resultElement = this.createRecallResultElement(result, index);
            container.appendChild(resultElement);
        });
    }

    /**
     * 创建召回结果元素
     * @param {Object} result - 召回结果
     * @param {number} index - 索引
     * @returns {Element}
     */
    createRecallResultElement(result, index) {
        const element = Utils.DOM.create('div', {
            className: 'recall-result-item'
        });

        const score = Math.round(result.score * 100);
        const scoreClass = score >= 80 ? 'high' : score >= 60 ? 'medium' : 'low';

        element.innerHTML = `
            <div class="result-header">
                <div class="result-source">${Utils.String.escapeHtml(result.source || '未知来源')}</div>
                <div class="result-score ${scoreClass}">${score}%</div>
            </div>
            <div class="result-content">${Utils.String.escapeHtml(result.content)}</div>
            <div class="result-meta">
                <span>排名: ${index + 1}</span>
                <span>相似度: ${score}%</span>
                ${result.metadata ? `<span>类型: ${result.metadata.type || '未知'}</span>` : ''}
            </div>
        `;

        return element;
    }

    /**
     * 显示模态框
     * @param {string} modalId - 模态框ID
     */
    showModal(modalId) {
        const modal = Utils.DOM.get('#' + modalId);
        if (modal) {
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * 隐藏模态框
     * @param {string} modalId - 模态框ID
     */
    hideModal(modalId) {
        const modal = Utils.DOM.get('#' + modalId);
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    }

    /**
     * 显示新建知识库模态框
     */
    showNewKnowledgeModal() {
        this.showModal('newKnowledgeModal');
    }

    /**
     * 显示上传模态框
     */
    showUploadModal() {
        this.showModal('uploadModal');
    }

    /**
     * 显示文本上传模态框
     */
    showTextUploadModal() {
        this.showModal('textUploadModal');
    }

    /**
     * 创建知识库
     */
    async createKnowledge() {
        const name = Utils.DOM.get('#knowledgeName').value.trim();
        const description = Utils.DOM.get('#knowledgeDescription').value.trim();

        if (!name) {
            this.showError('请输入知识库名称');
            return;
        }

        try {
            const response = await Utils.HTTP.post('/api/knowledge/create', {
                name: name,
                description: description
            });

            if (response.success) {
                this.showSuccess('知识库创建成功');
                this.hideModal('newKnowledgeModal');
                
                // 清空表单
                Utils.DOM.get('#knowledgeName').value = '';
                Utils.DOM.get('#knowledgeDescription').value = '';
            } else {
                this.showError('创建知识库失败：' + response.error);
            }
        } catch (error) {
            this.showError('网络错误，请稍后重试');
            console.error('Create knowledge error:', error);
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
    window.knowledgeManager = new KnowledgeManager();
});