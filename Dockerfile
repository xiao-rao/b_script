# 使用 ARG 来指定基础镜像和系统类型
ARG BASE_IMAGE=python:3.10-slim
FROM ${BASE_IMAGE}

# 设置系统类型参数
ARG SYSTEM_TYPE=debian
# 可选值: debian, centos, fedora

# 设置工作目录
WORKDIR /app

# 根据不同系统安装依赖和 Chrome
RUN if [ "$SYSTEM_TYPE" = "debian" ]; then \
        # Debian/Ubuntu 系统安装方式
        apt-get update && apt-get install -y \
        curl wget gnupg2 ca-certificates git \
        libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
        libatspi2.0-0 libgbm1 libnspr4 libnss3 libxss1 \
        fonts-liberation libappindicator3-1 libasound2 \
        libatk-bridge2.0-0 libatk1.0-0 libgtk-3-0 \
        libdbus-1-3 libgdk-pixbuf2.0-0 libx11-6 && \
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
        sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' && \
        apt-get update && \
        apt-get install -y google-chrome-stable && \
        rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* ; \
    elif [ "$SYSTEM_TYPE" = "centos" ]; then \
        # CentOS 系统安装方式
        yum install -y wget git python3-pip && \
        wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm && \
        yum install -y ./google-chrome-stable_current_x86_64.rpm && \
        yum install -y \
        pango.x86_64 libXcomposite.x86_64 libXcursor.x86_64 libXdamage.x86_64 \
        libXext.x86_64 libXi.x86_64 libXtst.x86_64 cups-libs.x86_64 libXScrnSaver.x86_64 \
        libXrandr.x86_64 GConf2.x86_64 alsa-lib.x86_64 atk.x86_64 gtk3.x86_64 \
        ipa-gothic-fonts xorg-x11-fonts-100dpi xorg-x11-fonts-75dpi xorg-x11-utils \
        xorg-x11-fonts-cyrillic xorg-x11-fonts-Type1 xorg-x11-fonts-misc && \
        rm google-chrome-stable_current_x86_64.rpm && \
        yum clean all ; \
    elif [ "$SYSTEM_TYPE" = "fedora" ]; then \
        # Fedora 系统安装方式
        dnf install -y wget git python3-pip && \
        wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm && \
        dnf install -y ./google-chrome-stable_current_x86_64.rpm && \
        dnf install -y \
        pango libXcomposite libXcursor libXdamage \
        libXext libXi libXtst cups-libs libXScrnSaver \
        libXrandr GConf2 alsa-lib atk gtk3 \
        ipa-gothic-fonts xorg-x11-fonts-100dpi xorg-x11-fonts-75dpi xorg-x11-utils \
        xorg-x11-fonts-cyrillic xorg-x11-fonts-Type1 xorg-x11-fonts-misc && \
        rm google-chrome-stable_current_x86_64.rpm && \
        dnf clean all ; \
    fi

# 克隆仓库中的代码
RUN git clone --single-branch --branch master https://github.com/xiao-rao/b_script.git /app

# 创建配置文件，根据不同系统设置不同的 Chrome 路径
RUN if [ "$SYSTEM_TYPE" = "debian" ]; then \
        echo '{\
            "client_id": null,\
            "chrome_path": {\
                "windows": "",\
                "darwin": "",\
                "linux": "/usr/bin/google-chrome"\
            }\
        }' > /app/config.json ; \
    elif [ "$SYSTEM_TYPE" = "centos" ] || [ "$SYSTEM_TYPE" = "fedora" ]; then \
        echo '{\
            "client_id": null,\
            "chrome_path": {\
                "windows": "",\
                "darwin": "",\
                "linux": "/usr/bin/google-chrome-stable"\
            }\
        }' > /app/config.json ; \
    fi

# 安装 Python 项目依赖
COPY requirements.txt .
RUN if [ "$SYSTEM_TYPE" = "debian" ]; then \
        pip install -r requirements.txt ; \
    else \
        pip3 install -r requirements.txt ; \
    fi

# 安装 Playwright
RUN if [ "$SYSTEM_TYPE" = "debian" ]; then \
        pip install --upgrade pip && \
        pip install playwright && \
        python3 -m playwright install chromium ; \
    else \
        pip3 install --upgrade pip && \
        pip3 install playwright && \
        python3 -m playwright install chromium ; \
    fi

# 确保配置文件权限正确
RUN chmod 644 /app/config.json

# 验证 Chrome 安装
RUN if [ "$SYSTEM_TYPE" = "debian" ]; then \
        google-chrome --version ; \
    else \
        google-chrome-stable --version ; \
    fi

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV SYSTEM_TYPE=${SYSTEM_TYPE}

# 运行脚本
CMD ["python3", "client.py"]