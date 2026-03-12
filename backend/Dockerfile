FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

# 复制代码
COPY . .

# 创建必要目录
RUN mkdir -p uploads outputs data/chroma_db

# Railway 使用 PORT 环境变量
ENV PORT=8000
EXPOSE ${PORT}

# 启动 - 使用 shell 形式以支持环境变量替换
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
