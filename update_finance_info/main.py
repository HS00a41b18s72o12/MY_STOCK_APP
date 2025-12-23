import time
import jpholiday
import yfinance as yf
from datetime import datetime, date
from sqlalchemy.orm import Session
from common.notification import send_gmail
from common.database import engine, SessionLocal
from common.models import Stock, MarketData, DailyAssetSnapshot, DailyGroupSnapshot

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
                sector = info.get('sector')
                eps = info.get('trailingEps')
                # ミックス係数 (PER * PBR)
                mix_coeff = None
                if per is not None and pbr is not None:
                    mix_coeff = per * pbr
                # 配当性向 (1株配当 / EPS * 100)
                # 利益のうちどれだけ配当に回しているか
                payout_ratio = None
                if dividend_amount is not None and eps is not None and eps > 0:
                    payout_ratio = (dividend_amount / eps) * 100
                # 黒字判定 (EPSがプラスなら黒字)
                is_profitable = False
                if eps is not None and eps > 0:
                    is_profitable = True
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
                    "sector": sector,
                    "eps": eps,
                    "mix_coefficient": mix_coeff,
                    "payout_ratio": payout_ratio,
                    "is_profitable": is_profitable
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
            "sector": None,
            "past_eps": None,
            "predict_eps": None,
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

    def update_all_stocks(self):
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
            # 資産履歴の記録
            self._record_daily_snapshot(db)
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
        market_data.sector = data["sector"]
        market_data.eps = data["eps"]
        market_data.mix_coefficient = data["mix_coefficient"]
        market_data.payout_ratio = data["payout_ratio"]
        market_data.is_profitable = data["is_profitable"]

        # 目標価格到達の通知判定
        # Stock情報を取得（目標価格を確認するため）
        stock = db.query(Stock).filter(Stock.stock_code == code).first()
        current_val = data["current_price"]
        if stock:
            # 今日の日付
            today = date.today()
            # 既に今日通知済みならスキップ (日付のみ比較)
            if stock.last_notice_date and stock.last_notice_date.date() == today:
                return
            # 通知判定
            should_notify = False
            msg_subject = ""
            msg_body = ""
            # 売り目標判定
            if stock.target_sell_price and current_val >= stock.target_sell_price:
                should_notify = True
                msg_subject = f"売り時通知: {stock.stock_name}"
                msg_body = f"{stock.stock_name} ({code}) の株価が {current_val}円 になりました。\n目標売値: {stock.target_sell_price}円 以上です。"
            # 買い目標判定
            elif stock.target_buy_price and current_val <= stock.target_buy_price:
                should_notify = True
                msg_subject = f"買い時通知: {stock.stock_name}"
                msg_body = f"{stock.stock_name} ({code}) の株価が {current_val}円 になりました。\n目標買値: {stock.target_buy_price}円 以下です。"
            # 通知実行
            if should_notify:
                send_gmail(msg_subject, msg_body)
                stock.last_notice_date = datetime.now()


    def _record_daily_snapshot(self, db: Session):
        today = date.today()
        # 既存データの確認・削除（再実行時のため）
        # ※Cascade設定のおかげで親を消せば子(GroupSnapshot)も消える
        existing = db.query(DailyAssetSnapshot).filter(DailyAssetSnapshot.date == today).first()
        if existing:
            db.delete(existing)
            db.commit() # 一旦削除を確定

        # 新規作成
        snapshot = DailyAssetSnapshot(date=today)
        
        # 集計用変数
        total_market = 0
        total_profit = 0
        group_agg = {} # {"長期保有": {"mv": 0, "pf": 0, "inv": 0}, ...}

        stocks = db.query(Stock).all()
        for stock in stocks:
            market = stock.market_data
            if market and market.current_price:
                # 数値計算
                current_val = int(stock.number * market.current_price)
                buy_val = int(stock.number * stock.average_price)
                profit = current_val - buy_val
                
                # 全体合計
                total_market += current_val
                total_profit += profit

                # グループ集計
                grp = stock.group if stock.group else "未分類"
                if grp not in group_agg:
                    group_agg[grp] = {"mv": 0, "pf": 0, "inv": 0}
                
                group_agg[grp]["mv"] += current_val
                group_agg[grp]["pf"] += profit
                group_agg[grp]["inv"] += (current_val - profit)

        # 親レコード設定
        snapshot.total_market_value = total_market
        snapshot.total_profit = total_profit
        snapshot.total_investment = total_market - total_profit
        
        db.add(snapshot)
        db.flush() # IDを発行させるためにflush

        # 子レコード(グループ別)作成
        for grp_name, data in group_agg.items():
            grp_snapshot = DailyGroupSnapshot(
                snapshot_id=snapshot.id,
                group_name=grp_name,
                market_value=data["mv"],
                profit=data["pf"],
                investment=data["inv"]
            )
            db.add(grp_snapshot)
        
        print(f"Recorded snapshot for {today}")

    def check_holiday(self):
        today = datetime.today()
        if jpholiday.is_holiday(today):
            return True
        else:
            return False