FROM python:3.12-slim

WORKDIR /app

COPY update_finance_info/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ★ 共有フォルダをコピー
COPY common/ ./common/

# ★ アプリ本体をコピー
COPY update_finance_info/ .

CMD ["python", "start.py"]