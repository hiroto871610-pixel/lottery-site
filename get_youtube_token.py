import os
import google_auth_oauthlib.flow
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ステップ2でダウンロードしたファイルの名前
CLIENT_SECRETS_FILE = "client_secret.json"
# 今回要求する権限（YouTubeへのアップロード権限）
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"]

def main():
    print("🔄 ブラウザを開いてYouTubeアカウントの認証を行います...")
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES)
    
    # ここでローカルサーバーを立ち上げ、自動的にブラウザが開きます
    credentials = flow.run_local_server(port=0)

    # 認証に成功したら、その「許可証」を token.json として保存！
    with open("token.json", "w") as token_file:
        token_file.write(credentials.to_json())
    
    print("✅ 認証成功！『token.json』が作成されました！")
    print("⚠️ 注意: この client_secret.json と token.json は絶対にGitHubに公開しないでください！")

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    main()