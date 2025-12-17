import time
import schedule
from main import DbBackuper

if __name__ == "__main__":
    backuper = DbBackuper()

    # 平日 20:00 にバッチ開始
    # DBバックアップ実行スケジュール設定
    schedule.every().monday.at("20:00").do(backuper.backup)
    schedule.every().tuesday.at("20:00").do(backuper.backup)
    schedule.every().wednesday.at("20:00").do(backuper.backup)
    schedule.every().thursday.at("20:00").do(backuper.backup)
    schedule.every().friday.at("20:00").do(backuper.backup)
    # 開発用: 起動時に一度だけチェックを走らせる（テストしたい場合）
    # backuper.backup()

    # ダミーデータ登録
    backuper.insert_dummy_data()

    print("backup db Container Started.")

    while True:
        schedule.run_pending()
        time.sleep(10)