from flask import Flask, send_from_directory, render_template, request, redirect, url_for, make_response, jsonify
import os
from main import FrontendClass
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
frontend_app = FrontendClass() 

# Fabicon route
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')
# エラー
@app.errorhandler(404)
def not_found_error(error):
    return render_template("error.html", message="ページが見つかりません (404)"), 404
@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html", message="サーバー内部エラーが発生しました (500)"), 500

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # フォームの入力を取得
        stock_code = request.form.get("stock_code")
        stock_name = request.form.get("stock_name")
        number = request.form.get("number")
        average_price = request.form.get("average_price")
        target_sell_price = request.form.get("target_sell_price")
        target_buy_price = request.form.get("target_buy_price")
        remarks = request.form.get("remarks")
        group = request.form.get("group")
        # DBへの登録処理を実行 (main.pyに追加するメソッド)
        print("start frontend_app.register_stock")
        frontend_app.register_stock(stock_code, stock_name, number, average_price, target_sell_price, target_buy_price, remarks, group)
        
        # 二重送信防止のためリダイレクトする
        return redirect(url_for('index'))
    
    # デフォルトは stock_code の 昇順 (asc)
    sort_by = request.args.get("sort", "stock_code")
    order = request.args.get("order", "asc")
    group_filter = request.args.get("group_filter", None)
    stock_contents, summary = frontend_app.get_my_stocks(sort_by, order, group_filter)
    response = make_response(render_template(
        "index.html", 
        stock_contents=stock_contents,
        summary=summary,
        current_sort=sort_by,
        current_order=order,
        current_group=group_filter
    ))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/delete", methods=["POST"])
def delete_stock():
    stock_code = request.form.get("stock_code")
    if stock_code:
        frontend_app.delete_stock(stock_code)
    return redirect(url_for('index'))

@app.route("/api/get_stock_name/<stock_code>", methods=["GET"])
def get_stock_name(stock_code):
    try:
        # Yahoo!ファイナンスのURL
        url = f"https://finance.yahoo.co.jp/quote/{stock_code}.T"
        # ページを取得
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 銘柄名は <h1> タグに入っていることが多い
            # サイトのデザイン変更でクラス名が変わる可能性がありますが、現時点ではこれで取れます
            name_element = soup.select_one("h1")
            
            if name_element:
                stock_name = name_element.text.strip()
                stock_name_replace = stock_name.replace("の株価・株式情報", "")
                return jsonify({"status": "success", "name": stock_name_replace})
        
        return jsonify({"status": "error", "message": "Not found"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
