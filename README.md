# SparkLink AI - 智能聊天助手系统

基于 FastAPI + Celery + Redis + MySQL + Milvus 构建的智能聊天助手系统，支持知识库增强和联网搜索。

## 🌟 主要特性

- **智能对话**: 基于大语言模型的高质量对话生成
- **知识库增强**: 支持文档上传、解析、向量化和智能检索
- **联网搜索**: 智能判断模式，知识库不足时自动联网搜索
- **流式响应**: 支持 SSE 流式对话，提供实时交互体验
- **异步处理**: 使用 Celery 处理文档解析和向量生成任务
- **多格式支持**: 支持 PDF、Word、PPT、图片等多种文档格式
- **PocketFlow框架**: 智能搜索策略，动态决策最优搜索方案
- **用户会话管理**: 支持多用户、多会话的聊天管理
- **UUID用户系统**: 支持UUID格式的用户标识符

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Celery        │    │   前端界面       │
│   Web服务       │◄──►│   异步任务      │    │   (可选)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   MySQL         │    │   Redis         │
│   关系数据库     │    │   缓存/队列     │
└─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Milvus        │    │   外部API       │
│   向量数据库     │    │   LLM/搜索      │
└─────────────────┘    └─────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.13+
- MySQL 8.0+
- Redis 5.0+
- Milvus 2.4+ (可选，用于向量存储)
- uv (Python 包管理器)

### 安装步骤

1. **克隆项目**
```bash
git clone git@github.com:lemonguess/sparklinkAI.git
cd sparklinkAI
```

2. **安装依赖**
```bash
# 使用 uv 管理依赖
uv sync
```

3. **配置环境变量**
```bash
# 创建 .env 文件，填入你的 API 密钥
vim .env
```

4. **配置数据库**
```bash
# 创建 MySQL 数据库
mysql -u root -p -e "CREATE DATABASE sparklinkai;"

# 启动 Redis
redis-server
```

5. **启动服务**
```bash
# 启动 FastAPI 服务
uv run python main.py

# 启动 Celery Worker (新终端)
uv run python celery_worker.py
```

6. **访问服务**
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 📝 配置说明

### .env 文件配置

```env
# SiliconFlow API 配置 (主要LLM和嵌入模型)
SILICONFLOW_API_KEY=your_siliconflow_api_key_here
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# TextIn OCR API 配置
TEXTIN_API_KEY=your_textin_api_key_here
TEXTIN_API_SECRET=your_textin_api_secret_here

# Web 搜索 API 配置 (博查)
WEB_SEARCH_API_KEY=your_web_search_api_key_here

# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=sparklinkai

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### conf.ini 配置文件

系统的详细配置在 `config/conf.ini` 中，包括：
- 模型参数配置
- 知识库配置
- 搜索策略配置
- 性能参数配置

## 🔧 API 使用

### 聊天接口

```bash
# 发送聊天消息
curl -X POST "http://localhost:8000/api/v1/chat/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下人工智能",
    "user_id": "your-user-id",
    "session_id": "your-session-id",
    "use_knowledge_base": true,
    "use_web_search": true,
    "stream": false
  }'

# 流式聊天
curl -X POST "http://localhost:8000/api/v1/chat/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下人工智能",
    "user_id": "your-user-id",
    "session_id": "your-session-id",
    "use_knowledge_base": true,
    "use_web_search": true
  }'

# 创建聊天会话
curl -X POST "http://localhost:8000/api/v1/chat/create-session" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "title": "新的聊天会话"
  }'
```

### 文档上传

```bash
# 上传文档到知识库
curl -X POST "http://localhost:8000/api/v1/kb/documents/upload" \
  -F "file=@document.pdf" \
  -F "user_id=your-user-id"

# 获取文档列表
curl -X GET "http://localhost:8000/api/v1/kb/documents?user_id=your-user-id&skip=0&limit=20"

# 获取单个文档信息
curl -X GET "http://localhost:8000/api/v1/kb/documents/1"

# 删除文档
curl -X DELETE "http://localhost:8000/api/v1/kb/documents/1"
```

### 知识库管理

```bash
# 创建知识库
curl -X POST "http://localhost:8000/api/v1/kb/knowledge-bases" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的知识库",
    "description": "用于存储相关文档的知识库"
  }'

# 获取知识库列表
curl -X GET "http://localhost:8000/api/v1/kb/knowledge-bases?skip=0&limit=20"
```

### 知识库搜索

```bash
# 搜索知识库
curl -X POST "http://localhost:8000/api/v1/kb/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能的发展历史",
    "top_k": 10,
    "similarity_threshold": 0.7,
    "collection_name": "kb_12345678"
  }'
```

## 🧠 PocketFlow 智能搜索

PocketFlow 是本项目的核心智能搜索框架，实现了以下功能：

### 智能决策策略

1. **知识库优先**: 首先搜索本地知识库
2. **智能判断**: 根据结果质量和置信度决定是否联网
3. **动态调整**: 根据查询类型调整搜索策略
4. **结果融合**: 智能合并和排序多源结果

### 决策因子

- 结果数量阈值
- 置信度阈值
- 覆盖度评估
- 查询类型分析
- 质量分数计算

### 使用示例

```python
from services.chat_service import ChatService, SearchStrategy

# 创建聊天服务实例
chat_service = ChatService()

# 方式1: 智能搜索
result = await chat_service.intelligent_search(
    query="人工智能的最新发展",
    strategy=SearchStrategy.AUTO,
    max_results=10
)

print(f"搜索策略: {result['strategy']}")
print(f"决策原因: {result['decision_reasoning']}")
print(f"结果数量: {result['total_results_count']}")
print(f"使用框架: {result['performance_metrics']['framework']}")

# 方式2: 智能聊天（自动搜索+生成回复）
response = await chat_service.intelligent_chat(
    message="请介绍人工智能的最新发展",
    strategy=SearchStrategy.AUTO
)

print(f"AI回复: {response}")
```

## 📊 系统监控

### 健康检查

```bash
# 检查系统状态
curl http://localhost:8000/health

# 检查系统信息
curl http://localhost:8000/api/v1/system/status

# 获取系统统计信息
curl http://localhost:8000/api/v1/system/stats

# 检查数据库连接
curl http://localhost:8000/api/v1/system/db-status
```

### 性能指标

- 响应时间监控（通过 X-Process-Time 头部）
- 搜索质量评估
- 资源使用统计
- 任务执行状态
- 数据库连接状态
- Redis 连接状态

## 🔄 开发指南

### 项目结构

```
sparklinkAI/
├── api/                     # API 路由
│   ├── chat.py              # 聊天相关接口
│   ├── knowledge_base.py    # 知识库相关接口
│   └── system.py            # 系统相关接口
├── core/                    # 核心配置
│   ├── config.py            # 配置管理
│   └── database.py          # 数据库连接
├── models/                  # 数据模型
│   ├── database.py          # 数据库模型
│   └── schemas.py           # Pydantic 模型
├── services/                # 业务服务
│   ├── chat_service.py      # 聊天服务
│   ├── document_service.py  # 文档处理服务
│   ├── embedding_service.py # 嵌入向量服务
│   ├── knowledge_service.py # 知识库服务
│   ├── search_service.py    # 搜索服务
│   ├── vector_service.py    # 向量数据库服务
│   ├── celery_app.py        # Celery 应用配置
│   └── tasks/               # Celery 任务
│       ├── document_tasks.py    # 文档处理任务
│       ├── embedding_tasks.py   # 嵌入向量任务
│       └── search_tasks.py      # 搜索任务
├── config/                  # 配置文件
│   └── conf.ini             # 系统配置
├── static/                  # 静态文件
│   ├── css/                 # 样式文件
│   ├── js/                  # JavaScript 文件
│   └── libs/                # 第三方库
├── templates/               # 模板文件
│   └── index.html           # 主页模板
├── utils/                   # 工具模块
├── .env                     # 环境变量
├── main.py                  # 主程序入口
├── celery_worker.py         # Celery Worker
├── pyproject.toml           # 项目依赖配置
└── docker-compose.yml       # Docker 编排配置
```

### 添加新功能

1. **添加新的API端点**
   - 在 `api/` 下创建新的路由文件
   - 在 `main.py` 中注册路由

2. **添加新的服务**
   - 在 `services/` 下创建服务类
   - 实现业务逻辑和外部API调用

3. **添加新的任务**
   - 在 `services/tasks/` 下创建任务文件
   - 使用 `@celery_app.task` 装饰器

### 开发工具

```bash
# 安装开发依赖
uv add --dev pytest pytest-cov black isort

# 代码格式化
uv run black .
uv run isort .

# 运行测试（需要先安装pytest）
uv run pytest

# 测试覆盖率
uv run pytest --cov=.
```

## 🚀 部署

### Docker 部署

```bash
# 构建镜像
docker build -t sparklinkai .

# 运行容器
docker-compose up -d
```

### 生产环境

1. 使用 Gunicorn 或 uWSGI 部署 FastAPI
2. 使用 Nginx 作为反向代理
3. 配置 SSL 证书
4. 设置监控和日志

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [Celery](https://docs.celeryproject.org/) - 分布式任务队列
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包和 ORM
- [Redis](https://redis.io/) - 内存数据结构存储
- [MySQL](https://www.mysql.com/) - 关系型数据库
- [Milvus](https://milvus.io/) - 向量数据库
- [PocketFlow](https://github.com/pocketflow/pocketflow) - 智能搜索框架
- [uv](https://github.com/astral-sh/uv) - 极速 Python 包管理器
- [SiliconFlow](https://siliconflow.cn/) - AI 模型服务平台