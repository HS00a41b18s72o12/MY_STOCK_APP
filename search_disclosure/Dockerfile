FROM python:3.12-slim

WORKDIR /app

COPY search_disclosure/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ★ 共有フォルダをコピー
COPY common/ ./common/

# ★ アプリ本体をコピー
COPY search_disclosure/ .

CMD ["python", "start.py"]