import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Docker-composeで設定した環境変数を取得
DATABASE_URL = os.environ.get("DATABASE_URL")

# Engine作成
engine = create_engine(DATABASE_URL, echo=False) # echo=TrueにするとSQLがログに出ます

# Session作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Model定義の基底クラス
Base = declarative_base()

# DBセッションを取得する依存関係用関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
