import os
import json
import time
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 環境変数から情報を取得（GitHub Secretsで設定したもの）
USER_ID = os.environ["USER_ID"]
PASSWORD = os.environ["USER_PASS"]
# JSONキーを復元
json_creds = json.loads(os.environ["GCP_JSON"])

# ★ここだけ書き換えてください★
SPREADSHEET_KEY = 'https://docs.google.com/spreadsheets/d/1H2TiCraNjMNoj3547ZB78nQqrdfbfk2a0rMLSbZBE48/edit?gid=113667273#gid=113667273' 
SHEET_NAME = 'シート1'
TARGET_URL = "https://asp1.six-pack.xyz/admin/report/ad/list"

def main():
    print("処理開始")
    
    # Chromeの設定（クラウド上で動かすための設定）
    options = Options()
    options.add_argument('--headless') # 画面を出さない
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # ログイン処理
        driver.get(TARGET_URL)
        time.sleep(3)
        
        # ログイン画面が表示された場合の処理
        # ※実際のHTMLに合わせて name="login_id" などを調整が必要かもしれません
        try:
            id_input = driver.find_element(By.NAME, "login_id") 
            pass_input = driver.find_element(By.NAME, "password")
            
            id_input.send_keys(USER_ID)
            pass_input.send_keys(PASSWORD)
            pass_input.submit()
            time.sleep(5)
        except:
            print("ログイン画面が見つからない、または既にログイン済み")

        # データ取得
        driver.get(TARGET_URL)
        time.sleep(5)
        
        dfs = pd.read_html(driver.page_source)
        if len(dfs) > 0:
            df = dfs[0].fillna("")
            
            # スプレッドシート接続
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
            client = gspread.authorize(creds)
            
            sheet = client.open_by_key(SPREADSHEET_KEY).worksheet(SHEET_NAME)
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            print("更新完了")
        else:
            print("テーブルが見つかりませんでした")

    except Exception as e:
        print(f"エラー: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
