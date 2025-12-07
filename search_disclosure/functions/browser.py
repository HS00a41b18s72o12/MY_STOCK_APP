import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException

def open_browser(selenium_url, headless_mode):
    max_retries = 5
    for i in range(max_retries):
        try:
            options = Options()
            if headless_mode:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-logging")
            
            driver = webdriver.Remote(
                command_executor=selenium_url,
                options=options
            )
            return driver
        except WebDriverException:
            print(f"retrying ({i+1}/{max_retries})")
            time.sleep(2)

def get_todays_stock_disclosure_info(driver, stock_disclosure_url):
    results = []
    for i in range(10):
        stock_disclosure_url_added_page_num =  stock_disclosure_url + str(i + 1)
        driver.get(stock_disclosure_url_added_page_num)
        try:
            if driver.find_elements(By.CSS_SELECTOR, 'body div.alert.alert-warning'):
                break
            rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            for row in rows:
                columns = row.find_elements(By.TAG_NAME, "td")
                if len(columns) >= 3:
                    announce_time = columns[0].text.strip()
                    stock_code = columns[1].text.strip()
                    company_name = columns[2].text.strip()
                    disclosure_title = columns[3].text.strip()
                    # disclosure_url の取得
                    disclosure_link = columns[3].find_element(By.TAG_NAME, "a")
                    disclosure_url = disclosure_link.get_attribute("href").strip()  # href属性
                    results.append({
                        "announce_time": announce_time,
                        "stock_code": stock_code,
                        "company_name": company_name,
                        "disclosure_title": disclosure_title,
                        "disclosure_url": disclosure_url
                    })
        except Exception as e:
            print(f"Error retrieving stock information: {e}")
            break
        time.sleep(1)
    return results

def get_disclosure_pdf_info(driver, my_stock_disclosure_info_json):
    ret_json = []
    for stock_info in my_stock_disclosure_info_json:
        new_stock_info = stock_info.copy()
        disclosure_url = stock_info['disclosure_url']
        
        driver.get(disclosure_url)
        try:
            # "disclosure-info" クラス内の "download" 属性を持つ aタグ が現れるのを最大10秒待つ
            # CSSセレクタの意味: <ul class="disclosure-info"> の中にある <a download="..."> 要素
            pdf_link_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.disclosure-info a[download]"))
            )
            # href属性（PDFのURL）を取得
            pdf_url = pdf_link_elem.get_attribute("href")
            new_stock_info['disclosure_pdf_url'] = pdf_url
        except TimeoutException:
            print(f"PDF link not found for: {disclosure_url}")
            new_stock_info['disclosure_pdf_url'] = None
        except Exception as e:
            print(f"Error accessing {disclosure_url}: {e}")
            new_stock_info['disclosure_pdf_url'] = None
            
        ret_json.append(new_stock_info)
    return ret_json