from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from common.database import Base

# 1. ユーザー保有株情報
class Stock(Base):
    __tablename__ = "stocks"
    # カラム定義
    stock_code = Column(String(10), primary_key=True, index=True)                      # 銘柄コード
    stock_name = Column(String(255))                                                   # 銘柄名
    number = Column(Integer, default=0)                                                # 保有株数
    average_price = Column(Float, default=0.0)                                         # 取得単価
    target_sell_price = Column(Float, nullable=True)                                   # 目標売却価格
    target_buy_price = Column(Float, nullable=True)                                    # 目標購入価格
    last_notice_date = Column(DateTime, nullable=True)                                 # 最後通知送信日
    remarks = Column(String(255))                                                      # メモ
    group = Column(String(10))                                                         # グループ
    created_at = Column(DateTime(timezone=True), server_default=func.now())                      # 作成日時
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()) # 更新日時
    # リレーション定義 (1:1) StockとMarketDataは 1:1 の関係
    market_data = relationship("MarketData", back_populates="stock", uselist=False, cascade="all, delete-orphan")
    # リレーション定義 (1:N) StockとDisclosureは 1:N の関係
    disclosures = relationship("Disclosure", back_populates="stock", cascade="all, delete-orphan")


# 2. 市況・財務情報
class MarketData(Base):
    __tablename__ = "market_data"
    # カラム定義
    stock_code = Column(String(10), ForeignKey("stocks.stock_code"), primary_key=True)           # 銘柄コード
    current_price = Column(Float, nullable=True)                                                 # 現在値
    previous_price = Column(Float, nullable=True)                                                # 前日終値
    dividend_amount = Column(Float, nullable=True)                                               # 1株あたり配当金(円)
    per = Column(Float, nullable=True)                                                           # PER
    pbr = Column(Float, nullable=True)                                                           # PBR
    created_at = Column(DateTime(timezone=True), server_default=func.now())                      # 作成日時
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()) # 更新日時

    # リレーション
    stock = relationship("Stock", back_populates="market_data")


# 3. 適時開示・AI分析結果 (Search Disclosure & Analyze Batch)
class Disclosure(Base):
    __tablename__ = "disclosures"
    # カラム定義
    id = Column(Integer, primary_key=True, index=True)                                           # ID
    stock_code = Column(String(10), ForeignKey("stocks.stock_code"), nullable=False)                   # 銘柄コード
    announce_date = Column(DateTime, nullable=False)                                             # 開示日時
    title = Column(String(512), nullable=False)                                                  # タイトル
    pdf_url = Column(String(512))                                                                # PDFファイルURL
    web_url = Column(String(512))                                                                # 開示WebページURL
    summary = Column(Text, nullable=True)                                                        # 決算要約
    sales_growth = Column(String(50), nullable=True)                                             # 売上高増減(増収/減収)
    profit_growth = Column(String(50), nullable=True)                                            # 純利益増減(増益/減益)
    status = Column(String(20), default="PENDING")                                               # AI処理状態
    created_at = Column(DateTime(timezone=True), server_default=func.now())                      # 作成日時
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()) # 更新日時

    # 重複防止
    __table_args__ = (
        UniqueConstraint('stock_code', 'announce_date', 'title', name='uix_disclosure_unique'),
    )

    # リレーション
    stock = relationship("Stock", back_populates="disclosures")