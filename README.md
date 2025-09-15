# SparkLink AI - 智能聊天助手系统

基于 FastAPI + Celery + Redis + MySQL + Milvus 构建的智能聊天助手系统，支持知识库增强和联网搜索。

## 🌟 主要特性

- **智能对话**: 基于 DeepSeek-R1 模型的高质量对话生成
- **知识库增强**: 支持文档上传、解析、向量化和智能检索
- **联网搜索**: 智能判断模式，知识库不足时自动联网搜索
- **流式响应**: 支持 SSE 流式对话，提供实时交互体验
- **异步处理**: 使用 Celery 处理文档解析和向量生成任务
- **多格式支持**: 支持 PDF、Word、PPT、图片等多种文档格式
- **PocketFlow框架**: 智能搜索策略，动态决策最优搜索方案

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
- Redis 7.2+
- Milvus 2.4+ (可选)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd sparklinkAI
```

2. **安装依赖**
```bash
# 使用 uv 管理依赖
uv sync
```

3. **配置环境变量**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API 密钥
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
# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# SiliconFlow API 配置 (嵌入模型)
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
    "use_knowledge_base": true,
    "use_web_search": true,
    "stream": false
  }'
```

### 文档上传

```bash
# 上传文档到知识库
curl -X POST "http://localhost:8000/api/v1/kb/documents/upload" \
  -F "file=@document.pdf"
```

### 知识库搜索

```bash
# 搜索知识库
curl -X POST "http://localhost:8000/api/v1/kb/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能的发展历史",
    "top_k": 10,
    "similarity_threshold": 0.7
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
from app.utils.pocketflow import pocket_flow, SearchStrategy

# 智能搜索
result = await pocket_flow.intelligent_search(
    query="人工智能的最新发展",
    strategy=SearchStrategy.INTELLIGENT,
    max_results=10
)

print(f"搜索策略: {result['strategy']}")
print(f"决策原因: {result['decision_reasoning']}")
print(f"结果数量: {result['total_results_count']}")
```

## 📊 系统监控

### 健康检查

```bash
# 检查系统状态
curl http://localhost:8000/health

# 检查系统信息
curl http://localhost:8000/api/v1/system/status
```

### 性能指标

- 响应时间监控
- 搜索质量评估
- 资源使用统计
- 任务执行状态

## 🔄 开发指南

### 项目结构

```
sparklinkAI/
├── app/
│   ├── api/                 # API 路由
│   ├── core/                # 核心配置
│   ├── models/              # 数据模型
│   ├── services/            # 业务服务
│   │   └── tasks/           # Celery 任务
│   └── utils/               # 工具模块
├── config/                  # 配置文件
├── static/                  # 静态文件
├── templates/               # 模板文件
├── uploads/                 # 上传文件
├── .env                     # 环境变量
├── main.py                  # 主程序入口
└── celery_worker.py         # Celery Worker
```

### 添加新功能

1. **添加新的API端点**
   - 在 `app/api/` 下创建新的路由文件
   - 在 `app/main.py` 中注册路由

2. **添加新的服务**
   - 在 `app/services/` 下创建服务类
   - 实现业务逻辑和外部API调用

3. **添加新的任务**
   - 在 `app/services/tasks/` 下创建任务文件
   - 使用 `@celery_app.task` 装饰器

### 测试

```bash
# 运行测试
uv run pytest

# 测试覆盖率
uv run pytest --cov=app
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
- [Milvus](https://milvus.io/) - 向量数据库
- [SiliconFlow](https://siliconflow.cn/) - 嵌入模型服务
- [DeepSeek](https://www.deepseek.com/) - 大语言模型