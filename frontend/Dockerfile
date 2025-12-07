FROM python:3.12-slim

WORKDIR /app

# ルートの requirements.txt をコピーする場合の例（なければ frontend/requirements.txt）
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ★ 共有フォルダをコンテナ内にコピー
COPY common/ ./common/

# ★ アプリ本体をコンテナ内にコピー
COPY frontend/ .

# python start.py ではなく gunicorn で起動する
# -w 4 : ワーカープロセスを4つ立ち上げる（4つの処理を同時にさばける）
# -b 0.0.0.0:5000 : 5000番ポートで待ち受ける
# --reload : ソースコード変更時に自動で再起動（開発環境向け）
# start:app : start.py ファイルの中にある app という変数を実行する
CMD ["gunicorn", "--reload", "-w", "4", "-b", "0.0.0.0:5000", "start:app"]
# CMD ["python", "start.py"]