import os
import json
import time
import glob
import pandas as pd
import gspread
from datetime import datetime, timedelta, timezone # ← 【追加】日時を扱うライブラリ
from urllib.parse import quote
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- 環境変数 ---
USER_ID = os.environ["USER_ID"]
PASSWORD = os.environ["USER_PASS"]
json_creds = json.loads(os.environ["GCP_JSON"])

# --- 設定 ---
SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1H2TiCraNjMNoj3547ZB78nQqrdfbfk2a0rMLSbZBE48/edit'
SHEET_NAME = '当日_raw'
DATE_SHEET_NAME = '更新日' # ← 【追加】更新日を書き込むシート名
TARGET_URL = "https://asp1.six-pack.xyz/admin/report/ad/list"

def main():
    print("=== 処理開始 ===")
    
    # ダウンロード先のフォルダ設定
    download_dir = os.path.join(os.getcwd(), "downloads")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # Chrome設定
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # --- 1. ログイン ---
        safe_user = quote(USER_ID, safe='')
        safe_pass = quote(PASSWORD, safe='')
        url_body = TARGET_URL.replace("https://", "").replace("http://", "")
        auth_url = f"https://{safe_user}:{safe_pass}@{url_body}"
        
        print(f"アクセス中: {TARGET_URL}")
        driver.get(auth_url)
        time.sleep(5)

        # --- 2. CSVダウンロード ---
        try:
            print("「CSV生成」ボタンを探しています...")
            csv_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'CSV生成')]")
            csv_btn.click()
            print("ボタンをクリックしました。ダウンロード待機中...")
            
            time.sleep(5) 
            for i in range(10):
                files = glob.glob(os.path.join(download_dir, "*.csv"))
                if files:
                    break
                time.sleep(3)
                
            files = glob.glob(os.path.join(download_dir, "*.csv"))
            if not files:
                print("【エラー】CSVファイルがダウンロードされませんでした。")
                return
            
            csv_file_path = files[0]
            print(f"ダウンロード完了: {csv_file_path}")

        except Exception as e:
            print(f"ボタン操作エラー: {e}")
            return

        # --- 4. CSV読み込みとスプレッドシート更新 ---
        print("CSVデータを読み込んでいます...")
        
        try:
            df = pd.read_csv(csv_file_path, encoding='cp932')
        except:
            try:
                df = pd.read_csv(csv_file_path, encoding='utf-8')
            except:
                df = pd.read_csv(csv_file_path, encoding='utf-16')

        df = df.fillna("")
        data_to_upload = [df.columns.values.tolist()] + df.values.tolist()

        # スプレッドシート接続
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(SPREADSHEET_URL)
        
        # データ書き込み
        sheet = spreadsheet.worksheet(SHEET_NAME)
        sheet.clear()
        sheet.update(data_to_upload)
        print("=== データ更新完了 ===")

        # --- 5. 更新日時の書き込み（追加部分） ---
        print("更新日時を記録しています...")
        
        # JST (UTC+9) の現在時刻を取得
        JST = timezone(timedelta(hours=+9), 'JST')
        now = datetime.now(JST)
        
        # 指定の形式を作成: 更新日：mm/dd_hh:mm
        # (例: 更新日：12/24_15:30)
        timestamp_str = now.strftime("更新日：%m/%d_%H:%M")
        
        try:
            sheet_date = spreadsheet.worksheet(DATE_SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            # シートがなければ作成する
            print(f"シート「{DATE_SHEET_NAME}」を作成します")
            sheet_date = spreadsheet.add_worksheet(title=DATE_SHEET_NAME, rows=5, cols=5)
        
        # A1セルに書き込み
        sheet_date.update('A1', [[timestamp_str]])
        print(f"日時記録完了: {timestamp_str}")

    except Exception as e:
        print(f"【エラー発生】: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
