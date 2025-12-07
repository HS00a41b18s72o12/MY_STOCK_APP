import jpholiday
from datetime import datetime

def get_my_stock_disclosure_info(todays_stock_disclosure_info_json, my_stock_info_list):
    my_stock_disclosure_info_json = []
    for stock_info in todays_stock_disclosure_info_json:
        if stock_info['stock_code'] in my_stock_info_list:
            my_stock_disclosure_info_json.append({
                    "announce_time": stock_info['announce_time'],
                    "stock_code": stock_info['stock_code'],
                    "company_name": stock_info['company_name'],
                    "disclosure_title": stock_info['disclosure_title'],
                    "disclosure_url": stock_info['disclosure_url']
                })
    return my_stock_disclosure_info_json

def create_stock_disclosure_url(base_url, current_date):
    current_year = current_date.tm_year
    current_month = current_date.tm_mon
    current_day = current_date.tm_mday
    stock_disclosure_url = base_url.replace("yyyy", str(current_year)).replace("mm", f"{current_month:02}").replace("dd", f"{current_day:02}")
    return stock_disclosure_url

def check_holiday():
    today = datetime.today()
    if jpholiday.is_holiday(today):
        return True
    else:
        return False

def filter_disclosure_by_keyword(todays_stock_disclosure_info_json, search_keywords):
    if not search_keywords:
        return
    keywords = search_keywords.split(",")

    # フィルタリング処理
    filtered_list = [
        item for item in todays_stock_disclosure_info_json
        if any(keyword in item["disclosure_title"] for keyword in keywords)
    ]
    return filtered_list