import os
import time
import datetime

from functions import browser
from functions import common
from common.models import Stock, Disclosure

class DisclosureClass:
    def __init__(self):
        self.selenium_url = os.environ.get("SELENIUM_URL")
        self.stock_disclosure_url = os.environ.get("SEARCH_DISCLOSURE_URL")
        self.database_url = os.environ.get("DATABASE_URL")
        self.search_keyword = os.environ.get("SEARCH_KEYWORD")

    def main_process(self):
        # 祝日だった場合、処理を行わない
        print("Check holiday")
        if common.check_holiday():
            print("Today is holiday, quit process")
            return None
        # ブラウザ起動
        driver = browser.open_browser(self.selenium_url, False)

        # 今日の適時開示からキーワードを含む情報を取得
        print("Get today's stock disclosure information")
        date = time.localtime()
        todays_stock_disclosure_info_json = self.get_stock_disclosure(driver, date)
        
        # DBから自分の保有株式コードを取得
        print("Get my stock code list from DB")
        my_stock_code_list = self.get_my_stock_code_list()

        # 保有株式コードに該当する適時開示情報を取得
        print("Pick up my stock in the stock disclosure information")
        my_stock_disclosure_info_json = self.pickup_my_stock_disclosure(driver, todays_stock_disclosure_info_json, my_stock_code_list)

        # テーブル更新
        print("Update database")
        self.update_database(my_stock_disclosure_info_json)
        print("my_stock_disclosure_info_json")
        print(my_stock_disclosure_info_json)

    """
    当日の適時開示情報を取得する
    """
    def get_stock_disclosure(self, driver, date):
        todays_stock_disclosure_url = common.create_stock_disclosure_url(self.stock_disclosure_url, date)
        # get stock disclosure information
        todays_stock_disclosure_info = browser.get_todays_stock_disclosure_info(driver, todays_stock_disclosure_url)
        # select containing search keyword
        filtered_json = common.filter_disclosure_by_keyword(todays_stock_disclosure_info, self.search_keyword)
        return filtered_json

    """
    適時開示情報の中から自身の保有株式コードに該当するものを取得する
    """
    def pickup_my_stock_disclosure(self, driver, todays_stock_disclosure_info_json, my_stock_code_list):
        temp_my_stock_disclosure_info_json = common.get_my_stock_disclosure_info(todays_stock_disclosure_info_json, my_stock_code_list)
        my_stock_disclosure = browser.get_disclosure_pdf_info(driver, temp_my_stock_disclosure_info_json)
        return my_stock_disclosure

    """
    DBから銘柄コードのリストを取得する
    """
    def get_my_stock_code_list(self):
        db = SessionLocal()
        stock_list = []
        try:
            # Stockテーブルから全レコード取得
            stocks = db.query(Stock).all()
            # コードだけをリストにする
            stock_list = [stock.stock_code for stock in stocks]
            print(f"Target Stocks: {stock_list}")
        finally:
            db.close()
        return stock_list

    def update_database(self, my_stock_disclosure_info_json):
        """取得した情報をDBに保存する"""
        db = SessionLocal()
        try:
            for item in my_stock_disclosure_info_json:
                # PDF URLが取得できていないものはスキップする場合
                if not item.get('disclosure_pdf_url'):
                    continue

                # announce_timeをdatetimeに変換
                now = datetime.datetime.now()
                announce_time_str = item['announce_time']
                hour, minute = map(int, announce_time_str.split(':'))
                announce_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # Disclosureモデルのインスタンス作成
                new_disclosure = Disclosure(
                    stock_code=item['stock_code'],
                    announce_date=announce_dt,
                    title=item['disclosure_title'],
                    pdf_url=item['disclosure_pdf_url'],
                    web_url=item['disclosure_url'],
                    status="PENDING" # Gemini処理待ち状態にする
                )

                # 重複チェック (UniqueConstraintがあるが、Python側でも確認すると丁寧)
                exists = db.query(Disclosure).filter_by(
                    stock_code=new_disclosure.stock_code,
                    title=new_disclosure.title,
                    announce_date=new_disclosure.announce_date
                ).first()

                if not exists:
                    print(f"Adding to DB: {new_disclosure.title}")
                    db.add(new_disclosure)
                else:
                    print(f"Skipping duplicate: {new_disclosure.title}")
            
            db.commit() # まとめて保存
            print(f"{len(my_stock_disclosure_info_json)} updated.")

        except Exception as e:
            print(f"DB Error: {e}")
            db.rollback() # エラー時はロールバック
        finally:
            db.close()