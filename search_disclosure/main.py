import os
import csv
import time
import datetime
import glob
from sqlalchemy.orm import Session

from functions import browser
from functions import common
from common.database import engine, SessionLocal, Base
from common.models import Stock, Disclosure, MarketData

class DisclosureClass:
    def __init__(self):
        self.selenium_url = os.environ.get("SELENIUM_URL")
        self.stock_disclosure_url = os.environ.get("SEARCH_DISCLOSURE_URL")
        self.database_url = os.environ.get("DATABASE_URL")
        self.search_keyword = os.environ.get("SEARCH_KEYWORD")
        # DB接続準備
        # テーブルが存在しなければ作成する
        Base.metadata.create_all(bind=engine)
        # ダミーデータ投入
        self._insert_dummy_stock_data()

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
    開発用に監視対象銘柄をDBに入れる
    """
    def _insert_dummy_stock_data(self):
        """
        DBのStockテーブルが空の場合、CSVファイルから初期データを投入する
        """
        db = SessionLocal()
        try:
            # === 特定のMarketDataを削除する処理 ===
            # target_code = "2928"
            # bad_data = db.query(MarketData).filter(MarketData.stock_code == target_code).first()
            # if bad_data:
            #     print(f"Deleting incorrect MarketData for {target_code}...")
            #     db.delete(bad_data)
            #     db.commit()
            #     print("Deletion completed.")

            # === 初期データ取り込み処理 ===
            # CSVファイルのパス (コンテナ内のパス: /app/dummy_data/dummy_data.csv)
            # 実行スクリプト(main.py)からの相対パスで指定
            csv_folder = os.path.join(os.path.dirname(__file__), 'dummy_data')
            stocks_csv_path = glob.glob(os.path.join(csv_folder, 'stocks*.csv'))[0]
            market_data_csv_path = glob.glob(os.path.join(csv_folder, 'market_data*.csv'))[0]
            disclosures_csv_path = glob.glob(os.path.join(csv_folder, 'disclosures*.csv'))[0]
            # stocks
            if db.query(Stock).count() > 0:
                print(f"stocks data exists")
            elif not os.path.exists(stocks_csv_path):
                print(f"CSV file not found at: {stocks_csv_path}")
            else:
                print("Stock table is empty. Starting import from CSV...")
                new_stocks = []
                # CSV読み込み (エンコーディングはutf-8推奨)
                with open(stocks_csv_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 空文字のクリーニング (CSVの ,, は空文字 "" になるため None に変換)
                        remarks = row.get('remarks')
                        remarks = remarks if remarks else None
                        
                        group = row.get('group')
                        group = group if group else None

                        # 数値変換 (空文字の場合は0にする安全策)
                        number_str = row.get('number', '0')
                        number = int(number_str) if number_str else 0
                        
                        price_str = row.get('average_price', '0')
                        price = float(price_str) if price_str else 0.0

                        stock = Stock(
                            stock_code=row['stock_code'],
                            stock_name=row['stock_name'],
                            number=number,
                            average_price=price,
                            remarks=remarks,
                            group=group
                        )
                        new_stocks.append(stock)
                if new_stocks:
                    db.add_all(new_stocks)
                    db.commit()
                    print(f"Successfully imported {len(new_stocks)} stocks from CSV.")
                else:
                    print("CSV file was empty.")

            # market_data
            if db.query(MarketData).count() > 0:
                print(f"market_data data exists")
            elif not os.path.exists(market_data_csv_path):
                print(f"CSV file not found at: {market_data_csv_path}")
            else:
                print("MarketData table is empty. Starting import from CSV...")
                new_market_data = []
                # CSV読み込み (エンコーディングはutf-8推奨)
                with open(market_data_csv_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 数値変換 (空文字の場合は0にする安全策)
                        current_price_str = row.get('current_price', '0.0')
                        current_price = float(current_price_str) if current_price_str else 0.0
                        previous_price_str = row.get('previous_price', '0.0')
                        previous_price = float(previous_price_str) if previous_price_str else 0.0
                        dividend_amount_str = row.get('dividend_amount', '0.0')
                        dividend_amount = float(dividend_amount_str) if dividend_amount_str else 0.0
                        per_str = row.get('per', '0.0')
                        per = float(per_str) if per_str else 0.0
                        pbr_str = row.get('pbr', '0.0')
                        pbr = float(pbr_str) if pbr_str else 0.0
                        
                        market_data = MarketData(
                            stock_code=row['stock_code'],
                            current_price=current_price,
                            previous_price=previous_price,
                            dividend_amount=dividend_amount,
                            per=per,
                            pbr=pbr
                        )
                        new_market_data.append(market_data)
                if new_market_data:
                    db.add_all(new_market_data)
                    db.commit()
                    print(f"Successfully imported {len(new_market_data)} market_data from CSV.")
                else:
                    print("CSV file was empty.")


            # disclosures
            if db.query(Disclosure).count() > 0:
                print(f"disclosures data exists")
            elif not os.path.exists(disclosures_csv_path):
                print(f"CSV file not found at: {disclosures_csv_path}")
            else:
                print("Disclosure table is empty. Starting import from CSV...")
                new_disclosures = []
                # CSV読み込み (エンコーディングはutf-8推奨)
                with open(disclosures_csv_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    now = datetime.datetime.now()
                    for row in reader:
                        # 空文字のクリーニング (CSVの ,, は空文字 "" になるため None に変換)
                        title = row.get('title')
                        title = title if title else None
                        pdf_url = row.get('pdf_url')
                        pdf_url = pdf_url if pdf_url else None
                        web_url = row.get('web_url')
                        web_url = web_url if web_url else None
                        summary = row.get('summary')
                        summary = summary if summary else None
                        sales_growth = row.get('sales_growth')
                        sales_growth = sales_growth if sales_growth else None
                        profit_growth = row.get('profit_growth')
                        profit_growth = profit_growth if profit_growth else None
                        status = row.get('status')
                        status = status if status else None

                        # 時刻
                        announce_date = row.get('announce_date', now.replace(hour=0, minute=0, second=0, microsecond=0))
                        disclosures = Disclosure(
                            stock_code=row['stock_code'],
                            announce_date=announce_date,
                            title=title,
                            pdf_url=pdf_url,
                            web_url=web_url,
                            summary=summary,
                            sales_growth=sales_growth,
                            profit_growth=profit_growth,
                            status=status
                        )
                        new_disclosures.append(disclosures)
                if new_disclosures:
                    db.add_all(new_disclosures)
                    db.commit()
                    print(f"Successfully imported {len(new_disclosures)} disclosures from CSV.")
                else:
                    print("CSV file was empty.")

        except Exception as e:
            print(f"Error importing CSV: {e}")
            db.rollback()
        finally:
            db.close()

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