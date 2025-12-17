FROM python:3.12-slim

WORKDIR /app

COPY db_manage/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ★ 共有フォルダをコピー
COPY common/ ./common/

# ★ アプリ本体をコピー
COPY db_manage/ .

CMD ["python", "start.py"]