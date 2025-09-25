# 基于 Ubuntu 22.04 (使用官方镜像)
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 设置工作目录
WORKDIR /workspace

# 安装系统依赖和 Python
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    build-essential \
    gcc \
    g++ \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv (使用 pip 方式)
RUN pip3 install uv

# 复制 pyproject.toml 和 uv.lock 文件
COPY pyproject.toml uv.lock ./

# 安装 Python 环境和依赖 (使用清华源)
RUN uv sync --frozen --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件到容器
COPY . /workspace/

# 创建必要的目录
RUN mkdir -p uploads logs

# 暴露端口
EXPOSE 8000

# 设置默认命令，激活环境并启动应用
CMD ["uv", "run", "python", "main.py"]