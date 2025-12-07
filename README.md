# 持ち株管理リスト
## 概要
自分の保有銘柄リストを作成できるWebサイト  
## 構成
![fig](fig.svg)

## frontend 
コンテナ起動時に開始

## db
コンテナ起動時に開始

## Search Disclosure
平日19:10に開始(祝日除)

## Analyze FinReport
平日19:10に開始(祝日除)
※新規適時開示がある場合のみ処理実行

## update finance info
平日18:00に開始(祝日除)  
frontendから新規銘柄登録時に開始

## コマンド
```
docker-compose up --build
docker compose down
docker volume rm my-stock-app_db_data
```