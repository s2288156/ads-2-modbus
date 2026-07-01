FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 日志目录
RUN mkdir -p /app/logs

EXPOSE 5020

CMD ["python", "main.py", "--config", "config/mapping.yaml"]
