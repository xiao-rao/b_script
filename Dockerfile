# 基础镜像，使用 Python 3.10+
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖，包括 git 和 Playwright 所需的其他依赖
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg2 \
    ca-certificates \
    git \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libatspi2.0-0 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libxss1 \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgtk-3-0 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libx11-6 \
    libx11-6 && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# 克隆仓库中的代码
RUN git clone --single-branch --branch master https://github.com/xiao-rao/b_script.git /app

# 安装 Python 项目依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 安装 Playwright 和浏览器
RUN pip install --upgrade pip
RUN pip install playwright
RUN python3 -m playwright install

# 运行脚本
CMD ["python3", "client.py"]