from sqlalchemy.orm import Session
import os

from common.database import engine, SessionLocal, Base
from common.models import Stock, Disclosure, MarketData

class FrontendClass:
    def __init__(self):
        self.selenium_url = os.environ.get("SELENIUM_URL")
        self.stock_disclosure_url = os.environ.get("SEARCH_DISCLOSURE_URL")
        self.database_url = os.environ.get("DATABASE_URL")
        self.search_keyword = os.environ.get("SEARCH_KEYWORD")

    def get_my_stocks(self,  sort_by="stock_code", order="asc", group_filter=None):
        db: Session = SessionLocal()
        try:
            stocks = db.query(Stock).all()
            
            ret_list = []
            for stock in stocks:
                # 1. MarketDataの取得 (1:1なのでそのままアクセス)
                market = stock.market_data # データがない場合は None になる

                # 2. 最新のDisclosureを1件だけ取得
                # Python側でソートして先頭を取る
                latest_disclosure = None
                if stock.disclosures:
                    latest_disclosure = sorted(stock.disclosures, key=lambda x: x.announce_date, reverse=True)[0]

                # 3. 計算項目の算出
                current_price = market.current_price if market else 0
                average_price = stock.average_price
                number = stock.number
                # 前日差分 = 現在値 - 前日終値
                price_diff = round((current_price - market.previous_price) if market and market.previous_price else 0, 2)
                # 前日比率 = (現在値 - 前日終値) / 前日終値 * 100
                price_diff_percent = round(((current_price - market.previous_price) / market.previous_price * 100) if market and market.previous_price and current_price else 0, 2)
                # 損益額 = (現在値 - 取得単価) * 株数
                profit_yen = round((current_price - average_price) * number if current_price else 0, 2)
                # 損益率 = (現在値 - 取得単価) / 取得単価 * 100
                profit_percent = round(((current_price - average_price) / average_price * 100) if average_price > 0 and current_price else 0, 2)
                # 一株あたり配当金
                dividend_amount = market.dividend_amount if market and market.dividend_amount else 0
                # 配当利回り(%) = (一株あたり配当金 / 現在値) * 100
                dividend_yield_percent = round((dividend_amount / current_price * 100) if current_price > 0 else 0, 2)
                # メモ
                remarks = stock.remarks if stock.remarks else "-"
                # グループ
                group = stock.group if stock.group else "-"
                # 辞書に詰める
                stock_data = {
                    # Stock
                    "stock_code": stock.stock_code,
                    "stock_name": stock.stock_name,
                    "number": stock.number,
                    "average_price": stock.average_price,
                    "remarks": remarks,
                    "group": group,

                    # MarketData
                    "current_price": current_price,
                    "price_diff": price_diff,
                    "price_diff_percent": price_diff_percent,
                    "profit_yen": profit_yen,
                    "profit_percent": profit_percent,
                    "dividend_amount": dividend_amount,
                    "dividend_yield_percent": dividend_yield_percent,
                    "per": market.per if market else "-",
                    "pbr": market.pbr if market else "-",
                    
                    # Disclosure
                    "announce_date": latest_disclosure.announce_date if latest_disclosure else "-",
                    "title": latest_disclosure.title if latest_disclosure else "-",
                    "pdf_url": latest_disclosure.pdf_url if latest_disclosure else "-",
                    "summary": latest_disclosure.summary if latest_disclosure else "-",
                    "sales_growth": latest_disclosure.sales_growth if latest_disclosure else "-",
                    "profit_growth": latest_disclosure.profit_growth if latest_disclosure else "-",
                }
                ret_list.append(stock_data)
            
            # === フィルタリング処理 ===
            if group_filter:
                if group_filter == "未分類":
                    # DBでNoneだったものは "-" になっているので、"-" を探す
                    ret_list = [x for x in ret_list if x["group"] == "-"]
                else:
                    # 指定されたグループと一致するものだけ残す
                    ret_list = [x for x in ret_list if x["group"] == group_filter]
            
            # === サマリー計算 (フィルタリング後のデータで計算) ===
            total_market_value = 0      # 時価総額合計
            total_cost = 0              # 取得額合計
            total_day_change_yen = 0    # 前日比(円)合計
            
            for item in ret_list:
                # 数値型であることを確認して計算
                num = item["number"]
                curr = item["current_price"]
                
                if num > 0 and curr > 0:
                    val = num * curr
                    cost = num * item["average_price"]
                    
                    total_market_value += val
                    total_cost += cost
                    
                    # 前日比(円) × 株数 を加算
                    total_day_change_yen += item["price_diff"] * num

            # トータル損益
            total_profit_yen = total_market_value - total_cost
            total_profit_percent = (total_profit_yen / total_cost * 100) if total_cost > 0 else 0
            
            # トータル前日比(%) = トータル前日差額 / (トータル時価総額 - トータル前日差額) * 100
            yesterday_total_val = total_market_value - total_day_change_yen
            total_day_change_percent = (total_day_change_yen / yesterday_total_val * 100) if yesterday_total_val > 0 else 0

            summary = {
                "market_value": round(total_market_value),
                "profit_yen": round(total_profit_yen),
                "profit_percent": round(total_profit_percent, 2),
                "day_change_yen": round(total_day_change_yen),
                "day_change_percent": round(total_day_change_percent, 2)
            }

            #  ===  ソート処理 ===
            # ソート用の値を安全に取り出す関数
            def sort_key(item):
                value = item.get(sort_by)
                
                # ハイフンやNoneの場合は、並び順の最後に来るように極端な値を返す
                if value is None or value == "-":
                    # 昇順なら無限大、降順なら無限小扱いにすると「データなし」が常に末尾に来る
                    return float('inf') if order == 'asc' else float('-inf')
                
                # 文字列のまま比較すべきカラム（銘柄コードなど）
                if sort_by in ["stock_code", "stock_name"]:
                    return str(value)
                
                # それ以外は数値として比較
                try:
                    return float(value)
                except ValueError:
                    return str(value)

            # ソート実行
            is_reverse = (order == "desc")
            ret_list.sort(key=sort_key, reverse=is_reverse)
            return ret_list, summary
        finally:
            db.close()

    def register_stock(self, stock_code, stock_name, number, average_price, remarks, group):
        """銘柄を登録または更新する"""
        db: Session = SessionLocal()
        try:
            # 既に同じ銘柄コードがあるか探す
            existing_stock = db.query(Stock).filter(Stock.stock_code == stock_code).first()
            # 入力値のクリーニング（空文字ならNoneにする）
            stock_name = stock_name if stock_name else None
            number = int(number) if number else None
            average_price = float(average_price) if average_price else None
            remarks = remarks if remarks else None
            group = group if group else None

            if existing_stock:
                # 更新 (Update)
                print(f"Update stock: {stock_code}")
                # 値が入っている場合のみ更新（空なら維持）
                if stock_name is not None:
                    existing_stock.stock_name = stock_name
                if number is not None:
                    existing_stock.number = number
                if average_price is not None:
                    existing_stock.average_price = average_price
                if remarks is not None:
                    existing_stock.remarks = remarks
                if group is not None:
                    existing_stock.group = group
            else:
                # 新規登録 (Insert)
                print(f"Insert new stock: {stock_code}")
                new_stock = Stock(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    number=int(number),
                    average_price=float(average_price),
                    remarks=remarks,
                    group=group
                )
                db.add(new_stock)
            
            db.commit()
        except Exception as e:
            print(f"Error registering stock: {e}")
            db.rollback()
        finally:
            db.close()

    def delete_stock(self, code):
        """銘柄とそれに関連する全データを削除する"""
        db: Session = SessionLocal()
        try:
            # 1. 削除対象のStockを取得
            stock = db.query(Stock).filter(Stock.stock_code == code).first()
            
            if stock:
                # 2. 親を削除（cascade設定により、market_dataとdisclosuresも自動削除される）
                db.delete(stock)
                db.commit()
                print(f"Deleted stock: {code}")
            else:
                print(f"Stock not found: {code}")
                
        except Exception as e:
            print(f"Error deleting stock: {e}")
            db.rollback()
        finally:
            db.close()