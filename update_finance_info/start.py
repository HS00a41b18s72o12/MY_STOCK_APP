import time
import schedule
from main import FinanceUpdater

if __name__ == "__main__":
    updater = FinanceUpdater()

    # 1. バッチのスケジュール設定
    # 現在値など市場情報は10:00と18:00に更新
    schedule.every().monday.at("10:00").do(updater.update_all_stocks)
    schedule.every().tuesday.at("10:00").do(updater.update_all_stocks)
    schedule.every().wednesday.at("10:00").do(updater.update_all_stocks)
    schedule.every().thursday.at("10:00").do(updater.update_all_stocks)
    schedule.every().friday.at("10:00").do(updater.update_all_stocks)

    schedule.every().monday.at("18:00").do(updater.update_all_stocks)
    schedule.every().tuesday.at("18:00").do(updater.update_all_stocks)
    schedule.every().wednesday.at("18:00").do(updater.update_all_stocks)
    schedule.every().thursday.at("18:00").do(updater.update_all_stocks)
    schedule.every().friday.at("18:00").do(updater.update_all_stocks)

    print("Update Finance Info Container Started.")

    while True:
        # A. スケジュール実行 (18:00の処理)
        schedule.run_pending()

        # B. 新規銘柄のポーリング監視
        updater.check_new_stocks()

        time.sleep(25)