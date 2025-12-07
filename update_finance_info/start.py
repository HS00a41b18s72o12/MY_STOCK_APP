import time
import schedule
from main import FinanceUpdater

if __name__ == "__main__":
    updater = FinanceUpdater()

    # 1. 日次バッチのスケジュール設定 (平日18:00)
    # ※土日判定をここで入れるか、main.py内で common.check_holiday() を使う
    schedule.every().monday.at("18:00").do(updater.update_all_stocks_daily)
    schedule.every().tuesday.at("18:00").do(updater.update_all_stocks_daily)
    schedule.every().wednesday.at("18:00").do(updater.update_all_stocks_daily)
    schedule.every().thursday.at("18:00").do(updater.update_all_stocks_daily)
    schedule.every().friday.at("18:00").do(updater.update_all_stocks_daily)

    print("Update Finance Info Container Started.")

    while True:
        # A. スケジュール実行 (18:00の処理)
        schedule.run_pending()

        # B. 新規銘柄のポーリング監視
        updater.check_new_stocks()

        time.sleep(25)