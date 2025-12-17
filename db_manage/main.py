from sqlalchemy.orm import Session
from common.database import SessionLocal
from common.models import Stock, Disclosure, MarketData
from common.database import engine, SessionLocal, Base

import os
import csv
import glob
import datetime

class DbBackuper:
    def __init__(self):
        # DB接続準備
        # テーブルが存在しなければ作成する
        Base.metadata.create_all(bind=engine)

    def backup(self):
        """
        Stock, MarketData, Disclosure テーブルの内容をCSVとしてバックアップする
        保存先: analyze_finance_report/backups/
        """
        print("Backing up the database...")
        db: Session = SessionLocal()
        try:
            # 1. 保存先ディレクトリの作成 (なければ作る)
            # コンテナ内の /app/backups に保存されます
            # ホスト側では my-stock-app/analyze_finance_report/backups になります
            backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
            os.makedirs(backup_dir, exist_ok=True)

            # 2. ファイル名用のタイムスタンプ (例: 20251215_193000)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

            # 3. バックアップ対象の定義 (モデルクラス, ファイル名のプレフィックス)
            targets = [
                (Stock, "stocks"),
                (MarketData, "market_data"),
                (Disclosure, "disclosures")
            ]
            print(f"Starting database backup to {backup_dir} ...")
            for model_class, prefix in targets:
                # 全データを取得
                records = db.query(model_class).all()
                # ファイルパス作成
                filename = f"{prefix}_{timestamp}.csv"
                filepath = os.path.join(backup_dir, filename)
                # カラム名（ヘッダー）を動的に取得
                # SQLAlchemyのモデル定義からカラム名のリストを取り出します
                columns = model_class.__table__.columns.keys()
                with open(filepath, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # ヘッダー書き込み
                    writer.writerow(columns)
                    # データ書き込み
                    for record in records:
                        # 各カラムの値を取り出してリストにする
                        row = [getattr(record, col) for col in columns]
                        writer.writerow(row)
                print(f"Saved: {filename} ({len(records)} records)")
            print("Data backup completed successfully.")
        except Exception as e:
            print(f"Error during data backup: {e}")
        finally:
            db.close()

    def insert_dummy_data(self):
        """
        DBのStockテーブルが空の場合、CSVファイルから初期データを投入する
        """
        print("Inserting dummy data into the database...")
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
            # CSVファイルのパス (コンテナ内のパス: /app/dummy_data/stocks*.csv)
            # 実行スクリプト(main.py)からの相対パスで指定
            csv_folder = os.path.join(os.path.dirname(__file__), 'dummy_data')
            stocks_files = glob.glob(os.path.join(csv_folder, 'stocks*.csv'))
            market_files = glob.glob(os.path.join(csv_folder, 'market_data*.csv'))
            disclosures_files = glob.glob(os.path.join(csv_folder, 'disclosures*.csv'))

            # stocks
            if db.query(Stock).count() > 0:
                print(f"stocks data exists")
            elif not stocks_files:
                print(f"Stocks CSV file not found")
            else:
                stocks_csv_path = stocks_files[0]
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
            elif not market_files:
                print(f"MarketData CSV file not found")
            else:
                market_data_csv_path = market_files[0]
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
            elif not disclosures_files:
                print(f"Disclosures CSV file not found")
            else:
                disclosures_csv_path = disclosures_files[0]
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
                        announce_date_str = row.get('announce_date')
                        if announce_date_str:
                            try:
                                announce_date = datetime.datetime.strptime(announce_date_str, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                # フォーマットが合わない場合は現在時刻などで代替
                                print(f"Date parse error: {announce_date_str}")
                                announce_date = datetime.datetime.now()
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