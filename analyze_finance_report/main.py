import os
import io
import json
import time
import requests
import google.generativeai as genai
from pypdf import PdfReader
from sqlalchemy.orm import Session
from common.database import SessionLocal
from common.models import Disclosure

class FinanceAnalyzer:
    def __init__(self):
        # Gemini API設定
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash") # 高速・安価なモデル

    def run_analysis_batch(self):
        """
        バッチ処理のメインループ
        データがなくなるまで処理し続け、なくなってもしばらく待機してから終了する
        """
        print("Starting Analysis Batch...")
        empty_count = 0
        MAX_RETRIES = 30 # 10秒 * 30回 = 5分間データが来なければ終了

        while True:
            # 1. 未処理のデータを1件取得
            record = self._get_pending_record()
            
            if record:
                # データがあれば処理実行
                print(f"Processing: {record.title} ({record.stock_code})")
                try:
                    self._process_single_record(record)
                except Exception as e:
                    print(f"Error processing record {record.id}: {e}")
                    self._update_status(record.id, "ERROR")
                
                empty_count = 0 # カウントリセット
                time.sleep(2) # APIレートリミット考慮
            else:
                # データがない場合
                empty_count += 1
                print(f"No pending records. Waiting... ({empty_count}/{MAX_RETRIES})")
                
                if empty_count >= MAX_RETRIES:
                    print("Batch finished. Sleeping until next schedule.")
                    break
                time.sleep(10) # 10秒待機

    def _get_pending_record(self):
        db: Session = SessionLocal()
        try:
            # 古いものから順に1件取得
            return db.query(Disclosure).filter(Disclosure.status == "PENDING").order_by(Disclosure.created_at.asc()).first()
        finally:
            db.close()

    def _update_status(self, record_id, status):
        """エラー時などのステータス更新用"""
        db: Session = SessionLocal()
        try:
            record = db.query(Disclosure).filter(Disclosure.id == record_id).first()
            if record:
                record.status = status
                db.commit()
        finally:
            db.close()

    def _process_single_record(self, record_data):
        """PDF取得 -> 分析 -> DB更新の一連の流れ"""
        # DBセッションはここで新規作成（長時間トランザクション回避）
        db: Session = SessionLocal()
        try:
            # 再度インスタンスを取得（デタッチ状態回避のため）
            record = db.query(Disclosure).filter(Disclosure.id == record_data.id).first()
            if not record:
                return

            # PDFが取得できない場合の処理
            if not record.pdf_url:
                print(f"Skipping analysis (No PDF URL): {record.title}")
                # DONEにしておけば、画面には表示される（要約はないがリンクはある状態）
                # または "NO_PDF" というステータスを新設しても良い
                record.status = "NO_PDF" 
                record.summary = "PDFを取得できませんでした。"
                db.commit()
                return
            
            # A. PDFダウンロード & テキスト抽出
            pdf_text = self._extract_text_from_pdf(record.pdf_url)
            if not pdf_text:
                print("Failed to extract text.")
                record.status = "ERROR"
                db.commit()
                return

            # B. Geminiで分析
            analysis_result = self._analyze_with_gemini(record.stock_code, record.title, pdf_text)
            
            # C. 結果をDBに保存
            if analysis_result:
                record.summary = analysis_result.get("summary", "")
                record.sales_growth = analysis_result.get("sales_growth", "-")
                record.profit_growth = analysis_result.get("profit_growth", "-")
                record.status = "DONE"
            else:
                record.status = "ERROR"
            
            db.commit()

        except Exception as e:
            print(f"Error in _process_single_record: {e}")
            db.rollback()
            raise e
        finally:
            db.close()

    def _extract_text_from_pdf(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            with io.BytesIO(response.content) as f:
                reader = PdfReader(f)
                text = ""
                # 決算短信のサマリーは通常1ページ目（多くても2ページ目）にあるため
                # 全ページ読むとトークン消費が激しいので、先頭2ページだけ抽出する
                max_pages = min(len(reader.pages), 2)
                for i in range(max_pages):
                    text += reader.pages[i].extract_text()
            return text
        except Exception as e:
            print(f"PDF Download Error: {e}")
            return None

    def _analyze_with_gemini(self, code, title, text):
        """タイトルに応じてプロンプトを切り替え、Geminiで分析する"""
        
        # 1. タイトル判定してプロンプトを作成
        if "決算短信" in title:
            prompt = self._create_earnings_prompt(code, title, text)
            analysis_type = "earnings"
        elif "株主優待" in title:
            prompt = self._create_benefits_prompt(code, title, text)
            analysis_type = "benefits"
        else:
            # その他の開示（デフォルト）
            prompt = self._create_default_prompt(code, title, text)
            analysis_type = "other"

        try:
            response = self.model.generate_content(prompt)
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            result_json = json.loads(cleaned_text)

            # 2. 結果の正規化
            # どのプロンプトを使ってもDBに入れられる形（辞書）に整える
            return {
                "summary": result_json.get("summary", "要約できませんでした"),
                # 決算以外は "-" をデフォルト値にする
                "sales_growth": result_json.get("sales_growth", "-"),
                "profit_growth": result_json.get("profit_growth", "-")
            }

        except Exception as e:
            print(f"Gemini API Error ({analysis_type}): {e}")
            # エラー時もNoneではなくエラーメッセージ入り辞書を返すとDB更新しやすい（お好みで）
            return None

# --- 以下、プロンプト生成用メソッド ---

    def _create_earnings_prompt(self, code, title, text):
        """決算短信用のプロンプト"""
        return f"""
        あなたは証券アナリストです。以下の「決算短信」から重要な情報を抽出してください。
        
        対象銘柄: {code}
        タイトル: {title}
        
        以下の3つの情報を抽出し、JSON形式でのみ出力してください。
        
        1. summary: 開示内容の要約（200文字以内。増収増益などの業績変化や、配当の変更点など核心部分）
        2. sales_growth: 売上高の増減率（例: "+10.5%", "△5.2%", "-"）。記載がなければ"-"
        3. profit_growth: 最終利益（親会社株主に帰属する当期純利益）の増減率（例: "+20.0%", "-"）。記載がなければ"-"

        テキスト:
        {text}
        """

    def _create_benefits_prompt(self, code, title, text):
        """株主優待用のプロンプト"""
        return f"""
        あなたは証券アナリストです。以下の「株主優待」に関する開示情報から重要な情報を抽出してください。
        
        対象銘柄: {code}
        タイトル: {title}
        
        以下の情報を抽出し、JSON形式でのみ出力してください。
        ※株主優待に関するニュースなので、売上や利益の増減率は不要です。
        
        1. summary: 優待の内容と変更点の要約（200文字以内）。
           以下の点を明確に含めてください：
           - 変更の種類（新設 / 変更 / 廃止 / 再開 など）
           - 何がもらえるのか（QUOカード〇〇円分、カタログギフトなど）
           - 対象となる株主（100株以上、保有期間1年以上など）
        
        テキスト:
        {text}
        """

    def _create_default_prompt(self, code, title, text):
        """その他の開示用の汎用プロンプト"""
        return f"""
        あなたは証券アナリストです。以下の適時開示情報から重要な情報を抽出してください。
        
        対象銘柄: {code}
        タイトル: {title}
        
        以下の情報を抽出し、JSON形式でのみ出力してください。
        
        1. summary: 開示内容の要約（200文字以内）。投資家にとってどのような影響があるかを簡潔に。
        
        テキスト:
        {text}
        """