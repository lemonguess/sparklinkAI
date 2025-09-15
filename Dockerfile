FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 复制项目文件
COPY pyproject.toml uv.lock ./

# 安装 Python 依赖
RUN uv sync --frozen

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads logs static templates

# 设置权限
RUN chmod +x main.py celery_worker.py

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "python", "main.py"]