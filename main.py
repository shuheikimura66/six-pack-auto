import os
import json
import time
import pandas as pd
import gspread
from urllib.parse import quote  # ★追加：記号などをURL用に変換する機能
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 環境変数から情報を取得
USER_ID = os.environ["USER_ID"]
PASSWORD = os.environ["USER_PASS"]
# JSONキーを復元
json_creds = json.loads(os.environ["GCP_JSON"])

# 設定
SPREADSHEET_KEY = 'あなたのスプレッドシートID' # ★ここだけあなたのIDのままで！
SHEET_NAME = 'シート1'
TARGET_URL = "https://asp1.six-pack.xyz/admin/report/ad/list"

def main():
    print("処理開始")
    
    # Chromeの設定
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # --- ★Basic認証用のURL作成とアクセス（ここが変わりました） ---
        
        # IDやパスワードに「@」などの記号が入っているとURLが壊れるので変換処理をします
        safe_user = quote(USER_ID, safe='')
        safe_pass = quote(PASSWORD, safe='')
        
        # "https://" を取り除いたURLの本体を取得
        url_body = TARGET_URL.replace("https://", "").replace("http://", "")
        
        # 認証情報付きのURLを作成: https://ID:PASS@URL... の形式にします
        auth_url = f"https://{safe_user}:{safe_pass}@{url_body}"
        
        print("認証付きURLでアクセスします...")
        driver.get(auth_url)
        
        # 読み込み待機（Basic認証はアクセスした瞬間にログイン完了しています）
        time.sleep(5)
        
        # --- データ取得処理 ---
        # 画面のHTMLを取得してテーブルを探す
        dfs = pd.read_html(driver.page_source)
        
        if len(dfs) > 0:
            print(f"{len(dfs)}個の表が見つかりました。最初の表を保存します。")
            df = dfs[0].fillna("")
            
            # スプレッドシート接続
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
            client = gspread.authorize(creds)
            
            sheet = client.open_by_key(SPREADSHEET_KEY).worksheet(SHEET_NAME)
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            print("更新完了！スプレッドシートを確認してください。")
        else:
            print("エラー: 画面内にテーブル(表)が見つかりませんでした。ログインは成功している可能性がありますが、ページの構造が予想と違うかもしれません。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
