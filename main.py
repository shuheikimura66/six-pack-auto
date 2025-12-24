import os
import json
import time
import glob
import pandas as pd
import gspread
from urllib.parse import quote
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
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
# 転記先のスプレッドシート
SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1H2TiCraNjMNoj3547ZB78nQqrdfbfk2a0rMLSbZBE48/edit'
SHEET_NAME = 'シート1'

# CSVを保存したいGoogleドライブのフォルダID
# URLが https://drive.google.com/drive/u/0/folders/1HaLB... の場合、末尾の記号部分です
DRIVE_FOLDER_ID = '1HaLB15qHhdf4r2oSGzyiqN_0Cswmnf3O'

# 対象サイト
TARGET_URL = "https://asp1.six-pack.xyz/admin/report/ad/list"

def main():
    print("=== 処理開始 ===")
    
    # ダウンロード先のフォルダ設定（現在の場所/downloads）
    download_dir = os.path.join(os.getcwd(), "downloads")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # Chrome設定（ダウンロード許可設定を追加）
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # ヘッドレスモードでのダウンロードを有効にする設定
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # --- 1. Basic認証URLでアクセス ---
        safe_user = quote(USER_ID, safe='')
        safe_pass = quote(PASSWORD, safe='')
        url_body = TARGET_URL.replace("https://", "").replace("http://", "")
        auth_url = f"https://{safe_user}:{safe_pass}@{url_body}"
        
        print(f"アクセス中: {TARGET_URL}")
        driver.get(auth_url)
        time.sleep(5) # ページ読み込み待機

        # --- 2. 「CSV生成」ボタンを探してクリック ---
        try:
            # "CSV生成" という文字を含む要素を探す（ボタンやリンク）
            print("「CSV生成」ボタンを探しています...")
            csv_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'CSV生成')]")
            csv_btn.click()
            print("ボタンをクリックしました。ダウンロード待機中...")
            
            # ダウンロード完了待ち（最大30秒）
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
            
            csv_file_path = files[0] # 見つかった最新のファイル
            print(f"ダウンロード完了: {csv_file_path}")

        except Exception as e:
            print(f"ボタンクリックまたはダウンロード中にエラー: {e}")
            return

        # --- 3. Googleドライブへのアップロード ---
        print("Googleドライブへアップロード中...")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {
            'name': os.path.basename(csv_file_path),
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(csv_file_path, mimetype='text/csv')
        drive_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"ドライブへの保存完了 (File ID: {drive_file.get('id')})")

        # --- 4. CSV読み込みとスプレッドシート更新 ---
        print("CSVデータを読み込んでいます...")
        
        # 文字コード判定（日本語CSVはShift-JISが多いが、UTF-8の場合もあるためトライする）
        try:
            df = pd.read_csv(csv_file_path, encoding='cp932') # Shift-JIS
        except:
            try:
                df = pd.read_csv(csv_file_path, encoding='utf-8')
            except:
                df = pd.read_csv(csv_file_path, encoding='utf-16')

        # NaN（空データ）を空文字に変換
        df = df.fillna("")
        
        # データ整形
        data_to_upload = [df.columns.values.tolist()] + df.values.tolist()

        # スプレッドシート書き込み
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)
        
        sheet.clear()
        sheet.update(data_to_upload)
        print("=== 更新完了！スプレッドシートを確認してください ===")

    except Exception as e:
        print(f"【エラー発生】: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
