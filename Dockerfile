FROM docker.m.daocloud.io/library/python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# 复制源码
COPY . .

# 日志目录
RUN mkdir -p /app/logs

EXPOSE 5020

CMD ["python", "main.py", "--config", "config/mapping.yaml"]
