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

def load_history_from_jsonbin():
    if not JSONBIN_BIN_ID: return []
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    try:
        # 通信のタイムアウトを10秒に設定
        res = requests.get(JSONBIN_URL, headers=headers, timeout=60)
        
        if res.status_code == 200:
            return res.json().get('record', [])
        else:
            # 🚨 ステータスコードが200以外（エラー）の場合は空配列を返さず、処理を止める！
            print(f"⚠️ JSONBin取得エラー: {res.status_code} - {res.text}")
            raise SystemExit("🚨 データの消失（サイレント上書き）を防ぐため、処理を強制終了しました。")
            
    except Exception as e:
        # 🚨 通信タイムアウトなどの場合も同様に強制終了させる
        print(f"⚠️ JSONBin通信エラー: {e}")
        raise SystemExit("🚨 データの消失（サイレント上書き）を防ぐため、処理を強制終了しました。")

def save_history_to_jsonbin(data):
    if not JSONBIN_BIN_ID: return
    headers = {"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}
    try:
        requests.put(JSONBIN_URL, json=data, headers=headers)
    except Exception as e: print(f"保存エラー: {e}")

# .envファイルを読み込む
load_dotenv()
# ▲▲▲ ここまで追加 ▲▲▲

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
        # 動画アップロード実行
        response = request.execute()
        video_id = response.get('id')
        print(f"🎉🎉🎉 YouTube Shortsの自動投稿が完了しました！ URL: https://youtu.be/{video_id} 🎉🎉🎉")
        
        # ▼▼▼ アップロード成功直後に、ここで固定コメントを追加！ ▼▼▼
        fixed_msg = (
            "🎯 本日のAI全予想はこちら（完全無料）！\n"
            "👉 https://loto-yosou-ai.com/\n\n"
            "次回の予想も見逃さないよう、チャンネル登録お願いします！✨"
        )
        add_pinned_comment(video_id, fixed_msg)
        # ▲▲▲ ここまで ▲▲▲
        
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

def create_result_image(n4_text, n3_text, base_image_path, output_image_path, target_kai="", target_date=""):
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
    title4 = "【ナンバーズ4 予想A】"
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
    title3 = "【ナンバーズ3 予想A】"
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

    # HTMLの組み立て（※CSSの波括弧は {{ }} と2つ重ねてエラーを回避しています）
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【{result_data.get('round', '')}】ナンバーズ3＆4 抽選結果詳細データ</title>
    <meta name="description" content="{result_data.get('round', '')}のナンバーズ3・ナンバーズ4の当せん金額・口数などの詳細データを公開しています。">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; padding: 10px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #1e3a8a; padding: 15px 20px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; }}
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
    </style> 
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
    </nav>

    <div class="container">
        <h1 style="color: #1e3a8a; font-size: 26px; text-align: center; border-bottom: 3px solid #1e3a8a; padding-bottom: 15px; margin-bottom: 30px;">
            {result_data.get('round', '')} ({result_data.get('date', '')}) 抽選結果詳細
        </h1>

        <div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <script src="https://adm.shinobi.jp/s/4275e4a786993be6d30206e03ec2de0f"></script>
        </div>

        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4RGVRU+4GLE+5ZU29" rel="nofollow">
                <img border="0" width="320" height="auto" alt="" src="https://www29.a8.net/svt/bgt?aid=260331146288&wid=002&eno=01&mid=s00000020813001007000&mc=1">
            </a>
            <img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=4AZSSQ+4RGVRU+4GLE+5ZU29" alt="">
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
    <a href="numbers.html" style="display: inline-block; background-color: #3b82f6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        ◀ ナンバーズ AI予想トップに戻る
    </a>
</div>

        <div style="text-align: center; margin-bottom: 40px;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4UG1SQ+3P7U+61JSH" rel="nofollow">
                <img border="0" width="300" height="250" alt="" src="https://www22.a8.net/svt/bgt?aid=260331146293&wid=002&eno=01&mid=s00000017265001015000&mc=1">
            </a>
            <img border="0" width="1" height="1" src="https://www14.a8.net/0.gif?a8mat=4AZSSQ+4UG1SQ+3P7U+61JSH" alt="">
        </div>

    </div>

    <footer>
        <div class="footer-links">
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p>※当サイトのデータは当選を保証するものではありません。宝くじの購入は自己責任でお願いいたします。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 宝くじ当選予想・データ分析ポータル All Rights Reserved.</p>
    </footer>
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
    print(f"🧠 AI（Random Forest）がナンバーズ{length}の『桁ごとの傾向』と共起性を学習中...")
    if not history_data or len(history_data) < 20:
        return [] 

    # 古い順（時系列）に並び替え、数字を整数のリストに変換
    draws = [[int(n) for n in d[win_key]] for d in reversed(history_data)]
    
    # --- 1. 共起性行列（一緒に選ばれやすい数字のペア） ---
    pair_counts = Counter()
    for draw in draws:
        # 順番を問わず、同じ回に出現した数字のペアをカウント
        for pair in itertools.combinations(sorted(draw), 2):
            pair_counts[pair] += 1

    # --- 2 & 3. 桁(ポジション)ごとの機械学習モデルの構築と予測 ---
    # ナンバーズは桁ごとに傾向が異なるため、各桁専用のAIモデルを個別に作ります
    pos_ml_scores = []
    window_size = 10 
    
    for pos in range(length):
        features = []
        labels = []
        
        # この桁(ポジション)だけの過去の出現履歴を抽出
        pos_sequence = [draw[pos] for draw in draws]
        
        for i in range(window_size, len(pos_sequence) - 1):
            past_window = pos_sequence[i-window_size:i]
            past_counts = Counter(past_window)
            
            target_digit = pos_sequence[i] 
            for num in range(10): # ナンバーズは0〜9
                feature = [past_counts.get(num, 0)]
                features.append(feature)
                labels.append(1 if num == target_digit else 0)

        X = np.array(features)
        y = np.array(labels)

        # Random Forestモデルの学習
        model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
        
        # データが偏りすぎて1種類しかない場合のエラー回避
        if len(np.unique(y)) > 1:
            model.fit(X, y)
            
            # 次回の予測スコアを算出
            latest_window = pos_sequence[-window_size:]
            latest_counts = Counter(latest_window)
            next_features = np.array([[latest_counts.get(num, 0)] for num in range(10)])
            probabilities = model.predict_proba(next_features)[:, 1]
        else:
            probabilities = np.array([0.1] * 10) # 例外処理
            
        ml_scores = {num: prob for num, prob in enumerate(probabilities)}
        pos_ml_scores.append(ml_scores)

    # --- 4. ハイブリッド選定（桁ごとのML確率 × 共起性） ---
    predictions = []
    seen = set()
    seen_box = set() # ボックスでの重複も防ぎ、予想のカバー範囲を最大化する
    digits = list(range(10))

    candidates = []
    for _ in range(4000): # パターンを多めに生成
        cand = []
        for pos in range(length):
            # 各桁ごとに、専用のAIが弾き出した確率(重み)を使って数字を抽出
            weights = [pos_ml_scores[pos][n] for n in digits]
            if sum(weights) > 0:
                choice = random.choices(digits, weights=weights)[0]
            else:
                choice = random.choice(digits)
            cand.append(choice)
        candidates.append(cand)

    valid_candidates = []
    for cand in candidates:
        # MLのベーススコア（各桁のAIが弾き出した確率の合計）
        base_score = sum(pos_ml_scores[pos][cand[pos]] for pos in range(length))
        
        # 共起性(ペア)ボーナスの加算
        pair_bonus = 0
        for pair in itertools.combinations(sorted(cand), 2):
            pair_bonus += pair_counts.get(pair, 0)
            
        final_score = base_score + (pair_bonus * 0.05)
        
        # ナンバーズ特有のフィルター：同じ数字が3つ以上出る確率（トリプル以上）は極めて低いため除外
        counts = Counter(cand)
        if any(v >= 3 for v in counts.values()):
            continue
            
        valid_candidates.append((final_score, cand))

    # 最終スコア順にランキングし、上位5つの予想を選定
    valid_candidates.sort(key=lambda x: x[0], reverse=True)
    
    for score, cand in valid_candidates:
        cand_str = "".join(map(str, cand))
        box_str = "".join(sorted(cand_str))
        
        # ストレートでもボックスでも過去の予想と被らないようにする
        if cand_str not in seen and box_str not in seen_box:
            seen.add(cand_str)
            seen_box.add(box_str)
            predictions.append(cand_str)
        if len(predictions) == 5:
            break

    # 万が一、条件が厳しすぎて5個揃わなかった場合の安全処理
    while len(predictions) < 5:
        cand_str = "".join(str(random.randint(0,9)) for _ in range(length))
        if cand_str not in seen:
            seen.add(cand_str)
            predictions.append(cand_str)

    return predictions

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

# --- 5. HTML構築 ---
def build_html():
    history_data = fetch_both_history()
    latest_data = history_data[0]
    
    # ★N4とN3のトレンドを別々に取得
    n4_hot, n4_cold = analyze_digit_trends(history_data, 'n4_win')
    n3_hot, n3_cold = analyze_digit_trends(history_data, 'n3_win')
    # ★新設した高度な複合分析ロジックを使用 (N4とN3それぞれで生成)
    n4_preds = generate_advanced_predictions(history_data, 4, 'n4_win')
    n3_preds = generate_advanced_predictions(history_data, 3, 'n3_win')
    
    history_record = manage_history(latest_data, n4_preds, n3_preds)

    next_date_str = get_next_numbers_date()
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【{history_record[0]['target_kai']}】ナンバーズ3＆4当選予想・データ分析 | 最新AI予想</title>
    <meta name="description" content="{history_record[0]['target_kai']}のナンバーズ3・ナンバーズ4当選予想。過去1年分の出現傾向（HOT/COLD）から導き出した完全無料のAI予想とストレート/ボックス推奨を公開中！">
    <meta property="og:title" content="【{history_record[0]['target_kai']}】ナンバーズ3＆4最新AI予想">
    <meta property="og:description" content="過去1年分の出現傾向から導き出した完全無料のAI予想と推奨の買い方を公開中！">
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
        nav a {{ color: #1e3a8a; padding: 15px 20px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; }}
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
    </nav>

<div class="section-card" style="text-align: center; background: linear-gradient(to right, #ffffff, #f8fafc); border: 2px solid #64748b; margin-top: 25px; margin-bottom: 30px; padding: 25px 15px; border-radius: 12px;">
        <h3 style="color: #334155; margin-top: 0; font-size: 20px; font-weight: bold;">📊 最新の当せん詳細データ</h3>
        <a href="numbers_detail.html" style="display: inline-block; background-color: #1e293b; color: white; text-decoration: none; padding: 15px 35px; border-radius: 30px; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(30, 41, 59, 0.3); transition: transform 0.2s;">
            🔍 詳細ページを確認する
        </a>
    </div>
    
    <div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <script src="https://adm.shinobi.jp/s/4275e4a786993be6d30206e03ec2de0f"></script>
        </div>

    <div class="container">
    
        <div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4RGVRU+4GLE+5ZU29" rel="nofollow">
<img border="0" width="320" height="auto" alt="" src="https://www29.a8.net/svt/bgt?aid=260331146288&wid=002&eno=01&mid=s00000020813001007000&mc=1"></a>
<img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=4AZSSQ+4RGVRU+4GLE+5ZU29" alt="">
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
            <p>直近の傾向からHOT数字とCOLD数字を掛け合わせたアルゴリズム予想です。</p>
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
    
    html += f"""            </div>
        </div>

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
    html += """                </tbody>
            </table>
            </div>
        </div>

        <div style="text-align: center; margin-bottom: 40px;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4UG1SQ+3P7U+61JSH" rel="nofollow">
            <img border="0" width="300" height="250" alt="" src="https://www22.a8.net/svt/bgt?aid=260331146293&wid=002&eno=01&mid=s00000017265001015000&mc=1"></a>
            <img border="0" width="1" height="1" src="https://www14.a8.net/0.gif?a8mat=4AZSSQ+4UG1SQ+3P7U+61JSH" alt="">
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
    html += """                    </tbody>
                </table>
            </div>
        </div>
    </div>

<div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4RGVRU+4GLE+65U41" rel="nofollow">
<img border="0" width="340" height="auto" alt="" src="https://www22.a8.net/svt/bgt?aid=260331146288&wid=002&eno=01&mid=s00000020813001035000&mc=1"></a>
<img border="0" width="1" height="1" src="https://www11.a8.net/0.gif?a8mat=4AZSSQ+4RGVRU+4GLE+65U41" alt="">
    </div>

    <footer>
        <div class="footer-links">
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p>※当サイトの予想・データは当選を保証するものではありません。宝くじの購入は自己責任でお願いいたします。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 宝くじ当選予想・データ分析ポータル All Rights Reserved.</p>
    </footer>
</body>
</html>"""

    # --- ⭐️ 【改良版】自動ポスト・LINE配信ロジック ⭐️ ---
    import datetime
    
    now = datetime.datetime.now()
    today_weekday = now.weekday() # 0:月, 1:火, 2:水, 3:木, 4:金, 5:土, 6:日
    current_hour = now.hour
    
    next_kai = history_record[0]['target_kai']
    site_url = "https://loto-yosou-ai.com/numbers.html" 
    
    send_flag = False
    msg = ""

    # ■ 平日 (月〜金) の処理
    if today_weekday < 5:
        # 朝の予告はスキップ (何もしない)
        if current_hour < 19:
            pass 
        
        # 夜の結果確認
        else:
            finished_record = history_record[1] if len(history_record) > 1 else history_record[0]
            finished_kai = finished_record['target_kai']
            n3_res = finished_record.get('result_n3', '')  # ⭕️ 正しい名前に修正
            n4_res = finished_record.get('result_n4', '')  # ⭕️ 正しい名前に修正
            
            # 「的中」という言葉が含まれている場合のみフラグを立てる
            if "的中" in n3_res or "的中" in n4_res:
                send_flag = True
                msg = f"【#ナンバーズ 的中速報🎯】\n第 {finished_kai} 回でAI予想が的中しました！\n"
                msg += f"・ナンバーズ3：{n3_res}\n・ナンバーズ4：{n4_res}\n"
                msg += f"\n的中した具体的な数字と、明日({next_kai})の最新予想はこちら👇\n{site_url}"

    # ■ 土曜日 (5) の夜に週末通知を送る
    elif today_weekday == 5:
        if current_hour >= 19:
            send_flag = True
            msg = f"【#ナンバーズ 週末の予想更新🎯】\n来週、 {next_kai} 回からの最新AI予想を公開しました！\n"
            msg += f"\n週末の間に最新の出現傾向データをチェックして、次回の戦略を立てましょう👇\n{site_url}"

    # ■ 日曜日 (6) は何もしない (土曜に送っているため)
    else:
        pass

    # 配信フラグが立っている場合のみ送信
    if send_flag and msg:
        # post_to_x(msg)
        post_to_line(msg)
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        current_weekday = now.weekday() # 6:日曜, 2:水曜

        if current_weekday in [6, 2]:
            print(f"📅 本日は日曜または水曜（{current_weekday}）のため、SNSへ投稿します。")
            post_to_threads(msg)
            
            image_url = upload_image_to_server(output_image_path)
            if image_url:
                post_to_instagram(image_url, msg)
        else:
            print(f"💤 本日はSNS投稿日ではないため、LINE配信のみで終了します。")
        # ----------------------------------------------------
        # ★ ここからInstagramの自動投稿処理＆動画生成を追加！
        # ----------------------------------------------------
        base_image = "base_image.png"     
        image_path = "numbers_result.jpg"
        
        # ▼▼▼ 数字を職人に渡すために取り出す ▼▼▼
        n4_yosou_a = history_record[0]['n4_preds'][0]
        n3_yosou_a = history_record[0]['n3_preds'][0]
        
        caption = f"🎯最新のナンバーズ AI予想です！\n\n{msg}\n\n#ナンバーズ #宝くじ #AI予想 #ロトナンバーズ攻略局"
        
        # ① 今までの職人に「静止画」を作成してもらう
        is_created = create_result_image(n4_yosou_a, n3_yosou_a, base_image, image_path, target_kai=next_kai, target_date=next_date_str)

        # ====================================================
        # 🎬 ここで動画職人を呼び出し、本物の数字を渡す！
        # ====================================================
        try:
                from create_reel import generate_numbers_reel
                generate_numbers_reel(n4_yosou=n4_yosou_a, n3_yosou=n3_yosou_a, target_kai=next_kai, target_date=next_date_str)
                print(f"✅ 本物のデータでリール生成完了！")
                
                # ▼▼▼ いよいよリール自動投稿の最終ロジック！ ▼▼▼
                video_url = upload_video_to_cloudinary("reel_numbers.mp4")
                if video_url:
                    post_reel_to_instagram(video_url, caption)
                # ▲▲▲ ここまで ▲▲▲
                # ▼▼▼ 追加：YouTube Shortsへの投稿 ▼▼▼
                yt_title = "🎯 明日のナンバーズ激アツAI予想！ #shorts"
                yt_tags = ["ナンバーズ", "宝くじ", "AI予想", "ショート"]
                upload_to_youtube_shorts("reel_numbers.mp4", yt_title, caption, yt_tags)
                # ▲▲▲ ここまで ▲▲▲

                # ▼▼▼ 新規追加：TikTokへの投稿 ▼▼▼
                post_to_tiktok("reel_numbers.mp4", caption)
                # ▲▲▲ ここまで ▲▲▲
                
        except Exception as e:
                print(f"❌ 動画の自動生成・投稿エラー: {e}")
        # ====================================================
        # ====================================================

        # ② 画像が無事に作れたら、アップロードしてインスタに投稿する！（今までの処理）
        if is_created:
            public_image_url = upload_image_to_server(image_path)
            if public_image_url:
                post_to_instagram(public_image_url, caption)
            else:
                print("⚠️ 画像のURL化に失敗しました。")
        # ----------------------------------------------------

    return html

if __name__ == "__main__":
    final_html = build_html()
    with open('numbers.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
        real_data = get_numbers_full_detail()
    generate_numbers_detail_page(real_data)
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