# 使用官方 Python 3.10 基础镜像
FROM python:3.10-slim

# Node.js 版本（可覆盖）
ARG NODE_VERSION=22.15.0

# 设置工作目录
WORKDIR /app

# 切换 Debian 源到阿里云镜像（主仓库 + 安全更新）
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|http://deb.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources

# apt 强制禁用代理，直连国内镜像（优先级高于系统 http_proxy，不影响其他命令）
RUN printf 'Acquire::http::Proxy "false";\nAcquire::https::Proxy "false";\n' > /etc/apt/apt.conf.d/99-no-proxy.conf

# 安装系统依赖：FFmpeg、Chromium/Puppeteer/Playwright 共享库
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates xz-utils \
    ffmpeg \
    # Chromium / Playwright / Puppeteer 共享库
    libnss3 libnspr4 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libxshmfence1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Node.js 22 — 从阿里云 nodejs-release 镜像下载二进制包直装（完全不走海外网络）
RUN curl -fsSL https://mirrors.aliyun.com/nodejs-release/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz \
    -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.xz \
    && node -v && npm -v

# 复制依赖文件
COPY requirements.txt .

# 切换阿里pypi源再安装依赖
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple && \
    pip install --no-cache-dir -r requirements.txt

# 走宿主机SSH隧道直连Playwright官方下载浏览器
  RUN HTTP_PROXY=http://host.docker.internal:1080 HTTPS_PROXY=http://host.docker.internal:1080 python -m playwright install chromium --with-deps

# 切换淘宝npm国内镜像，再安装依赖
RUN npm config set registry https://registry.npmmirror.com && \
    npm install -g hyperframes@0.6.121

# 复制应用代码
COPY . .

# 创建运行时需要的目录
RUN mkdir -p storage/exported_videos storage/temp_render storage/logs storage/shared_html

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
