from flask import Flask, send_from_directory, render_template, request, redirect, url_for, make_response, jsonify
import os
import requests
from bs4 import BeautifulSoup
from main import FrontendClass

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
        # 状態維持用のパラメータを取得
        keep_sort = request.form.get("keep_sort", "stock_code")
        keep_order = request.form.get("keep_order", "asc")
        keep_group = request.form.get("keep_group")
        # DBへの登録処理を実行 (main.pyに追加するメソッド)
        print("start frontend_app.register_stock")
        frontend_app.register_stock(stock_code, stock_name, number, average_price, target_sell_price, target_buy_price, remarks, group)
        # 空文字の場合は None に戻す（url_for でパラメータを除外するため）
        if keep_group == "":
            keep_group = None
        return redirect(url_for('index', sort=keep_sort, order=keep_order, group_filter=keep_group))
    
    # デフォルトは stock_code の 昇順 (asc)
    sort_by = request.args.get("sort", "stock_code")
    order = request.args.get("order", "asc")
    group_filter = request.args.get("group_filter", "holdings")
    stock_contents, summary = frontend_app.get_my_stocks(sort_by, order, group_filter)
    
    # グラフ用データの取得
    graph_data = frontend_app.get_graph_data()

    response = make_response(render_template(
        "index.html", 
        stock_contents=stock_contents,
        summary=summary,
        current_sort=sort_by,
        current_order=order,
        current_group=group_filter,
        graph_data=graph_data
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
