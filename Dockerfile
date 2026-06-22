# 使用官方 Python 3.10 基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖：FFmpeg、Node.js 22、Chromium/Puppeteer/Playwright 共享库
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    ffmpeg \
    # Chromium / Playwright / Puppeteer 共享库
    libnss3 libnspr4 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libxshmfence1 \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && node -v && npm -v \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright Chromium 浏览器
RUN python -m playwright install chromium --with-deps

# 全局安装 HyperFrames（锁定版本，加速首次渲染）
RUN npm install -g hyperframes@0.6.121

# 复制应用代码
COPY . .

# 创建运行时需要的目录
RUN mkdir -p exported_videos temp_render

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
