FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# context 已在 docker-compose 中设为项目根 (..)，此处复制整个项目到 /app
COPY . .

EXPOSE 8113

CMD ["python", "main.py"]