import time
import schedule
from main import FinanceAnalyzer

if __name__ == "__main__":
    analyzer = FinanceAnalyzer()

    # 平日 19:15 にバッチ開始
    # search_disclosure (19:10開始) がデータを入れ始めるのを待ってから動く
    schedule.every().monday.at("19:15").do(analyzer.run_analysis_batch)
    schedule.every().tuesday.at("19:15").do(analyzer.run_analysis_batch)
    schedule.every().wednesday.at("19:15").do(analyzer.run_analysis_batch)
    schedule.every().thursday.at("19:15").do(analyzer.run_analysis_batch)
    schedule.every().friday.at("19:15").do(analyzer.run_analysis_batch)
    
    # 開発用: 起動時に一度だけチェックを走らせる（テストしたい場合）
    # analyzer.run_analysis_batch()

    print("Analyze Finance Report Container Started.")

    while True:
        schedule.run_pending()
        time.sleep(10)