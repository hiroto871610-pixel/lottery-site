import random
import numpy as np
import pandas as pd
import itertools
from sklearn.ensemble import RandomForestClassifier
import requests
from bs4 import BeautifulSoup
import re
import json
import os
import datetime
from collections import Counter
import tweepy  # ←追加：Xポスト用
import urllib3 # ←追加：エラー回避用
# ▼▼▼ 修正：必ず「環境変数を取得する前」に.envを読み込む！ ▼▼▼
from dotenv import load_dotenv
load_dotenv()
import base64
import urllib.request
from PIL import Image, ImageDraw, ImageFont
import time
import cloudinary
import cloudinary.uploader
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
# ▲▲▲ ここまで ▲▲▲

# =========================================================
# JSONBin API設定 (Numbers専用)
# =========================================================
JSONBIN_BIN_ID = os.environ.get("JSONBIN_BIN_ID_NUMBERS") # ナンバーズ用に変更
JSONBIN_API_KEY = os.environ.get("JSONBIN_API_KEY")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}" if JSONBIN_BIN_ID else ""

import time # リトライの待機用に追加

def load_history_from_jsonbin():
    if not JSONBIN_BIN_ID: return []
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    
    max_retries = 3  # 最大3回試行
    retry_delay = 5  # 失敗時に5秒待ってから再試行

    for attempt in range(max_retries):
        try:
            # タイムアウトは60秒でOK（保存側のputも同様に長くしてください）
            res = requests.get(JSONBIN_URL, headers=headers, timeout=60)
            
            if res.status_code == 200:
                return res.json().get('record', [])
            else:
                print(f"⚠️ JSONBin取得エラー (試行 {attempt + 1}/{max_retries}): {res.status_code}")
                # 500系のエラー（サーバー混雑）ならリトライの余地あり
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    raise SystemExit(f"🚨 JSONBin側のエラーにより、処理を強制終了しました: {res.text}")
                    
        except (requests.exceptions.RequestException, Exception) as e:
            print(f"⚠️ 通信エラー (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                # 3回失敗したらデータ保護のために終了
                raise SystemExit("🚨 3回連続で通信に失敗したため、データの安全を考慮し処理を強制終了しました。")

    return []

def save_history_to_jsonbin(data):
    if not JSONBIN_BIN_ID: return
    headers = {"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}
    try:
        requests.put(JSONBIN_URL, json=data, headers=headers)
    except Exception as e: print(f"保存エラー: {e}")

# .envファイルを読み込む
load_dotenv()
# ▲▲▲ ここまで追加 ▲▲▲

# =========================================================
# 💰 i-mobile 広告共通パーツ（ここなら全ての関数から使えます！）
# =========================================================
imobile_overlay = """
<div style="position:fixed; bottom:0;left:0;right:0;width:100%;background: rgba(0, 0, 0, 0.7); z-index:99998;text-align:center;transform:translate3d(0, 0, 0);">
    <div style="margin:auto;z-index:99999;" >
        <div id="im-6d4249806e284e54896bb6614d5ca6f5">
            <script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script>
            <script>(window.adsbyimobile=window.adsbyimobile||[]).push({pid:84847,mid:592460,asid:1929926,type:"banner",display:"inline",elementid:"im-6d4249806e284e54896bb6614d5ca6f5"})</script>
        </div>
    </div>
</div>
"""

imobile_ad2_pc = """
<div id="im-d34f87828c9740a7b9a62172425cfcfd">
  <script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script>
  <script>(window.adsbyimobile=window.adsbyimobile||[]).push({pid:84847,mid:592459,asid:1929931,type:"banner",display:"inline",elementid:"im-d34f87828c9740a7b9a62172425cfcfd"})</script>
</div>
"""

imobile_ad2_sp = """
<div id="im-c4e1d905d99e4087b6a8d79bcd575552">
  <script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script>
  <script>(window.adsbyimobile=window.adsbyimobile||[]).push({pid:84847,mid:592460,asid:1929935,type:"banner",display:"inline",elementid:"im-c4e1d905d99e4087b6a8d79bcd575552"})</script>
</div>
"""

imobile_ad3_pc = """
<div id="im-4465412234044af19505d01849472875">
  <script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script>
  <script>(window.adsbyimobile=window.adsbyimobile||[]).push({pid:84847,mid:592459,asid:1929933,type:"banner",display:"inline",elementid:"im-4465412234044af19505d01849472875"})</script>
</div>
"""

imobile_ad3_sp = """
<div id="im-111a4112bae54171b8c129433281c73c">
  <script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script>
  <script>(window.adsbyimobile=window.adsbyimobile||[]).push({pid:84847,mid:592460,asid:1929936,type:"banner",display:"inline",elementid:"im-111a4112bae54171b8c129433281c73c"})</script>
</div>
"""
# =========================================================

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HISTORY_FILE = 'history_numbers.json'

# =========================================================
# 𝕏 (旧Twitter) API設定（.envファイルから読み込むように変更）
# =========================================================
X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET")
THREADS_USER_ID = os.environ.get("THREADS_USER_ID")
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")

# ▼▼▼ ここから追加：LINE公式アカウント API設定 ▼▼▼
LINE_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

def post_to_line(message):
    """LINE公式アカウントへ一斉送信(ブロードキャスト)する機能"""
    if not LINE_ACCESS_TOKEN:
        print("⚠️ LINEのアクセストークンが.envファイルから取得できないため、LINE配信をスキップしました。")
        return

    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    data = {
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    
    try:
        res = requests.post(url, headers=headers, json=data)
        if res.status_code == 200:
            print("✅ LINEへの自動配信が成功しました！")
        else:
            print(f"❌ LINE配信エラー: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ LINE通信エラー: {e}")
# ▲▲▲ ここまで追加 ▲▲▲

def auto_refresh_threads_token():
    """Threadsのトークン期限を自動で延長（60日）し、.envを自己書き換えする自己修復機能"""
    global THREADS_ACCESS_TOKEN
    if not THREADS_ACCESS_TOKEN:
        return None

    print("🔄 Threadsのアクセストークンを自動更新（延命）しています...")
    url = f"https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token={THREADS_ACCESS_TOKEN}"
    try:
        res = requests.get(url)
        data = res.json()
        if "access_token" in data:
            new_token = data["access_token"]
            
            # 自分のパソコンの .env ファイルを自動で上書きする処理
            env_path = ".env"
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as file:
                    lines = file.readlines()
                
                with open(env_path, "w", encoding="utf-8") as file:
                    for line in lines:
                        if line.startswith("THREADS_ACCESS_TOKEN="):
                            file.write(f"THREADS_ACCESS_TOKEN={new_token}\n")
                        else:
                            file.write(line)

                            # ▼▼▼ ココを追加！ ▼▼▼
            # クラウド(GitHub Actions)環境で動いている場合は、システムに新しいトークンを伝達する
            if "GITHUB_ENV" in os.environ:
                with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as f:
                    f.write(f"NEW_THREADS_TOKEN={new_token}\n")
            # ▲▲▲ ここまで ▲▲▲
            
            print("✅ Threadsのトークン自動更新に成功し、.envを書き換えました！")
            THREADS_ACCESS_TOKEN = new_token # プログラム内の変数も最新に書き換え
            return new_token
        else:
            # 短期間に連続で更新しようとした場合などはスキップされる
            print("⚠️ トークンの更新は不要（または制限中）のためスキップしました。")
            return THREADS_ACCESS_TOKEN
    except Exception as e:
        print(f"❌ Threadsトークン更新エラー: {e}")
        return THREADS_ACCESS_TOKEN

# =========================================================
# Threads API設定
# =========================================================

def post_to_threads(message):
    """Threadsへ自動投稿する機能（2ステップ方式）"""
    # ★投稿する前に、毎回必ずトークンの寿命を60日に回復させる！
    auto_refresh_threads_token()

    if not all([THREADS_USER_ID, THREADS_ACCESS_TOKEN]):
        print("⚠️ ThreadsのAPI情報が.envから取得できないため、自動ポストをスキップしました。")
        return

    try:
        # ステップ1：メディアコンテナ（下書き）を作成する
        create_url = f"https://graph.threads.net/v1.0/me/threads"
        payload = {
            "media_type": "TEXT",
            "text": message,
            "access_token": THREADS_ACCESS_TOKEN
        }
        res_create = requests.post(create_url, data=payload)
        
        if res_create.status_code != 200:
            print(f"❌ Threads下書き作成エラー: {res_create.text}")
            return
            
        creation_id = res_create.json().get("id")

        # ステップ2：作成したコンテナを公開（パブリッシュ）する
        publish_url = f"https://graph.threads.net/v1.0/me/threads_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": THREADS_ACCESS_TOKEN
        }
        res_publish = requests.post(publish_url, data=publish_payload)
        
        if res_publish.status_code == 200:
            print("✅ Threadsへの自動ポストが成功しました！")
        else:
            print(f"❌ Threads公開エラー: {res_publish.text}")

    except Exception as e:
        print(f"❌ Threads通信エラー: {e}")
# =========================================================

def upload_image_to_server(image_path):
    """Catboxがインスタにブロックされるため、SNSに強いFreeimage.hostを使用"""
    url = "https://freeimage.host/api/1/upload"
    print("☁️ 画像をアップロードサーバー(Freeimage.host)に送信中...")
    try:
        import base64
        # 画像をテキストデータ（Base64）に変換して安全に送る
        with open(image_path, "rb") as file:
            b64_image = base64.b64encode(file.read()).decode('utf-8')
            
        payload = {
            "key": "6d207e02198a847aa98d0a2a901485a5", # 公式が一般公開している無料APIキー
            "action": "upload",
            "source": b64_image,
            "format": "json"
        }
        response = requests.post(url, data=payload)
        result = response.json()
        
        if result.get("status_code") == 200:
            image_url = result["image"]["url"]
            print(f"✅ 画像のURL化成功: {image_url}")
            return image_url
        else:
            print(f"❌ サーバーエラー: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 画像アップロードエラー: {e}")
        return None

def post_to_instagram(image_url, caption_text):
    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    
    # 【ステップ1】メディアコンテナの作成
    container_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
    container_payload = {
        'image_url': image_url,
        'caption': caption_text,
        'access_token': access_token
    }
    print("☁️ Instagramへ画像をアップロード中...")
    container_response = requests.post(container_url, data=container_payload)
    container_data = container_response.json()
    
    if 'id' not in container_data:
        print(f"❌ コンテナ作成エラー: {container_data}")
        return
        
    creation_id = container_data['id']

    # ▼▼▼ ココに1行追加！ ▼▼▼
    print("⏳ Instagram側の画像処理完了を15秒待ちます...")
    time.sleep(60) 
    # ▲▲▲ ココまで ▲▲▲
    
    # 【ステップ2】メディアの公開
    publish_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
    publish_payload = {
        'creation_id': creation_id,
        'access_token': access_token
    }
    print("☁️ Instagramへ投稿を公開中...")
    publish_response = requests.post(publish_url, data=publish_payload)
    publish_data = publish_response.json()
    
    if 'id' in publish_data:
        print("✅ Instagramへの自動投稿が完了しました！")
    else:
        print(f"❌ 公開エラー: {publish_data}")

# ↑↑↑ ここまで ↑↑↑

# =========================================================
# 🎬 リール動画用：Cloudinaryアップロード＆Instagram投稿機能
# =========================================================
def upload_video_to_cloudinary(video_path):
    """Cloudinaryに動画を自動アップロードしてURLを取得する"""
    print("☁️ Cloudinaryへ動画をアップロード中... (15秒の動画なので少し時間がかかります)")
    
    # .envからキーを取得してCloudinaryにログイン
    cloudinary.config( 
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
        api_key = os.environ.get("CLOUDINARY_API_KEY"), 
        api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
        secure = True
    )
    
    try:
        # ★ resource_type="video" を指定するのが動画アップロードの鉄則！
        response = cloudinary.uploader.upload(video_path, resource_type="video")
        video_url = response.get("secure_url")
        print(f"✅ 動画のURL化成功: {video_url}")
        return video_url
    except Exception as e:
        print(f"❌ Cloudinaryアップロードエラー: {e}")
        return None

def post_reel_to_instagram(video_url, caption_text):
    """Instagram Graph APIを使ってリール動画を自動投稿する"""
    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    
    # 【ステップ1】メディアコンテナの作成（REELS指定）
    container_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
    container_payload = {
        'media_type': 'REELS',    # ★ ここを REELS にするだけでリール投稿になります！
        'video_url': video_url,   # ★ image_url ではなく video_url
        'caption': caption_text,
        'access_token': access_token
    }
    print("☁️ Instagramへリールのアップロードをリクエスト中...")
    container_response = requests.post(container_url, data=container_payload)
    container_data = container_response.json()
    
    if 'id' not in container_data:
        print(f"❌ リールコンテナ作成エラー: {container_data}")
        return
        
    creation_id = container_data['id']
    print(f"✅ コンテナ作成成功 (ID: {creation_id})。Instagram側の処理完了を1分間待ちます⏳...")
    
    # 🚨【超重要】リール動画は、Instagram側のサーバーでエンコード(変換処理)が行われます。
    # この処理が終わる前に公開しようとするとエラーになるため、ここで強制的に「60秒待機」させます。
    time.sleep(60) 
    
    # 【ステップ2】メディアの公開
    publish_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
    publish_payload = {
        'creation_id': creation_id,
        'access_token': access_token
    }
    print("☁️ リール動画を公開（パブリッシュ）中...")
    publish_response = requests.post(publish_url, data=publish_payload)
    publish_data = publish_response.json()
    
    if 'id' in publish_data:
        print("🎉🎉🎉 Instagramへのリール自動投稿が完了しました！！！ 🎉🎉🎉")
    else:
        print(f"❌ 公開エラー: {publish_data}")
# =========================================================
# =========================================================
# 💬 YouTube：コメント投稿＆固定（ピン留め）機能
# =========================================================
def add_pinned_comment(video_id, comment_text):
    print(f"💬 動画(ID:{video_id})に固定コメントを追加中...")
    token_str = os.environ.get("YOUTUBE_TOKEN_JSON")
    try:
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        youtube = build('youtube', 'v3', credentials=creds)
        
        # 1. コメントを投稿する
        comment_res = youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": comment_text}
                    }
                }
            }
        ).execute()
        
        # 2. そのコメントを一番上に「固定」する
        comment_id = comment_res['snippet']['topLevelComment']['id']
        youtube.comments().setModerationStatus(
            id=comment_id,
            moderationStatus="published",
            ban=False
        ).execute()
        
        print("✅ 固定コメントの設置が完了しました！")
    except Exception as e:
        print(f"⚠️ コメント固定エラー（手動で固定してください）: {e}")

# =========================================================
# 🎥 YouTube Shorts用：自動アップロード機能
# =========================================================
def upload_to_youtube_shorts(video_path, title, description, tags):
    """YouTubeへ動画を自動アップロードし、直後にコメントを固定する"""
    print("🎥 YouTube Shortsへ動画をアップロード中...")
    
    token_str = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not token_str:
        print("❌ YOUTUBE_TOKEN_JSONが設定されていません。")
        return
        
    try:
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        youtube = build('youtube', 'v3', credentials=creds)
        
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '24' # 24 = エンターテイメント
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
        
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )
        # アップロード実行！
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )
        response = request.execute()
        
        video_id = response.get('id')
        print(f"🎉🎉🎉 YouTube Shortsの自動投稿が完了しました！ URL: https://youtu.be/{video_id} 🎉🎉🎉")
        
        # ⭕ ▼▼▼ ここに正しいインデントで追加 ▼▼▼ ⭕
        fixed_msg = (
            "🎯 本日のAI全予想はこちら（完全無料）！\n"
            "👉 https://loto-yosou-ai.com/\n\n"
            "次回の予想も見逃さないよう、チャンネル登録お願いします！✨"
        )
        add_pinned_comment(video_id, fixed_msg)
        # ⭕ ▲▲▲ ここまで追加 ▲▲▲ ⭕

    except Exception as e:
        print(f"❌ YouTubeアップロードエラー: {e}")
# =========================================================

# =========================================================
# 🎵 TikTok用：自動アップロード機能
# =========================================================
def post_to_tiktok(video_path, caption):
    """TikTokへ動画を完全自動でアップロードする"""
    session_id = os.environ.get("TIKTOK_SESSION_ID")
    if not session_id:
        print("⚠️ TIKTOK_SESSION_IDが設定されていないため、TikTokへの投稿をスキップしました。")
        return

    print(f"🎵 TikTokへ動画({video_path})をアップロード中...")

    # tiktok-uploaderが読み込める「Netscape形式」のCookieファイルを自動生成
    cookie_content = f".tiktok.com\tTRUE\t/\tFALSE\t2147483647\tsessionid\t{session_id}\n"
    cookie_file = "tiktok_cookies.txt"
    with open(cookie_file, "w") as f:
        f.write(cookie_content)

    try:
        from tiktok_uploader.upload import upload_video
        
        # ヘッドレスブラウザ（裏側の見えないChrome）を起動して自動投稿
        upload_video(
            video_path,
            description=caption,
            cookies=cookie_file,
            headless=True
        )
        print("🎉🎉🎉 TikTokへの自動投稿が完了しました！！！ 🎉🎉🎉")
        
    except Exception as e:
        print(f"❌ TikTokアップロードエラー: {e}")
    finally:
        # セキュリティのため、使い終わったCookieファイルは削除しておく
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
# =========================================================

def create_result_image(n4_text, n3_text, base_image_path, output_image_path, target_kai="", target_date="", n4_rank="", n3_rank=""):
    """ナンバーズ専用：1080x1350の大画面に合わせて、文字を大きく中央揃えで描画する職人"""
    print("🎨 ナンバーズ専用の予想画像を生成中（中央揃え・大画面版）...")
    try:
        # 1. ベース（背景）となる画像を開く
        img = Image.open(base_image_path)
        W, H = img.size # 画像の実際の幅と高さを取得 (1080x1350を想定)
    except FileNotFoundError:
        print(f"❌ 背景画像({base_image_path})が見つかりません！")
        return False

    draw = ImageDraw.Draw(img)

    # 日本語フォントの準備
    font_path = "NotoSansJP-Bold.ttf"
    if not os.path.exists(font_path):
        # 以前修正した、 static が入ったURLを使用
        font_url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/static/NotoSansJP-Bold.ttf"
        urllib.request.urlretrieve(font_url, font_path)

    # --- デザイン設定 (1080x1350用に大幅に数値をアップ) ---
    shadow_color = (100, 100, 100)  # 影の色
    white = (255, 255, 255)         # 文字の色
    n4_color = (22, 163, 74)   # ナンバーズ4は緑色
    n3_color = (217, 119, 6)   # ナンバーズ3はオレンジ

    # ボールの設定 (大画面用に大きく)
    ball_dia = 160 # ボールの直径
    ball_space = 25 # ボール間のスペース
    shadow_offset = 6 # 影のズレ量

    # フォントサイズの設定（見やすく大きく！）
    font_title = ImageFont.truetype(font_path, 90)
    font_num = ImageFont.truetype(font_path, 95)
    font_sub = ImageFont.truetype(font_path, 50) # ★追加：日付用の少し小さなフォント

    # 全体の上下バランスを見て、描画開始Y位置を決める
    current_y = 250 

    # ------------------------------------------------
    # 描画1：ナンバーズ4
    # ------------------------------------------------
    title4 = f"【ナンバーズ4 予想A {n4_rank}】"
    subtitle = f"{target_kai} ({target_date})" # ★追加：回号と日付
    
    # ★Pillowの機能でタイトルの描画サイズを取得し、中央位置(X)を計算
    # (Pillow 9.2.0以降推奨の textbbox を使用)
    left, top, right, bottom = draw.textbbox((0, 0), title4, font=font_title)
    text_w = right - left
    text_h = bottom - top
    title_x = (W - text_w) / 2 # 画像中央から文字幅の半分を引く
    
    # タイトルの影を描画
    draw.text((title_x + shadow_offset, current_y + shadow_offset), title4, font=font_title, fill=shadow_color)
    # タイトル本体を描画
    draw.text((title_x, current_y), title4, font=font_title, fill=n4_color)

    # ★追加：サブタイトル（回号と日付）の描画
    left_s, top_s, right_s, bottom_s = draw.textbbox((0, 0), subtitle, font=font_sub)
    sub_w = right_s - left_s
    sub_x = (W - sub_w) / 2
    draw.text((sub_x + shadow_offset, current_y + 110 + shadow_offset), subtitle, font=font_sub, fill=shadow_color)
    draw.text((sub_x, current_y + 110), subtitle, font=font_sub, fill=white)
    
    current_y += text_h + 80 # ボール列との間隔

    # ★ボール列全体の中央位置を計算
    total_ball_w_4 = (ball_dia * 4) + (ball_space * 3)
    ball_x = (W - total_ball_w_4) / 2 # 列の開始X位置

    for digit in n4_text:
        # ボールの影を描画
        draw.ellipse([ball_x + shadow_offset, current_y + shadow_offset, ball_x + ball_dia + shadow_offset, current_y + ball_dia + shadow_offset], fill=shadow_color)
        # ボール本体を描画
        draw.ellipse([ball_x, current_y, ball_x + ball_dia, current_y + ball_dia], fill=n4_color)
        
        # ★数字もボール内の中央に来るように計算
        left, top, right, bottom = draw.textbbox((0, 0), digit, font=font_num)
        num_w = right - left
        num_h = bottom - top
        num_x = ball_x + (ball_dia - num_w) / 2
        # Y位置はフォントのベースラインによって微調整が必要な場合あり
        num_y = current_y + (ball_dia - num_h) / 2 - 12 

        # 数字をボールの中心に描画
        draw.text((num_x, num_y), digit, font=font_num, fill=white)
        ball_x += ball_dia + ball_space # 次のボールへの間隔

    # ------------------------------------------------
    # 描画2：ナンバーズ3
    # ------------------------------------------------
    current_y += ball_dia + 180 # N4とN3の間隔
    title3 = f"【ナンバーズ3 予想A {n3_rank}】"
    subtitle = f"{target_kai} ({target_date})" # ★追加：回号と日付
    
    # タイトルの中央位置を計算
    left, top, right, bottom = draw.textbbox((0, 0), title3, font=font_title)
    text_w = right - left
    title_x = (W - text_w) / 2
    
    draw.text((title_x + shadow_offset, current_y + shadow_offset), title3, font=font_title, fill=shadow_color)
    draw.text((title_x, current_y), title3, font=font_title, fill=n3_color)

    # ★追加：ここにもサブタイトル（回号と日付）の描画
    draw.text((sub_x + shadow_offset, current_y + 110 + shadow_offset), subtitle, font=font_sub, fill=shadow_color)
    draw.text((sub_x, current_y + 110), subtitle, font=font_sub, fill=white)
    
    current_y += text_h + 80 

    # ★ボール列全体の中央位置を計算 (3個用)
    total_ball_w_3 = (ball_dia * 3) + (ball_space * 2)
    ball_x = (W - total_ball_w_3) / 2

    for digit in n3_text:
        draw.ellipse([ball_x + shadow_offset, current_y + shadow_offset, ball_x + ball_dia + shadow_offset, current_y + ball_dia + shadow_offset], fill=shadow_color)
        draw.ellipse([ball_x, current_y, ball_x + ball_dia, current_y + ball_dia], fill=n3_color)
        
        # 数字の中央位置を計算
        left, top, right, bottom = draw.textbbox((0, 0), digit, font=font_num)
        num_w = right - left
        num_h = bottom - top
        num_x = ball_x + (ball_dia - num_w) / 2
        num_y = current_y + (ball_dia - num_h) / 2 - 12

        draw.text((num_x, num_y), digit, font=font_num, fill=white)
        ball_x += ball_dia + ball_space

    # --- 共通処理（以前の修正を維持） ---
    # 完成した画像を保存（Instagram対応のためJPEGに変換して保存！）
    img = img.convert("RGB") 
    img.save(output_image_path, "JPEG", quality=95)
    print(f"✅ 画像の生成が完了しました！: {output_image_path}")
    return True
# =========================================================
import re
import requests
from bs4 import BeautifulSoup

def get_numbers_full_detail():
    """ベースページで大成功しているロジックを呼び出し、確実に番号を同期する完全決着版"""
    print("☁️ 詳細ページ用のデータを同期中...")
    
    result_data = {
        "round": "", "date": "",
        "n4_numbers": [], "n4_prizes": [],
        "n3_numbers": [], "n3_prizes": []
    }

    # ==========================================
    # ★大革命★ ベースページで100%成功している関数を呼び出して、回号・日付・番号を確実にセットする！
    # ==========================================
    try:
        # fetch_both_history() はすでに同じファイル内で定義されているため呼び出せます
        base_data = fetch_both_history()[0] 
        result_data["round"] = base_data["kai"]
        result_data["date"] = base_data["date"]
        result_data["n4_numbers"] = list(base_data["n4_win"])
        result_data["n3_numbers"] = list(base_data["n3_win"])
        print(f"✅ ベースデータからの番号同期に成功！(N4: {base_data['n4_win']}, N3: {base_data['n3_win']})")
    except Exception as e:
        print(f"❌ ベースデータの同期に失敗しました: {e}")
        return None

    # ==========================================
    # あとは「賞金のテーブル（金額・口数）」だけを楽天から頂く！
    # ==========================================
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        # --- ナンバーズ4の賞金取得 ---
        url4 = "https://takarakuji.rakuten.co.jp/backnumber/numbers4/"
        res4 = requests.get(url4, headers=headers, timeout=10)
        if res4.status_code == 200:
            res4.encoding = 'euc-jp'
            soup4 = BeautifulSoup(res4.content, 'html.parser')
            for table in soup4.find_all('table'):
                if 'ストレート' in table.get_text() and 'ボックス' in table.get_text():
                    for tr in table.find_all('tr'):
                        header_cell = tr.find(['th', 'td'])
                        if not header_cell: continue
                        clean_header = header_cell.get_text(strip=True).replace(' ', '').replace('　', '')
                        
                        grade = None
                        if 'セット' in clean_header and 'ストレート' in clean_header: grade = 'セット(ストレート)'
                        elif 'セット' in clean_header and 'ボックス' in clean_header: grade = 'セット(ボックス)'
                        elif 'ストレート' in clean_header: grade = 'ストレート'
                        elif 'ボックス' in clean_header: grade = 'ボックス'

                        if grade:
                            tds = tr.find_all('td')
                            if len(tds) >= 2:
                                result_data["n4_prizes"].append({
                                    "grade": grade, "winners": tds[-2].get_text(strip=True), "prize": tds[-1].get_text(strip=True)
                                })
                    break

        # --- ナンバーズ3の賞金取得 ---
        url3 = "https://takarakuji.rakuten.co.jp/backnumber/numbers3/"
        res3 = requests.get(url3, headers=headers, timeout=10)
        if res3.status_code == 200:
            res3.encoding = 'euc-jp'
            soup3 = BeautifulSoup(res3.content, 'html.parser')
            for table in soup3.find_all('table'):
                if 'ストレート' in table.get_text() and 'ミニ' in table.get_text():
                    for tr in table.find_all('tr'):
                        header_cell = tr.find(['th', 'td'])
                        if not header_cell: continue
                        clean_header = header_cell.get_text(strip=True).replace(' ', '').replace('　', '')
                        
                        grade = None
                        if 'セット' in clean_header and 'ストレート' in clean_header: grade = 'セット(ストレート)'
                        elif 'セット' in clean_header and 'ボックス' in clean_header: grade = 'セット(ボックス)'
                        elif 'ストレート' in clean_header: grade = 'ストレート'
                        elif 'ボックス' in clean_header: grade = 'ボックス'
                        elif 'ミニ' in clean_header: grade = 'ミニ'

                        if grade:
                            tds = tr.find_all('td')
                            if len(tds) >= 2:
                                result_data["n3_prizes"].append({
                                    "grade": grade, "winners": tds[-2].get_text(strip=True), "prize": tds[-1].get_text(strip=True)
                                })
                    break

        print("✅ 詳細ページ用データの完全合成に成功しました！")
        return result_data
        
    except Exception as e:
        print(f"❌ 賞金データ解析エラー: {e} (ただし番号の同期は完了しているため生成を続行します)")
        return result_data # 万が一賞金テーブルが見つからなくても、回号・日付・番号は無事なのでそのまま返す！

def generate_numbers_detail_page(result_data):
    """既存のベースHTML/CSSにナンバーズの詳細データを流し込む"""
    print("🔄 ナンバーズ 詳細ページ(HTML)をベースデザインで生成中...")
    
    if not result_data:
        result_data = {
            "round": "第----回", "date": "----/--/--",
            "n4_numbers": ["-","-","-","-"], "n4_prizes": [],
            "n3_numbers": ["-","-","-"], "n3_prizes": []
        }

    # N4のボールとテーブル行を生成
    n4_balls = "".join([f'<span class="ball">{n}</span>' for n in result_data.get("n4_numbers", [])])
    n4_trs = ""
    for p in result_data.get("n4_prizes", []):
        n4_trs += f"<tr><td style='font-weight:bold; color:#334155;'>{p['grade']}</td><td style='color:#ea580c; font-weight:bold; font-size:16px;'>{p['prize']}</td><td style='color:#64748b;'>{p['winners']}</td></tr>"

    # N3のボール（少し色を変えてピンク系に）とテーブル行を生成
    n3_balls = "".join([f'<span class="ball" style="background: linear-gradient(135deg, #f43f5e, #e11d48);">{n}</span>' for n in result_data.get("n3_numbers", [])])
    n3_trs = ""
    for p in result_data.get("n3_prizes", []):
        n3_trs += f"<tr><td style='font-weight:bold; color:#334155;'>{p['grade']}</td><td style='color:#ea580c; font-weight:bold; font-size:16px;'>{p['prize']}</td><td style='color:#64748b;'>{p['winners']}</td></tr>"
    
    # === ▼ ここから追加 ▼ ===
    archive_link_html = ""
    target_round_str = result_data.get('round', '')
    round_match = re.search(r'\d+', target_round_str)
    
    if round_match:
        kai_num = round_match.group().zfill(4)
        archive_url = f"archive/numbers_{kai_num}.html"
        archive_link_html = f"""
        <a href="{archive_url}" style="display: inline-block; background-color: #f8fafc; color: #1e3a8a; border: 2px solid #1e3a8a; padding: 12px 25px; text-decoration: none; border-radius: 50px; font-weight: bold; margin: 10px 5px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: transform 0.2s;">
            📊 この回の出目分析とAI成績を見る ＞
        </a>
        """
    # === ▲ ここまで追加 ▲ ===

    # HTMLの組み立て（※CSSの波括弧は {{ }} と2つ重ねてエラーを回避しています）
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【{result_data.get('round', '')}】ナンバーズ3＆4 抽選結果詳細データ</title>
    <link rel="icon" type="image/png" href="favicon.icon.png">
    <link rel="apple-touch-icon" href="favicon.icon.png">
    <meta name="description" content="{result_data.get('round', '')}のナンバーズ3・ナンバーズ4の当せん金額・口数などの詳細データを公開しています。">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; padding: 10px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ 
    color: #1e3a8a; 
    padding: 12px 12px; /* 👈 上下の余白を12px、左右の余白を12pxに縮小 */
    font-size: 14px;    /* 👈 文字サイズを少し小さく指定（元は未指定＝16px相当） */
    text-decoration: none; 
    font-weight: bold; 
    border-bottom: 3px solid transparent; 
    transition: all 0.3s; 
}}
        nav a.active {{ border-bottom: 3px solid #16a34a; color: #16a34a; }}
        nav a:hover {{ background-color: #f0f4f8; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #16a34a; border-bottom: 2px solid #dcfce7; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; }}
        .prediction-box {{ background-color: #f0fdf4; border: 2px solid #bbf7d0; border-radius: 12px; padding: 25px; margin-bottom: 20px;}}
        .numbers-row {{ background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; align-items: center; flex-wrap: wrap; }}
        .row-label {{ font-size: 18px; font-weight: bold; color: #1e3a8a; background-color: #e0e7ff; padding: 5px 15px; border-radius: 4px; margin-right: 20px; min-width: 60px; text-align: center; }}
        .ball-container {{ display: flex; gap: 12px; flex-wrap: wrap; margin-right: auto;}}
        .ball {{ display: inline-flex; justify-content: center; align-items: center; width: 45px; height: 45px; background: linear-gradient(135deg, #22c55e, #16a34a); color: white; border-radius: 8px; font-size: 24px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.3); }}
        
        @media (max-width: 600px) {{ 
            .numbers-row {{ flex-direction: column; align-items: flex-start; padding: 15px; gap: 10px; }} 
            .row-label {{ margin-right: 0; margin-bottom: 5px; }} 
            .ball-container {{ margin-right: 0; gap: 8px; }}
            .ball {{ width: 36px; height: 36px; font-size: 18px; border-radius: 6px; }} 
        }}
        
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 15px; text-align: center; }}
        th, td {{ padding: 15px; border-bottom: 1px solid #e2e8f0; }}
        th {{ background-color: #f8fafc; color: #475569; font-weight: bold; }}
        footer {{ background-color: #1e293b; color: #94a3b8; text-align: center; padding: 40px 20px; margin-top: 60px; font-size: 13px; border-top: 4px solid #3b82f6; }}
        .footer-links {{ margin-bottom: 15px; }}
        .footer-links a {{ color: #cbd5e1; text-decoration: none; margin: 0 10px; transition: color 0.2s; }}
        .footer-links a:hover {{ color: white; text-decoration: underline; }}
        /* PC用とスマホ用の広告を自動で切り替える魔法のCSS */
.ad-pc {{ display: block; }}
.ad-sp {{ display: none; }}

/* スマホ（画面幅600px以下）で見た時だけルールを逆転させる */
@media (max-width: 600px) {{
    .ad-pc {{ display: none; }}
    .ad-sp {{ display: block; }}
}}
    </style> 
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1431683156739681"
     crossorigin="anonymous"></script>
</head>
<body>
    <header>
        <a href="index.html" style="text-decoration: none;">
            <img src="Lotologo001.png" alt="宝くじ当選予想・データ分析ポータル" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">ナンバーズ詳細データ</div>
        </a>
    </header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html" class="active">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="column.html">攻略ガイド🔰</a>
        <a href="horoscope.html">占い🔮</a>
        <a href="archive.html" >YOUTUBE🎥</a>
    </nav>

    <div class="container">
        <h1 style="color: #1e3a8a; font-size: 26px; text-align: center; border-bottom: 3px solid #1e3a8a; padding-bottom: 15px; margin-bottom: 30px;">
            {result_data.get('round', '')} ({result_data.get('date', '')}) 抽選結果詳細
        </h1>

        <div style="text-align: center; margin: 20px 0;">
    <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
    
    <!-- ▼ PCで見ている時だけ表示されるタグ1 ▼ -->
    <div class="ad-pc">
        <div id="im-839c9bd971c54d348a71dcbfed7984d3">
  <script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script>
  <script>(window.adsbyimobile=window.adsbyimobile||[]).push({{pid:84847,mid:592459,asid:1929932,type:"banner",display:"inline",elementid:"im-839c9bd971c54d348a71dcbfed7984d3"}})</script>
</div>
    </div>
    
    <!-- ▼ スマホで見ている時だけ表示されるタグ1 ▼ -->
    <div class="ad-sp">
        <div id="im-4b18f7a610e54053ae1a96fafd113652">
  <script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script>
  <script>(window.adsbyimobile=window.adsbyimobile||[]).push({{pid:84847,mid:592460,asid:1929934,type:"banner",display:"inline",elementid:"im-4b18f7a610e54053ae1a96fafd113652"}})</script>
</div>
    </div>
</div>

        <div class="section-card">
            <h2 class="section-header">🎯 ナンバーズ4 抽選結果</h2>
            <div class="prediction-box">
                <div class="numbers-row">
                    <div class="row-label">当せん数字</div>
                    <div class="ball-container">
                        {n4_balls}
                    </div>
                </div>
            </div>
            <table>
                <thead><tr><th>等級</th><th>当せん金額</th><th>口数</th></tr></thead>
                <tbody>
                    {n4_trs}
                </tbody>
            </table>
        </div>

        <div class="section-card" style="text-align: center; background: linear-gradient(to right, #ffffff, #f0fdf4); border: 2px solid #22c55e; margin-bottom: 30px;">
            <h3 style="color: #15803d; margin-top: 0; font-size: 20px;">📱 最新のAI予想をLINEでお届け！</h3>
            <p style="font-size: 15px; color: #475569; margin-bottom: 20px;">
                抽選日の朝に「今日の予想」を直接スマホにお知らせします。<br>
                買い忘れ防止や、キャリーオーバーの速報受け取りにぜひ登録してください！
            </p>
            <a href="https://lin.ee/rKXCkr3" style="display: inline-block; background-color: #06C755; color: white; text-decoration: none; padding: 15px 35px; border-radius: 30px; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(6, 199, 85, 0.3); transition: transform 0.2s;">
                💬 LINEで無料通知を受け取る
            </a>
        </div>

        <div class="section-card">
            <h2 class="section-header" style="color: #e11d48; border-color: #ffe4e6;">🎯 ナンバーズ3 抽選結果</h2>
            <div class="prediction-box" style="background-color: #fff1f2; border-color: #fecdd3;">
                <div class="numbers-row">
                    <div class="row-label" style="color: #be123c; background-color: #ffe4e6;">当せん数字</div>
                    <div class="ball-container">
                        {n3_balls}
                    </div>
                </div>
            </div>
            <table>
                <thead><tr><th>等級</th><th>当せん金額</th><th>口数</th></tr></thead>
                <tbody>
                    {n3_trs}
                </tbody>
            </table>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="numbers.html" style="display: inline-block; background-color: #3b82f6; color: white; padding: 12px 25px; text-decoration: none; border-radius: 50px; font-weight: bold; margin: 10px 5px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                ◀ ナンバーズ AI予想トップへ
            </a>
            {archive_link_html}
        </div>
    
    <!-- 👇広告の表示部分👇 -->
        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            
            <div class="ad-pc">
                {imobile_ad2_pc}
            </div>
            
            <div class="ad-sp">
                {imobile_ad2_sp}
            </div>
        </div>
</div>

    <footer>
        <div class="footer-links">
            <a href="about.html">運営者情報</a> |
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p>※当サイトのデータは当選を保証するものではありません。宝くじの購入は自己責任でお願いいたします。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 宝くじ当選予想・データ分析ポータル All Rights Reserved.</p>
    </footer>

        {imobile_overlay}

</body>
</html>"""

    with open("numbers_detail.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ ナンバーズ 詳細ページ(ベースデザイン版) の生成が完了しました！")

# --- 1. 過去データの取得（★ロトと同様のカット方式に修正） ---
def fetch_single_history(base_url, length):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    data = []
    
    # ★過去1年分（12ヶ月分）のURLを自動生成
    today = datetime.date.today()
    target_urls = [base_url]
    
    for i in range(36):
        y = today.year
        m = today.month - i
        if m <= 0:
            m += 12
            y -= 1
        # 楽天宝くじの正しいURLフォーマット（/YYYYMM/）で追加
        target_urls.append(f"{base_url}{y}{m:02d}/")
    
    for url in target_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'euc-jp'
            soup = BeautifulSoup(res.content, 'html.parser')
            
            text = soup.get_text(separator=' ')
            
            # 文章の中から「第〇〇回」をすべて見つける
            for m in re.finditer(r'第\s*(\d+)\s*回', text):
                kai = f"第{m.group(1)}回"
                
                # 回号のすぐ後ろのテキスト（300文字分）を切り出して解析
                chunk = text[m.end():m.end() + 300]
                
                # ★【修正部分】別の回号のデータが混ざらないよう、次の「第〇〇回」が現れたらそこでカットする
                next_kai_match = re.search(r'第\s*\d+\s*回', chunk)
                if next_kai_match:
                    chunk = chunk[:next_kai_match.start()]
                
                # 切り出した中から「日付」を見つける
                date_m = re.search(r'(\d{4})[/年]\s*(\d{1,2})\s*[/月]\s*(\d{1,2})', chunk)
                if not date_m: continue
                
                date = f"{date_m.group(1)}/{date_m.group(2).zfill(2)}/{date_m.group(3).zfill(2)}"
                
                # 日付の直後から残りのテキストを切り出す
                num_chunk = chunk[date_m.end():]
                
                # 「当せん番号」の文字の後の数字を抽出
                win_m = re.search(r'当せん番号\D*(\d{' + str(length) + r'})', num_chunk)
                if win_m:
                    win_num = win_m.group(1)
                    
                    # ★すでに取得した回号（重複）でなければ追加する
                    if not any(d['kai'] == kai for d in data):
                        data.append({"kai": kai, "date": date, "win_num": win_num})
                        
        except Exception:
            pass # エラーが起きても止まらずに次の月の取得へ進む
            
    # ★最後にすべてのデータを「回号の新しい順（降順）」に並び替える
    data.sort(key=lambda x: int(re.search(r'\d+', x['kai']).group()), reverse=True)
    
    return data

def fetch_both_history():
    print("🔄 ナンバーズ3＆4のデータ取得＆解析を開始...")
    n4_history = fetch_single_history("https://takarakuji.rakuten.co.jp/backnumber/numbers4/", 4)
    n3_history = fetch_single_history("https://takarakuji.rakuten.co.jp/backnumber/numbers3/", 3)
    
    # N3とN4のデータを「回号」をキーにして安全に合体させる
    merged = []
    n3_dict = {item['kai']: item for item in n3_history}
    
    for n4 in n4_history:
        if n4['kai'] in n3_dict:
            n3 = n3_dict[n4['kai']]
            merged.append({
                "kai": n4['kai'], "date": n4['date'],
                "n4_win": n4['win_num'], "n3_win": n3['win_num']
            })
            
    if not merged: raise ValueError("過去データが取得できませんでした。（サイト構造が変更された可能性があります）")
    print(f"📡 データ取得成功: 最新回 {merged[0]['kai']} (N4: {merged[0]['n4_win']}, N3: {merged[0]['n3_win']})")
    return merged

# --- 2. ホット＆コールド算出 (N4とN3を分けて算出できるように修正) ---
def analyze_digit_trends(history_data, win_key):
    all_digits = []
    for data in history_data:
        all_digits.extend(list(data[win_key]))
    
    counts = Counter(all_digits)
    for i in range(10):
        if str(i) not in counts: counts[str(i)] = 0
            
    sorted_counts = counts.most_common()
    hot = sorted_counts[:3]  # 上位3つ
    cold = list(reversed(sorted_counts))[:3] # 下位3つ
    return hot, cold

# --- 3. 複合アルゴリズム予想生成（★機械学習ハイブリッド版・ナンバーズ専用） ---
def generate_advanced_predictions(history_data, length, win_key):
    import numpy as np
    from xgboost import XGBClassifier
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense

    print(f"🧠 ナンバーズ{length} ハイブリッドAI（RF + XGB + LSTM）予測を開始します...")
    if not history_data or len(history_data) < 20:
        return [], "Bランク", "データ不足のため基本予想", ""

    draws = [[int(n) for n in d[win_key]] for d in reversed(history_data)]
    
    # --- 1. 共起性行列 ---
    pair_counts = Counter()
    for draw in draws:
        for pair in itertools.combinations(sorted(draw), 2):
            pair_counts[pair] += 1

    # --- 2 & 3. 桁ごとのハイブリッドAI構築 ---
    pos_ml_scores = []
    window_size = 10 
    
    # ★追加：全桁の中で一番確率が高い数字を記憶する変数
    best_overall_pos = 0
    best_overall_digit = 0
    best_overall_score = -1

    for pos in range(length):
        features = []
        labels = []
        pos_sequence = [draw[pos] for draw in draws]
        
        for i in range(window_size, len(pos_sequence) - 1):
            past_window = pos_sequence[i-window_size:i]
            past_counts = Counter(past_window)
            
            target_digit = pos_sequence[i] 
            for num in range(10): # ナンバーズは0〜9
                features.append([past_counts.get(num, 0)])
                labels.append(1 if num == target_digit else 0)

        X = np.array(features)
        y = np.array(labels)

        latest_window = pos_sequence[-window_size:]
        latest_counts = Counter(latest_window)
        X_latest = np.array([[latest_counts.get(num, 0)] for num in range(10)])

        can_train = len(np.unique(y)) > 1

        prob_rf = np.zeros(10)
        if can_train:
            rf_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
            rf_model.fit(X, y)
            rf_preds = rf_model.predict_proba(X_latest)
            if rf_preds.shape[1] > 1:
                for i in range(10): prob_rf[i] = rf_preds[i, 1]

        prob_xgb = np.zeros(10)
        if can_train:
            xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
            xgb_model.fit(X, y)
            xgb_preds = xgb_model.predict_proba(X_latest)
            if xgb_preds.shape[1] > 1:
                for i in range(10): prob_xgb[i] = xgb_preds[i, 1]

        prob_lstm = np.zeros(10)
        if can_train:
            X_3d = X.reshape((X.shape[0], 1, X.shape[1]))
            X_latest_3d = X_latest.reshape((X_latest.shape[0], 1, X_latest.shape[1]))
            lstm_model = Sequential([
                LSTM(32, activation='relu', input_shape=(1, X.shape[1])),
                Dense(1, activation='sigmoid')
            ])
            lstm_model.compile(optimizer='adam', loss='binary_crossentropy')
            lstm_model.fit(X_3d, y, epochs=5, verbose=0)
            lstm_preds = lstm_model.predict(X_latest_3d, verbose=0).flatten()
            for i in range(10): prob_lstm[i] = lstm_preds[i]

        final_prob = (prob_rf + prob_xgb + prob_lstm) / 3.0
        ml_scores = {num: prob for num, prob in enumerate(final_prob)}
        pos_ml_scores.append(ml_scores)
        
        # ★ここで「この桁で一番強い数字」をチェックし、全体ベストを更新する
        for num, prob in ml_scores.items():
            if prob > best_overall_score:
                best_overall_score = prob
                best_overall_pos = pos
                best_overall_digit = num

    # ★特注HOT数字のテキストを作成
    top_nums_str = f"{best_overall_pos+1}桁目の「{best_overall_digit}」"

    # --- 4. ハイブリッド選定 ---
    predictions = []
    seen, seen_box = set(), set()
    digits = list(range(10))
    candidates = []

    # ★修正：予想生成時に、本命(一番最初)の予想には必ずHOT数字を組み込む！
    for i in range(5000): 
        cand = []
        for pos in range(length):
            # 本命(0番目)の生成時は、ベストな桁を強制的に固定する
            if i < 100 and pos == best_overall_pos:
                cand.append(best_overall_digit)
            else:
                weights = [pos_ml_scores[pos][n] for n in digits]
                if sum(weights) > 0:
                    cand.append(random.choices(digits, weights=weights)[0])
                else:
                    cand.append(random.choice(digits))
        candidates.append(cand)

    valid_candidates = []
    for cand in candidates:
        base_score = sum(pos_ml_scores[pos][cand[pos]] for pos in range(length))
        pair_bonus = sum(pair_counts.get(pair, 0) for pair in itertools.combinations(sorted(cand), 2))
        
        # 本命予想(HOT数字入り)を優先的に採用するため、スコアに強力なボーナスを与える
        if cand[best_overall_pos] == best_overall_digit:
            base_score += 10.0 # 圧倒的ボーナス
            
        final_score = base_score + (pair_bonus * 0.05)
        
        counts = Counter(cand)
        if any(v >= 3 for v in counts.values()): # トリプル以上を除外
            continue
            
        valid_candidates.append((final_score, cand))

    # スコアが高い順（HOT数字入りが必ず上位に来る）にソート
    valid_candidates.sort(key=lambda x: x[0], reverse=True)
    
    for score, cand in valid_candidates:
        cand_str = "".join(map(str, cand))
        box_str = "".join(sorted(cand_str))
        if cand_str not in seen and box_str not in seen_box:
            seen.add(cand_str)
            seen_box.add(box_str)
            predictions.append(cand_str)
        if len(predictions) == 5: break

    while len(predictions) < 5:
        cand_str = "".join(str(random.randint(0,9)) for _ in range(length))
        if cand_str not in seen:
            seen.add(cand_str)
            predictions.append(cand_str)

    # 自信度の判定
    avg_max_score = np.mean([max(pos_ml_scores[pos].values()) for pos in range(length)])
    if avg_max_score > 0.4:
        rank, msg = "Sランク", f"🔥 激アツ！AIがナンバーズ{length}の強い偏りを検知！"
    elif avg_max_score > 0.25:
        rank, msg = "Aランク", f"✨ チャンス！ナンバーズ{length}の当選パターンが明確です。"
    else:
        rank, msg = "Bランク", f"⚠️ 過去データが分散。波乱の可能性があります。"
    
    return predictions, rank, msg, top_nums_str
    
# --- 4. 履歴の保存と成績の自動照合 ---
def manage_history(latest_data, n4_preds, n3_preds):
    # ▼▼▼ 変更①：ファイルの読み込みを削除し、JSONBinから取得 ▼▼▼
    print("☁️ JSONBin(Numbers)から履歴を取得中...")
    history_record = load_history_from_jsonbin()
    # ▲▲▲ ここまで ▲▲▲
            
    latest_kai = latest_data['kai']
    latest_kai_num = int(re.search(r'\d+', latest_kai).group()) # 最新回の数字部分だけを抽出
    actual_n4 = latest_data['n4_win']
    actual_n3 = latest_data['n3_win']
    
    for record in history_record:
        record_kai_match = re.search(r'\d+', record.get('target_kai', ''))
        if record.get('status') == 'waiting' and record_kai_match:
            record_kai_num = int(record_kai_match.group())
            
            # ★修正：「第6000回」と「第06000回」の違いを無視し、数字ベースで判定して更新
            if record_kai_num == latest_kai_num:
                # ナンバーズ4の判定
                res_n4 = "ハズレ"
                for p in record['n4_preds']:
                    if p == actual_n4: res_n4 = "ストレート🎯"
                    elif sorted(p) == sorted(actual_n4) and "🎯" not in res_n4: res_n4 = "ボックス🎯"
                
                # ナンバーズ3の判定
                res_n3 = "ハズレ"
                for p in record['n3_preds']:
                    if p == actual_n3: res_n3 = "ストレート🎯"
                    elif sorted(p) == sorted(actual_n3) and "🎯" not in res_n3: res_n3 = "ボックス🎯"
                    
                record['status'] = 'finished'
                record['actual_n4'] = actual_n4
                record['actual_n3'] = actual_n3
                record['result_n4'] = res_n4
                record['result_n3'] = res_n3
                record['target_kai'] = latest_kai # フォーマットを最新のものに上書き
                
    # 次回号の生成 (ナンバーズは通常4桁表記)
    next_kai_num = latest_kai_num + 1
    next_kai = f"第{next_kai_num:04d}回"
    
    if not any(int(re.search(r'\d+', r.get('target_kai', '0')).group()) == next_kai_num for r in history_record if re.search(r'\d+', r.get('target_kai', '0'))):
        history_record.insert(0, {
            "target_kai": next_kai,
            "status": "waiting",
            "n4_preds": n4_preds,
            "n3_preds": n3_preds,
            "actual_n4": "----",
            "actual_n3": "---",
            "result_n4": "抽選待ち...",
            "result_n3": "抽選待ち..."
        })
    
    history_record = history_record[:100]
    
    # ▼▼▼ 変更②：ファイルへの書き込みを削除し、JSONBinへ保存 ▼▼▼
    print("☁️ JSONBin(Numbers)へ最新データを保存中...")
    save_history_to_jsonbin(history_record)
    # ▲▲▲ ここまで ▲▲▲
        
    return history_record

def get_next_numbers_date():
    """現在時刻から次回のナンバーズ抽選日(月〜金)を自動計算する"""
    now = datetime.datetime.now()
    # 18:30以降に実行された場合は、当日の購入は終了したとみなして翌日基準で計算
    if now.hour >= 19 or (now.hour == 18 and now.minute >= 30):
        base_date = now.date() + datetime.timedelta(days=1)
    else:
        base_date = now.date()

    # ナンバーズは月〜金 (0〜4)
    n_days = 0
    while (base_date + datetime.timedelta(days=n_days)).weekday() > 4:
        n_days += 1
    next_date = base_date + datetime.timedelta(days=n_days)

    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return f"{next_date.month}月{next_date.day}日({weekdays[next_date.weekday()]})"

# ==========================================
# ▼▼▼ 新規追加：アーカイブとサイトマップ生成機能（ナンバーズ版） ▼▼▼
# ==========================================
import os
import re
import datetime

def analyze_numbers_draw(main_nums_str):
    """ナンバーズの出目分析（奇数偶数、サム、連続）を行う共通関数"""
    if not main_nums_str or main_nums_str == "----" or main_nums_str == "---":
        return "", "", ""
        
    nums_list = [int(x) for x in str(main_nums_str)]
    length = len(nums_list)
    
    # 1. 奇数・偶数のバランス
    odds = sum(1 for n in nums_list if n % 2 != 0)
    evens = length - odds
    balance_str = f"奇数 {odds} ： 偶数 {evens}"
    
    # 2. 合計値（サム）
    total_sum = sum(nums_list)
    
    # 3. 連続・重複数字（ダブル・トリプル等）
    counts = Counter(nums_list)
    duplicates = [f"{n}が{c}個" for n, c in counts.items() if c >= 2]
    dup_str = "、".join(duplicates) if duplicates else "なし"
    
    return balance_str, str(total_sum), dup_str

def generate_archive_detail_pages(history_record):
    """過去の各回ごとの個別分析ページを /archive/ フォルダに生成する"""
    os.makedirs("archive", exist_ok=True)
    generated_urls = []
    
    for idx, record in enumerate(history_record):
        if record.get('status') == 'finished':
            kai_str = record.get('target_kai', '')
            kai_match = re.search(r'\d+', kai_str)
            if not kai_match: continue
            
            kai_num = kai_match.group().zfill(4)
            filename = f"numbers_{kai_num}.html" # ナンバーズ用にファイル名を変更
            filepath = os.path.join("archive", filename)
            page_url = f"https://loto-yosou-ai.com/archive/{filename}"
            generated_urls.append(page_url)
            
            if os.path.exists(filepath):
                continue

            actual_n4 = record.get('actual_n4', '----')
            actual_n3 = record.get('actual_n3', '---')
            result_n4 = record.get('result_n4', '----')
            result_n3 = record.get('result_n3', '----')
            
            # --- 出目分析ロジック ---
            n4_bal, n4_sum, n4_dup = analyze_numbers_draw(actual_n4)
            n3_bal, n3_sum, n3_dup = analyze_numbers_draw(actual_n3)
            
            # 予想HTML化
            def build_preds_html(preds, labels, bg_color, border_color):
                html = ""
                for i, pred in enumerate(preds):
                    balls = "".join([f'<span class="ball" style="display: inline-flex; justify-content: center; align-items: center; width: 35px; height: 35px; background: {bg_color}; color: white; border-radius: 6px; font-weight: bold; margin: 2px;">{n}</span>' for n in pred])
                    html += f'<div style="background:#fff; border:2px solid {border_color}; border-radius:8px; padding:10px; margin-bottom:8px; display:flex; align-items:center; flex-wrap:wrap;"><div style="font-weight:bold; color:#333; background:#f1f5f9; padding:3px 10px; border-radius:4px; margin-right:15px; font-size: 14px;">{labels[i]}</div><div style="display:flex;">{balls}</div></div>\n'
                return html

            labels = ['予想A(本命)', '予想B', '予想C', '予想D', '予想E']
            n4_preds_html = build_preds_html(record.get('n4_preds', []), labels, "linear-gradient(135deg, #22c55e, #16a34a)", "#bbf7d0")
            n3_preds_html = build_preds_html(record.get('n3_preds', []), labels, "linear-gradient(135deg, #f43f5e, #e11d48)", "#fecdd3")

            html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【{kai_str}】ナンバーズ3＆4 抽選結果とAI分析・振り返り</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; background-color: #f0f4f8; padding: 20px; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .result-box {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 15px; color: #334155; margin-bottom: 15px; }}
        th, td {{ padding:10px 0; border-bottom:1px solid #e2e8f0; }}
        th {{ text-align:left; width:45%; }}
        .ad-pc {{ display: block; }} .ad-sp {{ display: none; }}
        @media (max-width: 600px) {{ .ad-pc {{ display: none; }} .ad-sp {{ display: block; }} }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../archive_numbers.html" style="color: #3b82f6; text-decoration: none; font-weight: bold;">◀ 過去の結果一覧に戻る</a>
        <h1 style="color: #1e3a8a; font-size: 24px; margin-top: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">ナンバーズ {kai_str} 抽選結果とAI分析</h1>
        
        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <div class="ad-pc">{imobile_ad2_pc}</div>
            <div class="ad-sp">{imobile_ad2_sp}</div>
        </div>

        <p>本ページは、<strong>ナンバーズ {kai_str}</strong> の実際の抽選結果と、当サイトのAIアルゴリズムが事前に算出した予想結果の照合・分析レポートです。</p>
        
        <!-- ナンバーズ4 ブロック -->
        <div class="result-box" style="border-left: 5px solid #16a34a; background: #f0fdf4;">
            <h2 style="color:#15803d; margin-top:0; display:flex; justify-content:space-between; align-items:center;">
                <span>🎯 ナンバーズ4 結果</span>
                <span style="font-size: 24px; font-weight: 900; letter-spacing: 4px;">{actual_n4}</span>
            </h2>
            <div style="background:#fff; padding:15px; border-radius:8px; margin-bottom:15px; border:1px solid #bbf7d0;">
                <strong style="color:#16a34a;">📊 出目分析</strong>
                <table>
                    <tr><th>⚖️ 奇数・偶数比率</th><td><strong>{n4_bal}</strong></td></tr>
                    <tr><th>∑ 合計値（サム）</th><td><strong>{n4_sum}</strong></td></tr>
                    <tr><th>🔗 重複数字（ゾロ目）</th><td><strong>{n4_dup}</strong></td></tr>
                </table>
            </div>
            <h3 style="color:#16a34a; font-size:16px;">🤖 AI成績：【 {result_n4} 】</h3>
            {n4_preds_html}
        </div>

        <!-- ナンバーズ3 ブロック -->
        <div class="result-box" style="border-left: 5px solid #e11d48; background: #fff1f2; margin-top:30px;">
            <h2 style="color:#be123c; margin-top:0; display:flex; justify-content:space-between; align-items:center;">
                <span>🎯 ナンバーズ3 結果</span>
                <span style="font-size: 24px; font-weight: 900; letter-spacing: 4px;">{actual_n3}</span>
            </h2>
            <div style="background:#fff; padding:15px; border-radius:8px; margin-bottom:15px; border:1px solid #fecdd3;">
                <strong style="color:#e11d48;">📊 出目分析</strong>
                <table>
                    <tr><th>⚖️ 奇数・偶数比率</th><td><strong>{n3_bal}</strong></td></tr>
                    <tr><th>∑ 合計値（サム）</th><td><strong>{n3_sum}</strong></td></tr>
                    <tr><th>🔗 重複数字（ゾロ目）</th><td><strong>{n3_dup}</strong></td></tr>
                </table>
            </div>
            <h3 style="color:#e11d48; font-size:16px;">🤖 AI成績：【 {result_n3} 】</h3>
            {n3_preds_html}
        </div>
        
        <div style="margin-top: 30px; text-align: center;">
            <a href="../numbers.html" style="background: #1e3a8a; color: white; padding: 15px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; box-shadow: 0 4px 10px rgba(30, 58, 138, 0.3);">最新のナンバーズ AI予想を見る ＞</a>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <div class="ad-pc">{imobile_ad3_pc}</div>
            <div class="ad-sp">{imobile_ad3_sp}</div>
        </div>
    </div>
    {imobile_overlay}
</body>
</html>"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
                
    return generated_urls

def generate_archive_index_page(history_record):
    """全履歴へのリンクをまとめた一覧ページ (archive_numbers.html) を生成する"""
    links_html = ""
    for record in history_record:
        if record.get('status') == 'finished':
            kai_str = record.get('target_kai', '')
            kai_match = re.search(r'\d+', kai_str)
            if not kai_match: continue
            
            kai_num = kai_match.group().zfill(4)
            actual_n4 = record.get('actual_n4', '----')
            actual_n3 = record.get('actual_n3', '---')
            result_n4 = record.get('result_n4', '----')
            result_n3 = record.get('result_n3', '----')
            
            c4 = "#dc2626" if "🎯" in result_n4 else "#64748b"
            c3 = "#dc2626" if "🎯" in result_n3 else "#64748b"
            
            links_html += f"""
            <a href="archive/numbers_{kai_num}.html" style="display: block; background: white; padding: 15px; margin-bottom: 10px; border-radius: 8px; text-decoration: none; color: #333; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); transition: transform 0.2s;">
                <div style="font-weight: bold; color: #1e3a8a; font-size: 18px; border-bottom: 1px dashed #e2e8f0; padding-bottom: 5px; margin-bottom: 8px;">{kai_str}</div>
                <div style="display:flex; justify-content:space-between; font-size: 14px;">
                    <div style="width:48%;">
                        <div style="color: #16a34a; font-weight:bold;">N4: {actual_n4}</div>
                        <div style="color: {c4}; font-weight:bold; font-size:12px;">AI: {result_n4}</div>
                    </div>
                    <div style="width:48%; border-left:1px solid #e2e8f0; padding-left:10px;">
                        <div style="color: #e11d48; font-weight:bold;">N3: {actual_n3}</div>
                        <div style="color: {c3}; font-weight:bold; font-size:12px;">AI: {result_n3}</div>
                    </div>
                </div>
            </a>
            """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>ナンバーズ 過去の当選番号とAI予想成績アーカイブ一覧</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; background-color: #f0f4f8; padding: 20px; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .ad-pc {{ display: block; }} .ad-sp {{ display: none; }}
        @media (max-width: 600px) {{ .ad-pc {{ display: none; }} .ad-sp {{ display: block; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1 style="color: #1e3a8a; text-align: center; border-bottom: 3px solid #1e3a8a; padding-bottom: 10px;">📊 ナンバーズ 過去データ＆AI分析一覧</h1>
        
        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <div class="ad-pc">{imobile_ad2_pc}</div>
            <div class="ad-sp">{imobile_ad2_sp}</div>
        </div>

        <p style="text-align: center; margin-bottom: 30px; color:#475569;">過去のすべての抽選結果と、当サイトのAIが予想した成績の振り返りを記録しています。</p>
        {links_html}
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="index.html" style="display:inline-block; background: #3b82f6; color: white; padding: 12px 25px; border-radius: 30px; text-decoration: none; font-weight: bold;">◀ トップページへ戻る</a>
        </div>
    </div>
    {imobile_overlay}
</body>
</html>"""

    with open("archive_numbers.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def generate_sitemap(archive_urls):
    """サイトマップを更新する（ナンバーズのアーカイブURLを追記）"""
    sitemap_path = "sitemap.xml"
    existing_content = ""
    if os.path.exists(sitemap_path):
        with open(sitemap_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

    base_urls = [
        "https://loto-yosou-ai.com/index.html",
        "https://loto-yosou-ai.com/loto7.html",
        "https://loto-yosou-ai.com/loto6.html",
        "https://loto-yosou-ai.com/numbers.html",
        "https://loto-yosou-ai.com/archive_loto7.html",
        "https://loto-yosou-ai.com/archive_loto6.html",
        "https://loto-yosou-ai.com/archive_numbers.html", # 追加
    ]
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for url in base_urls:
        xml_content += "  <url>\n"
        xml_content += f"    <loc>{url}</loc>\n"
        xml_content += f"    <lastmod>{today}</lastmod>\n"
        priority = "1.0" if "archive/" not in url else "0.8"
        xml_content += f"    <priority>{priority}</priority>\n"
        xml_content += "  </url>\n"

    for url in archive_urls:
        xml_content += "  <url>\n"
        xml_content += f"    <loc>{url}</loc>\n"
        xml_content += f"    <lastmod>{today}</lastmod>\n"
        xml_content += f"    <priority>0.6</priority>\n"
        xml_content += "  </url>\n"
        
    xml_content += '</urlset>'
    
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"✅ sitemap.xml を更新しました（ナンバーズアーカイブ追加）")
# ==========================================
# ▲▲▲ 新規追加：ここまで ▲▲▲
# ==========================================

# --- 5. HTML構築 ---
def build_html():
    history_data = fetch_both_history()
    latest_data = history_data[0]

    # ⭕ ▼▼▼ この2行が消えているので追加してください ▼▼▼ ⭕
    n4_hot, n4_cold = analyze_digit_trends(history_data, 'n4_win')
    n3_hot, n3_cold = analyze_digit_trends(history_data, 'n3_win')
    # ⭕ ▲▲▲ ここまで ▲▲▲ ⭕
    
    # ★新設した高度な複合分析ロジックを使用 (N4とN3それぞれで生成)
    n4_preds, n4_rank, n4_msg, n4_top_str = generate_advanced_predictions(history_data, 4, 'n4_win')
    n3_preds, n3_rank, n3_msg, n3_top_str = generate_advanced_predictions(history_data, 3, 'n3_win')
    
    # 総合的なメッセージを合成（SNS投稿用などに後で使えます）
    global global_confidence_rank, global_confidence_msg
    global_confidence_rank = f"N4: {n4_rank} / N3: {n3_rank}"
    global_confidence_msg = f"{n4_msg}\n{n3_msg}"

    history_record = manage_history(latest_data, n4_preds, n3_preds)

    # ▼▼▼ 新規追加：マイ予想チェッカー用のデータ作成 ▼▼▼
    # top_nums_str は "1桁目の「8」" のような形式なので数字だけを抽出
    def extract_num(text):
        m = re.search(r'「(\d+)」', text)
        return m.group(1) if m else ""

    checker_data = {
        "n4": {
            "hot_nums": [str(n) for n, c in n4_hot],
            "cold_nums": [str(n) for n, c in n4_cold],
            "top_num": extract_num(n4_top_str)
        },
        "n3": {
            "hot_nums": [str(n) for n, c in n3_hot],
            "cold_nums": [str(n) for n, c in n3_cold],
            "top_num": extract_num(n3_top_str)
        }
    }
    checker_json = json.dumps(checker_data)
    # ▲▲▲ 追加ここまで ▲▲▲

    next_date_str = get_next_numbers_date()
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【{history_record[0]['target_kai']}】ナンバーズ3＆4当選予想・データ分析 | 最新AI予想</title>
    <link rel="icon" type="image/png" href="favicon.icon.png">
    <link rel="apple-touch-icon" href="favicon.icon.png">
    <meta name="description" content="{history_record[0]['target_kai']}のナンバーズ3・ナンバーズ4当選予想。過去3年分の出現傾向（HOT/COLD）から導き出した完全無料のAI予想とストレート/ボックス推奨を公開中！">
    <meta property="og:title" content="【{history_record[0]['target_kai']}】ナンバーズ3＆4最新AI予想">
    <meta property="og:description" content="過去3年分の出現傾向から導き出した完全無料のAI予想と推奨の買い方を公開中！">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://loto-yosou-ai.com/numbers.html">
    <meta property="og:image" content="https://loto-yosou-ai.com/Lotologo001.png">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="canonical" href="https://loto-yosou-ai.com/numbers.html">
    <link rel="canonical" href="https://loto-yosou-ai.com/numbers.html">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; padding: 10px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ 
    color: #1e3a8a; 
    padding: 12px 12px; /* 👈 上下の余白を12px、左右の余白を12pxに縮小 */
    font-size: 14px;    /* 👈 文字サイズを少し小さく指定（元は未指定＝16px相当） */
    text-decoration: none; 
    font-weight: bold; 
    border-bottom: 3px solid transparent; 
    transition: all 0.3s; 
}}
        nav a.active {{ border-bottom: 3px solid #16a34a; color: #16a34a; }}
        nav a:hover {{ background-color: #f0f4f8; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #16a34a; border-bottom: 2px solid #dcfce7; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; }}
        .prediction-box {{ background-color: #f0fdf4; border: 2px solid #bbf7d0; border-radius: 12px; padding: 25px; margin-bottom: 20px;}}
        .numbers-row {{ background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; align-items: center; flex-wrap: wrap; }}
        .row-label {{ font-size: 18px; font-weight: bold; color: #1e3a8a; background-color: #e0e7ff; padding: 5px 15px; border-radius: 4px; margin-right: 20px; min-width: 60px; text-align: center; }}
        .ball-container {{ display: flex; gap: 12px; flex-wrap: wrap; margin-right: auto;}}
        .ball {{ display: inline-flex; justify-content: center; align-items: center; width: 45px; height: 45px; background: linear-gradient(135deg, #22c55e, #16a34a); color: white; border-radius: 8px; font-size: 24px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.3); }}
        .recommend-tag {{ font-size: 14px; font-weight: bold; padding: 4px 10px; border-radius: 20px; margin-left: 10px; white-space: nowrap;}}
        .tag-straight {{ background-color: #fee2e2; color: #ef4444; border: 1px solid #fca5a5;}}
        .tag-box {{ background-color: #e0f2fe; color: #0ea5e9; border: 1px solid #7dd3fc;}}
        
        @media (max-width: 600px) {{ 
            .numbers-row {{ flex-direction: column; align-items: flex-start; padding: 15px; gap: 10px; }} 
            .row-label {{ margin-right: 0; margin-bottom: 5px; }} 
            .ball-container {{ margin-right: 0; gap: 8px; }}
            .ball {{ width: 36px; height: 36px; font-size: 18px; border-radius: 6px; }} 
            .recommend-tag {{ margin-left: 0; margin-top: 5px; font-size: 12px; align-self: flex-start; }} 
        }}
        
        .hc-container {{ display: flex; gap: 20px; flex-wrap: wrap; }}
        .hc-box {{ flex: 1; min-width: 250px; padding: 15px; border-radius: 8px; }}
        .hot-box {{ background-color: #fee2e2; border: 1px solid #fca5a5; }}
        .cold-box {{ background-color: #e0f2fe; border: 1px solid #7dd3fc; }}
        .hc-title {{ font-weight: bold; margin-bottom: 10px; }}
        .hc-number {{ display: inline-block; padding: 5px 15px; margin: 3px; border-radius: 4px; font-weight: bold; background: white; font-size: 18px;}}
        .hot-box .hc-number {{ color: #ef4444; border: 1px solid #ef4444; }}
        .cold-box .hc-number {{ color: #0ea5e9; border: 1px solid #0ea5e9; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: center; }}
        th, td {{ padding: 12px; border-bottom: 1px solid #e2e8f0; }}
        th {{ background-color: #f8fafc; color: #475569; font-weight: bold; }}
        .result-win {{ color: #16a34a; font-weight: bold; background-color: #dcfce7; padding: 4px 8px; border-radius: 4px; display: inline-block; white-space: nowrap; margin-top: 4px; }}
        .result-lose {{ color: #94a3b8; display: inline-block; margin-top: 4px; }}
        .scroll-table-container {{ max-height: 400px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 15px; }}
        .scroll-table-container table {{ margin-top: 0; border-collapse: separate; border-spacing: 0; }}
        .scroll-table-container th {{ position: sticky; top: 0; z-index: 1; box-shadow: 0 2px 2px -1px rgba(0,0,0,0.1); }}
        footer {{ background-color: #1e293b; color: #94a3b8; text-align: center; padding: 40px 20px; margin-top: 60px; font-size: 13px; border-top: 4px solid #3b82f6; }}
        .footer-links {{ margin-bottom: 15px; }}
        .footer-links a {{ color: #cbd5e1; text-decoration: none; margin: 0 10px; transition: color 0.2s; }}
        .footer-links a:hover {{ color: white; text-decoration: underline; }}
        /* PC用とスマホ用の広告を自動で切り替える魔法のCSS */
.ad-pc {{ display: block; }}
.ad-sp {{ display: none; }}

/* スマホ（画面幅600px以下）で見た時だけルールを逆転させる */
@media (max-width: 600px) {{
    .ad-pc {{ display: none; }}
    .ad-sp {{ display: block; }}
}}
    </style> 
    <meta name="google-site-verification" content="j3Smi9nkNu6GZJ0TbgFNi8e_w9HwUt_dGuSia8RDX3Y" />
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1431683156739681"
         crossorigin="anonymous"></script>
</head>
<body>
    <header>
        <a href="index.html" style="text-decoration: none;">
            <img src="Lotologo001.png" alt="宝くじ当選予想・データ分析ポータル" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">ナンバーズ当選予想・速報</div>
        </a>
    </header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html" class="active">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="column.html">攻略ガイド🔰</a>
        <a href="horoscope.html">占い🔮</a>
        <a href="archive.html" >YOUTUBE🎥</a>
    </nav>

<div class="section-card" style="text-align: center; background: linear-gradient(to right, #ffffff, #f8fafc); border: 2px solid #64748b; margin-top: 25px; margin-bottom: 30px; padding: 25px 15px; border-radius: 12px;">
        <h3 style="color: #334155; margin-top: 0; font-size: 20px; font-weight: bold;">📊 最新の当せん詳細データ</h3>
        <a href="numbers_detail.html" style="display: inline-block; background-color: #1e293b; color: white; text-decoration: none; padding: 15px 35px; border-radius: 30px; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(30, 41, 59, 0.3); transition: transform 0.2s;">
            🔍 詳細ページを確認する
        </a>
    </div>

    <div class="container">
    
        <div style="text-align: center; margin: 20px 0;">
    <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
    
    <!-- ▼ PCで見ている時だけ表示されるタグ1 ▼ -->
    <div class="ad-pc">
        <div id="im-839c9bd971c54d348a71dcbfed7984d3">
  <script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script>
  <script>(window.adsbyimobile=window.adsbyimobile||[]).push({{pid:84847,mid:592459,asid:1929932,type:"banner",display:"inline",elementid:"im-839c9bd971c54d348a71dcbfed7984d3"}})</script>
</div>
    </div>
    
    <!-- ▼ スマホで見ている時だけ表示されるタグ1 ▼ -->
    <div class="ad-sp">
        <div id="im-4b18f7a610e54053ae1a96fafd113652">
  <script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script>
  <script>(window.adsbyimobile=window.adsbyimobile||[]).push({{pid:84847,mid:592460,asid:1929934,type:"banner",display:"inline",elementid:"im-4b18f7a610e54053ae1a96fafd113652"}})</script>
</div>
    </div>
</div>

        <div class="section-card" style="background: linear-gradient(to right, #ffffff, #f0fdf4); border-left: 5px solid #16a34a; padding: 20px;">
            <div style="font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 10px;">⏰ 次回抽選日と購入期限</div>
            <div style="font-size: 15px; color: #475569;">
                <span style="display:inline-block; margin-right: 20px;">次回抽選: <strong style="color: #16a34a; font-size: 18px;">{next_date_str}</strong></span>
                <span style="display:inline-block;">購入期限: 当日 <strong style="color: #ef4444; font-size: 18px;">18:30</strong> まで</span>
            </div>
            <div style="font-size:11px; color:#64748b; margin-top: 5px;">※ネット購入（楽天銀行等）の原則的な締め切り時間です。</div>
        </div>

        <div class="section-card" style="text-align: center; background: linear-gradient(to right, #ffffff, #f0fdf4); border: 2px solid #22c55e; margin-bottom: 30px;">
            <h3 style="color: #15803d; margin-top: 0; font-size: 20px;">📱 最新のAI予想をLINEでお届け！</h3>
            <p style="font-size: 15px; color: #475569; margin-bottom: 20px;">
                抽選日の朝に「今日の予想」を直接スマホにお知らせします。<br>
                買い忘れ防止や、キャリーオーバーの速報受け取りにぜひ登録してください！
            </p>
            
            <a href="https://lin.ee/rKXCkr3" style="display: inline-block; background-color: #06C755; color: white; text-decoration: none; padding: 15px 35px; border-radius: 30px; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(6, 199, 85, 0.3); transition: transform 0.2s;">
                💬 LINEで無料通知を受け取る
            </a>
        </div>

        <div class="section-card">
            <h2 class="section-header">🎯 次回 ({history_record[0]['target_kai']}) ナンバーズ4 予想</h2>
            <p>直近約3年間の傾向を3つのAIが分析する独自のアルゴリズム予想です。</p>
            <div class="prediction-box">
"""
    # ★予想A〜Eの5つに対応するため、配列の要素数を拡張
    labels = ['予想A', '予想B', '予想C', '予想D', '予想E']
    tags4 = ['<span class="recommend-tag tag-straight">ストレート推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>']
    for i, pred in enumerate(history_record[0]['n4_preds']):
        balls = "".join([f'<span class="ball">{n}</span>' for n in pred])
        html += f'                <div class="numbers-row"><div class="row-label">{labels[i]}</div><div class="ball-container">{balls}</div>{tags4[i]}</div>\n'
    
    html += f"""            </div>
            <h2 class="section-header" style="margin-top: 40px;">🎯 次回 ({history_record[0]['target_kai']}) ナンバーズ3 予想</h2>
            <div class="prediction-box">
"""
    # ★こちらも同様に5つに拡張
    tags3 = ['<span class="recommend-tag tag-straight">ストレート推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>', '<span class="recommend-tag tag-box">ミニ推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>']
    for i, pred in enumerate(history_record[0]['n3_preds']):
        balls = "".join([f'<span class="ball">{n}</span>' for n in pred])
        html += f'                <div class="numbers-row"><div class="row-label">{labels[i]}</div><div class="ball-container">{balls}</div>{tags3[i]}</div>\n'
    
    # ▼▼▼ 修正箇所：ナンバーズ3の予想が終わった直後に、解説ブロックを挿入します ▼▼▼
    html += f"""            </div>
            
            <div style="background-color: #f8fafc; border-left: 5px solid #16a34a; padding: 20px; border-radius: 8px; margin-top: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <h3 style="color: #15803d; margin-top: 0; font-size: 18px; display: flex; align-items: center;">
                    <span style="font-size: 22px; margin-right: 8px;">🤖</span> AI予測ロジック解説（当サイト独自）
                </h3>
                <p style="font-size: 15px; color: #475569; line-height: 1.7; margin-bottom: 12px;">
                    今回の予測は、過去の膨大なデータを基に、<strong>「Random Forest」「XGBoost」「LSTM（ディープラーニング）」</strong>という3つの異なる最先端AIモデルを用いて、各桁ごとの出現確率と数字同士の共起性を多角的に算出しました。
                </p>
                <div style="background-color: #f0fdf4; padding: 12px 15px; border-radius: 6px; margin-bottom: 12px; border: 1px dashed #bbf7d0;">
                    <strong style="color: #16a34a; font-size: 16px;">🎯 ナンバーズ4 AI判定：{n4_rank}</strong><br>
                    <span style="color: #15803d; font-weight: bold; display: block; margin-bottom: 5px;">{n4_msg}</span>
                    <span style="color: #e11d48; font-weight: bold; font-size: 14px; display: block; margin-bottom: 12px;">🔥 特注HOT数字: {n4_top_str}</span>
                    
                    <strong style="color: #ea580c; font-size: 16px;">🎯 ナンバーズ3 AI判定：{n3_rank}</strong><br>
                    <span style="color: #c2410c; font-weight: bold; display: block; margin-bottom: 5px;">{n3_msg}</span>
                    <span style="color: #e11d48; font-weight: bold; font-size: 14px; display: block;">🔥 特注HOT数字: {n3_top_str}</span>
                </div>
                <p style="font-size: 15px; color: #475569; line-height: 1.7; margin-bottom: 0;">
                    当サイトのAIは各桁ごとのトレンドの波を複合的にスコアリングしています。上記の特注数字を軸に構成された<strong>【予想A】</strong>が、当サイトの最もおすすめな本命予想です！
                </p>
            </div>

            <!-- ▼▼▼ 新規追加：マイ予想チェッカー UIとJS (ナンバーズ版) ▼▼▼ -->
            <div style="background-color: #ffffff; border: 2px solid #16a34a; padding: 25px; border-radius: 12px; margin-top: 30px; box-shadow: 0 4px 15px rgba(22, 163, 74, 0.1);">
                <h3 style="color: #15803d; margin-top: 0; font-size: 20px; text-align: center;">🤔 あなたの数字は当たる？<br>マイ予想チェッカー</h3>
                <p style="font-size: 14px; color: #64748b; text-align: center; margin-bottom: 20px;">買おうとしている数字を選んで、AIの期待値スコアをチェックしてみましょう！</p>
                
                <!-- タブ切り替え -->
                <div style="display: flex; justify-content: center; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0;">
                    <button id="tab-n4" style="background: none; border: none; padding: 10px 20px; font-size: 16px; font-weight: bold; color: #16a34a; border-bottom: 3px solid #16a34a; cursor: pointer;">ナンバーズ4</button>
                    <button id="tab-n3" style="background: none; border: none; padding: 10px 20px; font-size: 16px; font-weight: bold; color: #94a3b8; border-bottom: 3px solid transparent; cursor: pointer;">ナンバーズ3</button>
                </div>

                <!-- ダイヤルUI表示エリア -->
                <div id="dial-area" style="display: flex; justify-content: center; gap: 15px; margin-bottom: 20px;">
                    <!-- JSで桁数分のダイヤルを生成 -->
                </div>
                
                <div style="text-align: center; margin-bottom: 20px;">
                    <button id="btn-check" style="background: #16a34a; color: white; border: none; padding: 12px 40px; border-radius: 30px; font-weight: bold; font-size: 18px; cursor: pointer; box-shadow: 0 4px 10px rgba(22, 163, 74, 0.3);">AIで判定する</button>
                </div>
                
                <!-- 判定結果表示エリア -->
                <div id="checker-result" style="display: none; background: #f0fdf4; border: 2px dashed #86efac; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 16px; color: #15803d; font-weight: bold; margin-bottom: 10px;">AI総合判定</div>
                    <div id="result-rank" style="font-size: 32px; font-weight: 900; color: #dc2626; margin-bottom: 10px; letter-spacing: 2px;"></div>
                    <div id="result-comment" style="font-size: 15px; color: #475569; line-height: 1.6;"></div>
                </div>
            </div>

            <script>
                const aiData = {checker_json};
                let currentMode = 'n4'; // 'n4' or 'n3'
                
                const tabN4 = document.getElementById('tab-n4');
                const tabN3 = document.getElementById('tab-n3');
                const dialArea = document.getElementById('dial-area');
                const btnCheck = document.getElementById('btn-check');
                const resultArea = document.getElementById('checker-result');
                const resultRank = document.getElementById('result-rank');
                const resultComment = document.getElementById('result-comment');

                // ダイヤルUIを生成する関数
                function renderDials(length) {{
                    dialArea.innerHTML = '';
                    for(let i=0; i<length; i++) {{
                        const container = document.createElement('div');
                        container.style.cssText = 'display:flex; flex-direction:column; align-items:center; width:60px;';
                        
                        const btnUp = document.createElement('button');
                        btnUp.innerHTML = '▲';
                        btnUp.style.cssText = 'background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px 4px 0 0; width:100%; padding:8px 0; cursor:pointer; color:#475569;';
                        
                        const display = document.createElement('div');
                        display.innerText = '0';
                        display.className = 'digit-display'; // 値取得用のクラス
                        display.style.cssText = 'font-size:32px; font-weight:900; padding:10px 0; width:100%; text-align:center; border-left:1px solid #cbd5e1; border-right:1px solid #cbd5e1; background:#fff; color:#1e293b;';
                        
                        const btnDown = document.createElement('button');
                        btnDown.innerHTML = '▼';
                        btnDown.style.cssText = 'background:#f1f5f9; border:1px solid #cbd5e1; border-radius:0 0 4px 4px; width:100%; padding:8px 0; cursor:pointer; color:#475569;';

                        // 数字の増減ロジック
                        btnUp.onclick = () => {{
                            let val = parseInt(display.innerText);
                            display.innerText = val === 9 ? 0 : val + 1;
                            resultArea.style.display = 'none'; // 変更したら結果を隠す
                        }};
                        btnDown.onclick = () => {{
                            let val = parseInt(display.innerText);
                            display.innerText = val === 0 ? 9 : val - 1;
                            resultArea.style.display = 'none';
                        }};

                        container.appendChild(btnUp);
                        container.appendChild(display);
                        container.appendChild(btnDown);
                        dialArea.appendChild(container);
                    }}
                }}

                // 初期描画 (N4)
                renderDials(4);

                // タブ切り替え処理
                tabN4.onclick = () => {{
                    currentMode = 'n4';
                    tabN4.style.color = '#16a34a'; tabN4.style.borderBottomColor = '#16a34a';
                    tabN3.style.color = '#94a3b8'; tabN3.style.borderBottomColor = 'transparent';
                    renderDials(4);
                    resultArea.style.display = 'none';
                }};
                tabN3.onclick = () => {{
                    currentMode = 'n3';
                    tabN4.style.color = '#94a3b8'; tabN4.style.borderBottomColor = 'transparent';
                    tabN3.style.color = '#e11d48'; tabN3.style.borderBottomColor = '#e11d48'; // N3は赤系
                    renderDials(3);
                    resultArea.style.display = 'none';
                }};

                // 判定処理
                btnCheck.onclick = () => {{
                    // 現在のダイヤルの値を取得
                    const displays = document.querySelectorAll('.digit-display');
                    const selectedNums = Array.from(displays).map(d => d.innerText);
                    
                    const targetData = aiData[currentMode];
                    let hotMatch = 0;
                    let hasTop = false;

                    selectedNums.forEach(numStr => {{
                        if(targetData.hot_nums.includes(numStr)) hotMatch++;
                        if(targetData.top_num === numStr) hasTop = true;
                    }});

                    let rank = "Cランク";
                    let comment = "";

                    if(hasTop && hotMatch >= 2) {{
                        rank = "Sランク 🔥";
                        comment = "完璧なチョイスです！AI特注数字が組み込まれ、出現トレンドにも完全に合致しています。ストレートでの購入を強く推奨します！";
                    }} else if (hotMatch >= 1 || hasTop) {{
                        rank = "Aランク ✨";
                        comment = "非常に良い組み合わせです。トレンドの波に乗っています。ボックスも押さえておくと安心です。";
                    }} else {{
                        rank = "Bランク 💡";
                        comment = "AIのトレンドからは少し外れています。あえて裏をかくならOKですが、当サイトの『予想A』の数字をいくつか混ぜると期待値が上がります。";
                    }}

                    resultRank.innerText = rank;
                    resultComment.innerText = comment;
                    
                    // 色の切り替え（N4は緑、N3は赤）
                    const themeColor = currentMode === 'n4' ? '#15803d' : '#be123c';
                    const bgColor = currentMode === 'n4' ? '#f0fdf4' : '#fff1f2';
                    const borderColor = currentMode === 'n4' ? '#86efac' : '#fecdd3';
                    
                    resultArea.style.background = bgColor;
                    resultArea.style.borderColor = borderColor;
                    resultArea.querySelector('div').style.color = themeColor;

                    resultArea.style.display = 'block';
                    resultArea.scrollIntoView({{behavior: "smooth", block: "center"}});
                }};
            </script>
            <!-- ▲▲▲ 新規追加 ここまで ▲▲▲ -->

        <div class="section-card">
            <h2 class="section-header" style="color: #475569; border-bottom: 2px solid #e2e8f0;">🔔 最新の抽選結果 ({latest_data['kai']} - {latest_data['date']})</h2>
            <table style="margin-bottom: 0;">
                <thead><tr><th>ナンバーズ4</th><th>ナンバーズ3</th></tr></thead>
                <tbody>
                    <tr>
                        <td style="font-size:28px; font-weight: bold; letter-spacing: 6px; color:#16a34a;">{latest_data['n4_win']}</td>
                        <td style="font-size:28px; font-weight: bold; letter-spacing: 6px; color:#d97706;">{latest_data['n3_win']}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section-card">
            <h2 class="section-header">📊 直近の出現傾向 (HOT & COLD)</h2>
            
            <h3 style="color: #16a34a; font-size: 18px; margin-top: 10px; border-left: 4px solid #16a34a; padding-left: 10px;">■ ナンバーズ4 の傾向</h3>
            <div class="hc-container" style="margin-bottom: 25px;">
                <div class="hc-box hot-box"><div class="hc-title">🔥 よく出ている数字</div>\n"""
    for n, count in n4_hot: html += f'<span class="hc-number">{n} ({count}回)</span>'
    html += """</div>\n                <div class="hc-box cold-box"><div class="hc-title">❄️ 出ていない数字</div>\n"""
    for n, count in n4_cold: html += f'<span class="hc-number">{n} ({count}回)</span>'
    html += """</div>
            </div>

            <h3 style="color: #d97706; font-size: 18px; margin-top: 10px; border-left: 4px solid #d97706; padding-left: 10px;">■ ナンバーズ3 の傾向</h3>
            <div class="hc-container">
                <div class="hc-box hot-box" style="background-color: #fffbeb; border-color: #fde68a;"><div class="hc-title" style="color: #d97706;">🔥 よく出ている数字</div>\n"""
    for n, count in n3_hot: html += f'<span class="hc-number" style="color: #d97706; border-color: #d97706;">{n} ({count}回)</span>'
    html += """</div>\n                <div class="hc-box cold-box" style="background-color: #fafaf9; border-color: #e7e5e4;"><div class="hc-title" style="color: #57534e;">❄️ 出ていない数字</div>\n"""
    for n, count in n3_cold: html += f'<span class="hc-number" style="color: #57534e; border-color: #57534e;">{n} ({count}回)</span>'
    html += """</div>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">📝 当サイトの予想と成績履歴</h2>
            <div class="scroll-table-container">
            <table>
                <thead><tr><th>対象回号</th><th>N4 成績</th><th>N3 成績</th></tr></thead>
                <tbody>\n"""
    for record in history_record:
        r4_class = "result-win" if "🎯" in record.get('result_n4', '') else "result-lose"
        r3_class = "result-win" if "🎯" in record.get('result_n3', '') else "result-lose"
        html += f"""                    <tr>
                        <td style="font-weight:bold; color:#1e3a8a;">{record.get('target_kai', '----')}</td>
                        <td>実績: <span style="font-weight:bold;">{record.get('actual_n4', '----')}</span><br><span class="{r4_class}">{record.get('result_n4', '----')}</span></td>
                        <td>実績: <span style="font-weight:bold;">{record.get('actual_n3', '---')}</span><br><span class="{r3_class}">{record.get('result_n3', '----')}</span></td>
                    </tr>\n"""
    html += f"""                </tbody>
            </table>
            </div>
        </div>

        <!-- 👇広告の表示部分👇 -->
        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            
            <div class="ad-pc">
                {imobile_ad2_pc}
            </div>
            
            <div class="ad-sp">
                {imobile_ad2_sp}
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">📅 過去の当選番号一覧 (実際のデータ)</h2>
            <p style="font-size: 14px; color: #64748b;">※楽天宝くじの直近データ（過去1年分）</p>
            <div class="scroll-table-container">
                <table>
                    <thead>
                        <tr><th>回号 (抽選日)</th><th>ナンバーズ4</th><th>ナンバーズ3</th></tr>
                    </thead>
                    <tbody>\n"""
    for row in history_data:
        html += f"""                        <tr>
                            <td style="font-weight:bold; color:#1e3a8a;">{row['kai']}<br><span style="font-size:12px; font-weight:normal; color:#666;">({row['date']})</span></td>
                            <td style="font-size:18px; font-weight:bold; letter-spacing:3px;">{row['n4_win']}</td>
                            <td style="font-size:18px; font-weight:bold; letter-spacing:3px;">{row['n3_win']}</td>
                        </tr>\n"""
    html += f"""                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- 👇広告の表示部分👇 -->
    <div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        
        <div class="ad-pc">
            {imobile_ad3_pc}
        </div>
        
        <div class="ad-sp">
            {imobile_ad3_sp}
        </div>
    </div>

    <footer>
        <div class="footer-links">
            <a href="about.html">運営者情報</a> |
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p>※当サイトの予想・データは当選を保証するものではありません。宝くじの購入は自己責任でお願いいたします。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 宝くじ当選予想・データ分析ポータル All Rights Reserved.</p>
    </footer>

        {imobile_overlay}

</body>
</html>"""

    # --- ⭐️ 【改良版】自動ポスト・LINE配信ロジック ⭐️ ---
    import datetime
    
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today_weekday = now.weekday()
    current_hour = now.hour
    
    next_kai = history_record[0]['target_kai']
    site_url = "https://loto-yosou-ai.com/numbers.html" 
    
    send_flag = False
    msg = ""

    # ■ 平日 (月〜金) の処理（LINE用）
    if today_weekday < 5:
        if current_hour < 19:
            pass 
        else:
            finished_record = history_record[1] if len(history_record) > 1 else history_record[0]
            finished_kai = finished_record['target_kai']
            n3_res = finished_record.get('result_n3', '')  
            n4_res = finished_record.get('result_n4', '')  
            
            # 「的中」という言葉が含まれている場合のみLINEフラグを立てる
            if "的中" in n3_res or "的中" in n4_res:
                send_flag = True
                msg = f"【#ナンバーズ 的中速報🎯】\n第 {finished_kai} 回でAI予想が的中しました！\n"
                msg += f"・ナンバーズ3：{n3_res}\n・ナンバーズ4：{n4_res}\n"
                msg += f"\n的中した具体的な数字と、明日({next_kai})の最新予想はこちら👇\n{site_url}"

    # ■ 土曜日 (5) の夜に週末通知（LINE用）
    elif today_weekday == 5:
        if current_hour >= 19:
            send_flag = True
            msg = f"【#ナンバーズ 週末の予想更新🎯】\n来週、 {next_kai} 回からの最新AI予想を公開しました！\n"
            msg += f"\n週末の間に最新の出現傾向データをチェックして、次回の戦略を立てましょう👇\n{site_url}"

    # ■ 日曜日 (6) はLINE送付なし
    else:
        pass

    # ▼▼▼ 追加：SNS（動画・画像）用の配信判定を独立させる ▼▼▼
    sns_send_flag = False
    sns_msg = msg  

    # 抽選日は月〜金。SNS投稿はその「前日の夜（日・月・火・水・木）」に行う
    if today_weekday in [6, 0, 1, 2, 3] and current_hour >= 19:
        sns_send_flag = True
        # LINE送信用メッセージが空の場合は、SNS専用の告知メッセージを作成
        if not sns_msg:
            sns_msg = f"【明日は #ナンバーズ 抽選日🎯】\n明日 {next_kai} の最新AI予想を無料公開中！\n\n各桁の出現傾向を解析したAIの「激アツ数字」はこちら👇\n{site_url}"
    # ▲▲▲ ここまで ▲▲▲

    # --- 配信の実行（LINEとSNSを完全に分離） ---
    
    # ① LINEの送信処理（条件は一切変更なし）
    if send_flag and msg:
        post_to_line(msg)
        print("✅ LINEへの自動配信を実行しました。")
    else:
        print("💤 ナンバーズ：LINE配信対象外のためスキップしました。")

    # ② SNS（動画・画像・Threads・TikTok）の送信処理
    if sns_send_flag and sns_msg:
        print(f"📅 本日はSNS投稿タイミング（曜日:{today_weekday}、{current_hour}時台）のため、SNSへ投稿します。")
        post_to_threads(sns_msg)
        
        base_image = "base_image.png"     
        image_path = "numbers_result.jpg"
        
        # 数字を職人に渡すために取り出す
        n4_yosou_a = history_record[0]['n4_preds'][0]
        n3_yosou_a = history_record[0]['n3_preds'][0]
        
        caption = f"🎯最新のナンバーズ AI予想です！\n\n{sns_msg}\n\n#ナンバーズ #宝くじ #AI予想 #ロトナンバーズ攻略局"
        
        # 🌟 静止画の生成
        is_created = create_result_image(n4_yosou_a, n3_yosou_a, base_image, image_path, target_kai=next_kai, target_date=next_date_str, n4_rank=n4_rank, n3_rank=n3_rank)

        # 🌟 動画の生成と各SNSへの投稿
        try:
            from create_reel import generate_numbers_reel
            generate_numbers_reel(n4_yosou=n4_yosou_a, n3_yosou=n3_yosou_a, target_kai=next_kai, target_date=next_date_str)
            print(f"✅ 本物のデータでリール生成完了！")
            
            video_url = upload_video_to_cloudinary("reel_numbers.mp4")
            if video_url:
                post_reel_to_instagram(video_url, caption)
                
            yt_title = "🎯 明日のナンバーズ激アツAI予想！ #shorts"
            yt_tags = ["ナンバーズ", "宝くじ", "AI予想", "ショート"]
            upload_to_youtube_shorts("reel_numbers.mp4", yt_title, caption, yt_tags)

            post_to_tiktok("reel_numbers.mp4", caption)
            
        except Exception as e:
            print(f"❌ 動画の自動生成・投稿エラー: {e}")
            
        # 🌟 画像のInstagram投稿
        if is_created:
            public_image_url = upload_image_to_server(image_path)
            if public_image_url:
                post_to_instagram(public_image_url, caption)
            else:
                print("⚠️ 画像のURL化に失敗しました。")
    else:
        print("💤 ナンバーズ：SNS動画配信対象外のためスキップしました。")

    return html

if __name__ == "__main__":
    final_html = build_html()

# === ▼ 修正・追加：numbers.htmlの成績表の下に「アーカイブ一覧」ボタンを挿入 ▼ ===
    insertion_target = "</tbody>\n            </table>\n            </div>"
    insertion_button = """</tbody>
            </table>
            </div>
            
            <!-- ▼ 追加：アーカイブ一覧への導線ボタン ▼ -->
            <div style="text-align: center; margin-top: 25px;">
                <a href="archive_numbers.html" style="display: inline-block; background-color: #f8fafc; color: #1e3a8a; border: 2px solid #3b82f6; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; transition: all 0.3s; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    📚 過去の全成績と分析データ一覧を見る ＞
                </a>
            </div>
            <!-- ▲ 追加ここまで ▲ -->"""
    final_html = final_html.replace(insertion_target, insertion_button)
    # === ▲ 修正・追加ここまで ▲ ===

    with open('numbers.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
        real_data = get_numbers_full_detail()
    generate_numbers_detail_page(real_data)

# ▼▼▼ 新規追加：アーカイブ・サイトマップ自動生成処理 ▼▼▼
    print("📈 SEO用アーカイブページ・サイトマップの構築を開始します...")
    history_records = load_history_from_jsonbin()
    generated_archive_urls = generate_archive_detail_pages(history_records)
    generate_archive_index_page(history_records)
    generate_sitemap(generated_archive_urls)
    print("✨ SEO用アーカイブ構築が完了しました！")
    # ▲▲▲ 新規追加：ここまで ▲▲▲

    # ==========================================
    # 🎬 【追加】動画作成用のJSONデータを出力する (ナンバーズ版)
    # =========================================
    try:
        # JSONBinから最新の履歴を直接取得する！
        history = load_history_from_jsonbin()
        latest_pred = history[0] if history else {}
        
        actual_n4_str = "".join(real_data.get("n4_numbers", []))
        actual_n3_str = "".join(real_data.get("n3_numbers", []))

        # 的中判定用の関数
        def eval_numbers(pred, actual):
            if not actual or actual == "----" or actual == "---": return "抽選待ち"
            if pred == actual: return "ストレート🎯"
            elif sorted(pred) == sorted(actual): return "ボックス🎯"
            return "ハズレ"

        video_export_data = {
            "round": real_data.get("round", ""),
            "date": real_data.get("date", ""),
            "n4_win": real_data.get("n4_numbers", []),
            "n4_prizes": real_data.get("n4_prizes", []),
            "n4_preds": [
                {
                    "name": f"予想{chr(65+i)}",
                    "nums": pred,
                    "result": eval_numbers(pred, actual_n4_str)
                } for i, pred in enumerate(latest_pred.get("n4_preds", []))
            ],
            "n3_win": real_data.get("n3_numbers", []),
            "n3_prizes": real_data.get("n3_prizes", []),
            "n3_preds": [
                {
                    "name": f"予想{chr(65+i)}",
                    "nums": pred,
                    "result": eval_numbers(pred, actual_n3_str)
                } for i, pred in enumerate(latest_pred.get("n3_preds", []))
            ]
        }
        with open('video_data_numbers.json', 'w', encoding='utf-8') as f:
            json.dump(video_export_data, f, ensure_ascii=False, indent=4)
        print("🎬 動画生成用の連携データ (video_data_numbers.json) を出力しました！")
    except Exception as e:
        print(f"⚠️ 動画用JSONの出力に失敗しました: {e}")
    # ==========================================
    print("✨ [自動取得・完全決着版] ナンバーズ3＆4 の自動更新とXへのポストが完了しました！")