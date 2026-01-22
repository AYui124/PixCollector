FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 更换apt源为清华源
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖（curl用于网络测试，如不需要可以移除）
RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装 Python 依赖（使用清华源）
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

# 安装gunicorn
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir gunicorn

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 5000

# 默认保持容器运行（使用sleep infinity）
CMD ["sleep", "infinity"]
