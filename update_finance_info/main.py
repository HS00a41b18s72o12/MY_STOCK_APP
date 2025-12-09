import time
import jpholiday
import yfinance as yf
from datetime import datetime
from sqlalchemy.orm import Session
from common.database import engine, SessionLocal
from common.models import Stock, MarketData

class FinanceUpdater:
    def __init__(self):
        # 起動時に一度だけ実行（コンテナ再起動時などに即反映させるため）
        self.check_new_stocks()

    def get_stock_data_from_yfinance(self, code):
        """yfinanceからデータを取得するヘルパー関数"""
        stock_exchange_code = ['T', 'N', 'F', 'S']
        for exchange_code in stock_exchange_code:
            try:
                # 日本株の場合は .T をつける必要がある
                ticker_symbol = f"{code}.{exchange_code}"
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info
                current_price = info.get('currentPrice')
                previous_price = info.get('previousClose')
                dividend_amount = info.get('dividendRate')
                per = None if info.get('trailingPE') is None else round(info.get('trailingPE'), 2)
                pbr = None if info.get('priceToBook') is None else round(info.get('priceToBook'), 2)
                # データがない場合は次の取引所コードを試す    
                if current_price is None and previous_price is None:
                    print(f"No price data for {ticker_symbol}, trying next exchange.")
                    continue  
                # 取得できない場合は None が返ることもあるので注意
                return {
                    "current_price": current_price,
                    "previous_price": previous_price,
                    "dividend_amount": dividend_amount,
                    "per": per,
                    "pbr": pbr,
                }
            except Exception as e:
                print(f"Error fetching {ticker_symbol}: {e}")
                continue
        # どの取引所にも存在しない場合、初期値を返す
        return {
            "current_price": 0,
            "previous_price": 0,
            "dividend_amount": 0,
            "per": 0,
            "pbr": 0,
        }

    def check_new_stocks(self):
        """
        新規追加された（MarketDataがまだない）銘柄を探して更新する
        """
        db: Session = SessionLocal()
        try:
            # SQL: Stockテーブルにあるが、MarketDataテーブルにレコードがない銘柄を探す
            # (LEFT JOIN して market_data が NULL のものを抽出)
            new_stocks = db.query(Stock).outerjoin(
                MarketData, Stock.stock_code == MarketData.stock_code
            ).filter(
                MarketData.stock_code == None
            ).all()

            if new_stocks:
                print(f"Found {len(new_stocks)} new stocks. Updating...")
                for stock in new_stocks:
                    self._update_single_stock(db, stock.stock_code)
                db.commit()
            # else:
            #    print("No new stocks found.") 

        except Exception as e:
            print(f"Error in check_new_stocks: {e}")
            db.rollback()
        finally:
            db.close()

    def update_all_stocks_daily(self):
        """
        【日次バッチ】全銘柄の情報を更新する
        """
        # 祝日だった場合、処理を行わない
        if self.check_holiday():
            print("Today is holiday, quit process")
            return None
        print("Starting daily update...")
        db: Session = SessionLocal()
        try:
            stocks = db.query(Stock).all()
            for stock in stocks:
                self._update_single_stock(db, stock.stock_code)
                time.sleep(1) # API制限考慮で少し待つ
            db.commit()
            print("Daily update completed.")
        except Exception as e:
            print(f"Error in daily update: {e}")
            db.rollback()
        finally:
            db.close()

    def _update_single_stock(self, db: Session, code: str):
        """個別の銘柄を更新・保存する共通処理"""
        data = self.get_stock_data_from_yfinance(code)
        if not data:
            return

        print(f"Updating {code}: {data['current_price']} JPY")

        # MarketDataを取得、なければ作成
        market_data = db.query(MarketData).filter(MarketData.stock_code == code).first()
        if not market_data:
            market_data = MarketData(stock_code=code)
            db.add(market_data)

        # データの反映
        market_data.current_price = data["current_price"]
        market_data.previous_price = data["previous_price"]
        market_data.dividend_amount = data["dividend_amount"]
        market_data.per = data["per"]
        market_data.pbr = data["pbr"]

    def check_holiday(self):
        today = datetime.today()
        if jpholiday.is_holiday(today):
            return True
        else:
            return False