import os
import json
import time
import pandas as pd
import gspread
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
# ★修正: URLでもIDでも動くように open_by_url を使うようコード側を変えました
SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1H2TiCraNjMNoj3547ZB78nQqrdfbfk2a0rMLSbZBE48/edit?gid=1577246928#gid=1577246928'
SHEET_NAME = 'シート1'
TARGET_URL = "https://asp1.six-pack.xyz/admin/report/ad/list"

def main():
    print("=== 処理開始 ===")
    
    # Chrome設定
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080') # 画面サイズを確保
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # --- 1. Basic認証URLの作成 ---
        safe_user = quote(USER_ID, safe='')
        safe_pass = quote(PASSWORD, safe='')
        url_body = TARGET_URL.replace("https://", "").replace("http://", "")
        auth_url = f"https://{safe_user}:{safe_pass}@{url_body}"
        
        print(f"アクセス中: {TARGET_URL}")
        driver.get(auth_url)
        time.sleep(5)
        
        # --- 2. ログイン成功確認 (ログ用) ---
        print(f"現在のページタイトル: {driver.title}")
        print(f"現在のURL: {driver.current_url}")

        if "401" in driver.title or "Unauthorized" in driver.page_source:
            print("【失敗】認証に失敗しました。ID/PASSが間違っているか、サイトがこの方式をブロックしています。")
            return

        # --- 3. データ取得 ---
        # まずは「きれいな表」があるか探す
        dfs = pd.read_html(driver.page_source)
        data_to_upload = []

        if len(dfs) > 0:
            print(f"テーブルタグを {len(dfs)} 件発見。きれいな表として取得します。")
            df = dfs[0].fillna("")
            data_to_upload = [df.columns.values.tolist()] + df.values.tolist()
        else:
            print("テーブルタグが見つかりません。「Ctrl+A」モードでテキスト全文を取得します。")
            # bodyタグの中身をテキストとして全部取得
            body_text = driver.find_element(By.TAG_NAME, "body").text
            # 改行で区切ってリストにする（A列に縦に並べるイメージ）
            rows = body_text.split('\n')
            data_to_upload = [[row] for row in rows]
            
            if not data_to_upload:
                print("【警告】画面上にテキストが何も見つかりませんでした。")

        # --- 4. スプレッドシートへ書き込み ---
        if data_to_upload:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
            client = gspread.authorize(creds)
            
            # URLから直接開く方式に変更（これで変なエラーが消えます）
            sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)
            
            sheet.clear()
            sheet.update(data_to_upload)
            print("=== 更新完了！スプレッドシートを確認してください ===")
        else:
            print("=== データが空のため、更新をスキップしました ===")

    except Exception as e:
        print(f"【エラー発生】: {e}")
        # 詳細なエラー情報を出す
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
