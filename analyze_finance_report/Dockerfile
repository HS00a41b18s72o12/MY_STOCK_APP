FROM python:3.12-slim

WORKDIR /app

COPY analyze_finance_report/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ★ 共有フォルダをコピー
COPY common/ ./common/

# ★ アプリ本体をコピー
COPY analyze_finance_report/ .

CMD ["python", "start.py"]