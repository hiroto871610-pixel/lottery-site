import random
import numpy as np
import pandas as pd
import itertools
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import requests
from bs4 import BeautifulSoup
import re
import json
import datetime
import os
from collections import Counter
import tweepy  # ←追加：Xポスト用
import urllib3 # ←追加：エラー回避用
# ▼▼▼ 追加：.envファイルを読み込むためのライブラリ ▼▼▼
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
# JSONBin API設定
# =========================================================
JSONBIN_BIN_ID = os.environ.get("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.environ.get("JSONBIN_API_KEY")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}" if JSONBIN_BIN_ID else ""

def generate_hybrid_predictions(X_train, y_train, X_latest, window_size=10, num_predictions=5):
    import numpy as np
    print("🧠 ロト6 ハイブリッドAI予測を開始します...")

    # ① Random Forest (0か1かの確率を取得)
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    rf_preds = rf_model.predict_proba(X_latest)
    
    prob_rf = np.zeros(44)
    # クラス「1(当選)」の確率を抽出
    if rf_preds.shape[1] > 1:
        for i in range(43):
            prob_rf[i+1] = rf_preds[i, 1]
    else:
        for i in range(43):
            prob_rf[i+1] = rf_preds[i, 0]

    # ② XGBoost
    xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
    xgb_model.fit(X_train, y_train)
    xgb_preds = xgb_model.predict_proba(X_latest)
    
    prob_xgb = np.zeros(44)
    if xgb_preds.shape[1] > 1:
        for i in range(43):
            prob_xgb[i+1] = xgb_preds[i, 1]
    else:
        for i in range(43):
            prob_xgb[i+1] = xgb_preds[i, 0]

    # ③ LSTM (二値分類モデルとして構築)
    X_train_3d = X_train.reshape((X_train.shape[0], 1, X_train.shape[1]))
    X_latest_3d = X_latest.reshape((X_latest.shape[0], 1, X_latest.shape[1]))

    lstm_model = Sequential([
        LSTM(64, activation='relu', input_shape=(1, X_train.shape[1])),
        Dense(1, activation='sigmoid') # 0か1の確率を出力
    ])
    lstm_model.compile(optimizer='adam', loss='binary_crossentropy')
    lstm_model.fit(X_train_3d, y_train, epochs=10, verbose=0)
    lstm_preds = lstm_model.predict(X_latest_3d).flatten()
    
    prob_lstm = np.zeros(44)
    for i in range(43):
        prob_lstm[i+1] = lstm_preds[i]

    # 統合と自信度計算
    final_prob = (prob_rf + prob_xgb + prob_lstm) / 3.0
    
    top6_rf = set(np.argsort(prob_rf)[::-1][:6])
    top6_xgb = set(np.argsort(prob_xgb)[::-1][:6])
    top6_lstm = set(np.argsort(prob_lstm)[::-1][:6])
    agreed = top6_rf & top6_xgb & top6_lstm

    if len(agreed) >= 4:
        rank, msg = "Sランク", "🔥 激アツ！3つのAI予測がロト6で完全に一致！"
    elif len(top6_rf & top6_xgb) >= 3 or len(top6_rf & top6_lstm) >= 3:
        rank, msg = "Aランク", "✨ チャンス！複数のAIが同じ当選パターンを検知。"
    else:
        rank, msg = "Bランク", "⚠️ AIの意見が分散中。波乱の可能性があります。"

    # 予想生成
    predictions = []
    weights = final_prob[1:44] + 0.0001
    weights /= weights.sum()
    numbers_pool = np.arange(1, 44)

    for _ in range(num_predictions):
        pred_nums = np.random.choice(numbers_pool, size=6, replace=False, p=weights)
        pred_nums.sort()
        predictions.append([str(n).zfill(2) for n in pred_nums])

    # ▼▼▼ 追加：AIが最も確率が高いと判断した3つの数字を抽出 ▼▼▼
    top3_indices = np.argsort(final_prob)[::-1]
    top_nums = [str(i).zfill(2) for i in top3_indices if 1 <= i <= 43][:3]
    top_nums_str = "、".join(top_nums)
    # ▲▲▲ ここまで ▲▲▲

    return predictions, rank, msg, top_nums_str

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
    """JSONBinへ履歴データをアップロードして上書きする"""
    if not JSONBIN_BIN_ID:
        return
        
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_API_KEY
    }
    try:
        res = requests.put(JSONBIN_URL, json=data, headers=headers)
        if res.status_code == 200:
            print("☁️ JSONBinへの履歴データ保存が成功しました！")
        else:
            print(f"❌ JSONBin保存エラー: {res.status_code}")
    except Exception as e:
        print(f"❌ JSONBin通信エラー: {e}")

# .envファイルを読み込む
load_dotenv()
# ▲▲▲ ここまで追加 ▲▲▲

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HISTORY_FILE = 'history_loto6.json'

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

# =========================================================
# Threads API設定
# =========================================================

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
# 🎥 YouTube Shorts用：自動アップロード機能
# =========================================================
def upload_to_youtube_shorts(video_path, title, description, tags):
    """YouTubeへ動画を自動アップロードする"""
    print("🎥 YouTube Shortsへ動画をアップロード中...")
    
    # GitHubのSecrets（または.env）からtoken.jsonの中身を取り出す
    token_str = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not token_str:
        print("❌ YOUTUBE_TOKEN_JSONが設定されていません。")
        return
        
    try:
        # 文字列から資格情報（パスポート）を復元
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        
        # YouTube APIに接続
        youtube = build('youtube', 'v3', credentials=creds)
        
        # 動画の設定（タイトル、説明、タグなど）
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '24' # 24 = エンターテイメント
            },
            'status': {
                'privacyStatus': 'public', # ★ public(公開), unlisted(限定公開), private(非公開)
                'selfDeclaredMadeForKids': False
            }
        }
        
        # 動画ファイルの読み込み（YouTube Shortsは60秒以下の縦型なら自動的にShortsになります）
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
        
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
        # ※APIの制限により、チャンネル所有者本人のコメントのみ固定可能です
        comment_id = comment_res['snippet']['topLevelComment']['id']
        youtube.comments().setModerationStatus(
            id=comment_id,
            moderationStatus="published",
            ban=False
        ).execute()
        
        print("✅ 固定コメントの設置が完了しました！")
    except Exception as e:
        print(f"⚠️ コメント固定エラー（手動で固定してください）: {e}")

# アップロード成功時のレスポンスからIDを取得
        response = request.execute()
        video_id = response.get('id')
        print(f"🎉 YouTube投稿成功: {video_id}")
        
        # ▼▼▼ ここで固定コメントを追加！ ▼▼▼
        fixed_msg = (
            "🎯 本日のAI全予想はこちら（完全無料）！\n"
            "👉 https://loto-yosou-ai.com/\n\n"
            "次回の予想も見逃さないよう、チャンネル登録お願いします！✨"
        )
        add_pinned_comment(video_id, fixed_msg)
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

def upload_image_to_imgbb(image_path):
    """ローカル画像をImgBBにアップロードし、公開URLを返す"""
    api_key = os.environ.get("IMGBB_API_KEY")
    url = "https://api.imgbb.com/1/upload"
    
    print("☁️ 画像をImgBBにアップロードしてURL化中...")
    
    try:
        with open(image_path, "rb") as file:
            payload = {
                "key": api_key,
                "image": base64.b64encode(file.read()),
            }
            
        response = requests.post(url, data=payload)
        result = response.json()
        
        if result.get("success"):
            image_url = result["data"]["url"]
            print(f"✅ 画像のURL化成功: {image_url}")
            return image_url
        else:
            print(f"❌ ImgBBエラー: {result}")
            return None
            
    except FileNotFoundError:
        print(f"❌ 画像ファイルが見つかりません: {image_path}")
        return None
    # =========================================================

def create_result_image(loto6_nums, carryover_info, base_image_path, output_image_path, target_kai="", target_date="", confidence_rank="Aランク"):
    """ロト6専用：1080x1350の大画面に合わせて、特大2段組＆白タイトルで描画する職人"""
    print("🎨 ロト6専用の予想画像を生成中（特大2段・白タイトル版）...")
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
        font_url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/static/NotoSansJP-Bold.ttf"
        urllib.request.urlretrieve(font_url, font_path)

    # --- デザイン設定 (特大2段レイアウト用に最適化) ---
    shadow_color = (100, 100, 100)  # 影（グレー）
    white = (255, 255, 255)         # 文字（白）
    
    # ★ご要望に合わせてタイトルの色を白に統一！
    title_color = white          
    ball_color = (37, 99, 235)   # ボールは鮮やかなブルー（ロト6風）
    carry_color = (220, 38, 38)  # キャリーオーバーは目立つ赤！

    # ボールの設定 (3個×2段なので、限界まで巨大化！)
    ball_dia = 240  # ボールの直径（元の1.7倍！）
    ball_space_x = 40 # 横のボール間のスペース
    ball_space_y = 60 # 縦（1段目と2段目）のスペース
    shadow_offset = 8 # 影のズレ量も少し大きく

    # フォントサイズの設定
    font_title = ImageFont.truetype(font_path, 90)
    font_num = ImageFont.truetype(font_path, 140) # 数字も超特大！
    font_carry = ImageFont.truetype(font_path, 65)

    # 全体の上下バランスを見て、描画開始Y位置を決める
    current_y = 300 

    # ------------------------------------------------
    # 描画1：タイトル
    # ------------------------------------------------
    title = f"【ロト6 最新AI予想A {confidence_rank}】"
    subtitle = f"{target_kai} ({target_date})" # ★追加：回号と日付
    
    # タイトルの中央位置を計算
    left, top, right, bottom = draw.textbbox((0, 0), title, font=font_title)
    text_w = right - left
    title_x = (W - text_w) / 2
    
    # タイトルの影と本体を描画（白文字）
    draw.text((title_x + shadow_offset, current_y + shadow_offset), title, font=font_title, fill=shadow_color)
    draw.text((title_x, current_y), title, font=font_title, fill=title_color)

    # ★追加：サブタイトル（回号と日付）の描画
    font_sub = ImageFont.truetype(font_path, 50) # 日付用の少し小さなフォント
    left_s, top_s, right_s, bottom_s = draw.textbbox((0, 0), subtitle, font=font_sub)
    sub_w = right_s - left_s
    sub_x = (W - sub_w) / 2
    draw.text((sub_x + shadow_offset, current_y + 110 + shadow_offset), subtitle, font=font_sub, fill=shadow_color)
    draw.text((sub_x, current_y + 110), subtitle, font=font_sub, fill=white)
    
    current_y += (bottom - top) + 80 # ボール列（1段目）との間隔

    # ------------------------------------------------
    # 描画2：予想番号のボール（3個 × 2段）
    # ------------------------------------------------
    # ★1段（3個）の全体幅を計算して中央寄せ
    total_ball_w = (ball_dia * 3) + (ball_space_x * 2)
    start_x = (W - total_ball_w) / 2 

    # 6つの数字を「前半3個」と「後半3個」に分けてループ処理
    for row in range(2): # 0段目、1段目
        ball_x = start_x
        
        for col in range(3): # 1段につき3個
            idx = row * 3 + col
            if idx >= len(loto6_nums):
                break # 万が一数字が足りない場合のエラー防止
            
            digit = loto6_nums[idx]

            # ボールの影を描画
            draw.ellipse([ball_x + shadow_offset, current_y + shadow_offset, ball_x + ball_dia + shadow_offset, current_y + ball_dia + shadow_offset], fill=shadow_color)
            # ボール本体を描画
            draw.ellipse([ball_x, current_y, ball_x + ball_dia, current_y + ball_dia], fill=ball_color)
            
            # ★数字がボールのド真ん中に来るように計算
            left, top, right, bottom = draw.textbbox((0, 0), digit, font=font_num)
            num_w = right - left
            num_h = bottom - top
            num_x = ball_x + (ball_dia - num_w) / 2
            num_y = current_y + (ball_dia - num_h) / 2 - 18 # 縦位置の微調整

            # 数字をボールの中心に描画
            draw.text((num_x, num_y), digit, font=font_num, fill=white)
            
            # 次のボール（右）へ移動
            ball_x += ball_dia + ball_space_x

        # 1段目（3個）が終わったら、次の段（下）へ移動
        current_y += ball_dia + ball_space_y

    # ------------------------------------------------
    # 描画3：キャリーオーバー（発生時のみ出現）
    # ------------------------------------------------
    if carryover_info:
        current_y += 60 # 2段目のボールの下からの間隔
        
        # ★修正：絵文字を消し、「！(」の部分で強制的に改行（2段に）する
        carryover_info = carryover_info.replace("💰 ", "").replace("！(", "！\n(")
        
        # ▼ 改行対応のため textbbox → multiline_textbbox に変更
        left, top, right, bottom = draw.multiline_textbbox((0, 0), carryover_info, font=font_carry, align="center")
        carry_w = right - left
        carry_x = (W - carry_w) / 2
        
        # ▼ 改行対応のため text → multiline_text に変更し、align="center" を追加
        draw.multiline_text((carry_x + shadow_offset, current_y + shadow_offset), carryover_info, font=font_carry, fill=shadow_color, align="center")
        draw.multiline_text((carry_x, current_y), carryover_info, font=font_carry, fill=carry_color, align="center")

    # --- 共通処理 ---
    # 完成した画像を保存（Instagram対応のためJPEGに変換して保存！）
    img = img.convert("RGB") 
    img.save(output_image_path, "JPEG", quality=95)
    print(f"✅ 画像の生成が完了しました！: {output_image_path}")
    return True
# =========================================================
import re
import requests
from bs4 import BeautifulSoup

def get_loto6_full_detail():
    """楽天宝くじから直近の回号・日付・番号・金額・口数・キャリーオーバーをすべて取得する最強版"""
    print("☁️ 楽天宝くじから最新の詳細データを抽出中...")
    url = "https://takarakuji.rakuten.co.jp/backnumber/loto6/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    result_data = {
        "round": "", "date": "", "numbers": [], "bonus": "",
        "prizes": [], "carryover": "0円", "has_carryover": False
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            res.encoding = 'euc-jp'
            soup = BeautifulSoup(res.content, 'html.parser')

            # 1. ページ全体から「本数字」と「1等」の両方を含む【最新結果のテーブル】を特定する
            target_table = None
            for table in soup.find_all('table'):
                text = table.get_text()
                if '本数字' in text and '1等' in text and 'ボーナス' in text:
                    target_table = table
                    break
            
            if not target_table:
                print("❌ 最新結果のテーブルが見つかりません。")
                return None

            # 2. 特定したテーブルの各行(tr)を解析
            for tr in target_table.find_all('tr'):
                header_cell = tr.find(['th', 'td'])
                if not header_cell:
                    continue
                
                header_text = header_cell.get_text(strip=True)
                
                # --- ★修正：本数字（マスが分かれていても行全体から数字をすべて回収！） ---
                if '本数字' in header_text:
                    row_text = tr.get_text(separator=' ')
                    # 1桁または2桁の数字だけをすべて抜き出す
                    nums = re.findall(r'(?<!\d)\d{1,2}(?!\d)', row_text)
                    result_data["numbers"] = [str(n).zfill(2) for n in nums[:6]]
                
                # --- ★修正：ボーナス数字 ---
                elif 'ボーナス' in header_text:
                    row_text = tr.get_text(separator=' ')
                    nums = re.findall(r'(?<!\d)\d{1,2}(?!\d)', row_text)
                    if nums:
                        result_data["bonus"] = str(nums[0]).zfill(2)
                
                # --- 1等〜5等の当せん金と口数 ---
                for i in range(1, 6):
                    if f'{i}等' in header_text:
                        tds = tr.find_all('td')
                        if len(tds) >= 2:
                            result_data["prizes"].append({
                                "grade": f"{i}等",
                                "winners": tds[-2].get_text(strip=True),
                                "prize": tds[-1].get_text(strip=True)
                            })
                            
                # --- キャリーオーバー ---
                if 'キャリーオーバー' in header_text:
                    tds = tr.find_all('td')
                    if len(tds) >= 1:
                        carry_val = tds[-1].get_text(strip=True)
                        result_data["carryover"] = carry_val
                        if "0円" not in carry_val and carry_val != "":
                            result_data["has_carryover"] = True

            # 3. 回号と日付の取得
            table_text = target_table.get_text(separator=' ', strip=True)
            m_round = re.search(r'第\s*\d+\s*回', table_text)
            m_date = re.search(r'\d{4}[年/]\d{1,2}[月/]\d{1,2}日?', table_text)
            
            if m_round: result_data["round"] = m_round.group().replace(' ', '')
            if m_date: result_data["date"] = m_date.group()

            # もしテーブル内に回号が無ければ、周辺の見出しから探す
            if not result_data["round"]:
                for heading in soup.find_all(['h1', 'h2', 'h3', 'div', 'p']):
                    h_text = heading.get_text(strip=True)
                    if '第' in h_text and '回' in h_text and 'ロト6' in h_text:
                        m_r = re.search(r'第\s*\d+\s*回', h_text)
                        m_d = re.search(r'\d{4}[年/]\d{1,2}[月/]\d{1,2}日?', h_text)
                        if m_r: result_data["round"] = m_r.group().replace(' ', '')
                        if m_d: result_data["date"] = m_d.group()
                        if result_data["round"]: break

            print(f"✅ 最新詳細データの取得に成功しました！ ({result_data['round']})")
            return result_data
            
    except Exception as e:
        print(f"❌ 楽天データ解析エラー: {e}")
        return None

def generate_loto6_detail_page(result_data):
    """既存のベースHTML/CSSにロト6の詳細データを流し込む"""
    print("🔄 ロト6 詳細ページ(HTML)をベースデザインで生成中...")
    
    if not result_data:
        print("⚠️ リアルデータの取得に失敗したため、テスト用の仮データを使用します！") 
        result_data = {
            "round": "第----回", "date": "----/--/--",
            "numbers": ["-","-","-","-","-","-"], "bonus": "-",
            "prizes": [], "carryover": "0円", "has_carryover": False
        }

    # 本数字のボールを生成（青のグラデーション）
    main_balls = "".join([f'<span class="ball">{n}</span>' for n in result_data.get("numbers", [])])
    
    # ボーナス数字のボールを生成（目立つように赤のグラデーションに上書き）
    bonus_ball = f'<span class="ball" style="background: linear-gradient(135deg, #ef4444, #b91c1c);">{result_data.get("bonus", "")}</span>' if result_data.get("bonus") else ""

    # テーブルの行を生成
    trs = ""
    for p in result_data.get("prizes", []):
        trs += f"<tr><td style='font-weight:bold; color:#1e3a8a;'>{p['grade']}</td><td style='color:#0284c7; font-weight:bold; font-size:16px;'>{p['prize']}</td><td style='color:#64748b;'>{p['winners']}</td></tr>"

    # キャリーオーバーの表示ブロックを生成
    carryover_html = ""
    if result_data.get("has_carryover"):
        carryover_html = f"""
        <div class="carryover-badge">
            💰 キャリーオーバー発生中！<br>
            <span style="font-size: 26px; display: inline-block; margin-top: 5px; letter-spacing: 1px;">{result_data.get('carryover', '0円')}</span>
        </div>
        """

    # HTMLの組み立て（※CSSの波括弧は {{ }} と2つ重ねています）
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【{result_data.get('round', '')}】ロト6 抽選結果詳細データ</title>
    <meta name="description" content="{result_data.get('round', '')}のロト6当せん金額・口数、キャリーオーバーの最新詳細データを公開しています。">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; padding: 10px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #1e3a8a; padding: 15px 20px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; }}
        nav a.active {{ border-bottom: 3px solid #0284c7; color: #0284c7; }}
        nav a:hover {{ background-color: #f0f4f8; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #0284c7; border-bottom: 2px solid #e0f2fe; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; }}
        .prediction-box {{ background-color: #f0f9ff; border: 2px solid #bae6fd; border-radius: 12px; padding: 25px; margin-bottom: 20px;}}
        .numbers-row {{ background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; align-items: center; flex-wrap: wrap; }}
        .row-label {{ font-size: 18px; font-weight: bold; color: #1e3a8a; background-color: #e0e7ff; padding: 5px 15px; border-radius: 4px; margin-right: 20px; min-width: 60px; text-align: center; }}
        .ball-container {{ display: flex; gap: 8px; flex-wrap: wrap; margin-right: auto;}}
        .ball {{ display: inline-flex; justify-content: center; align-items: center; width: 42px; height: 42px; background: linear-gradient(135deg, #0ea5e9, #0284c7); color: white; border-radius: 50%; font-size: 18px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.3); }}
        
        .carryover-badge {{ background: linear-gradient(135deg, #ef4444, #b91c1c); color: white; font-size: 14px; font-weight: bold; padding: 15px 20px; border-radius: 12px; margin: 0 0 25px 0; display: inline-block; animation: pulse 2s infinite; box-shadow: 0 4px 10px rgba(239,68,68,0.4); text-align: center; width: 100%; box-sizing: border-box; }}
        @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.02); }} 100% {{ transform: scale(1); }} }}

        @media (max-width: 600px) {{ 
            .numbers-row {{ flex-direction: column; align-items: flex-start; padding: 15px; gap: 10px;}} 
            .row-label {{ margin-right: 0; margin-bottom: 5px; }} 
            .ball-container {{ margin-right: 0; gap: 6px; }}
            .ball {{ width: 36px; height: 36px; font-size: 16px;}}
            .carryover-badge {{ font-size: 13px; padding: 12px; margin: 0 0 20px 0; }} 
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
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">ロト6詳細データ</div>
        </a>
    </header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html" class="active">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
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
            <h2 class="section-header">🎯 ロト6 抽選結果</h2>
            
            {carryover_html}

            <div class="prediction-box">
                <div class="numbers-row">
                    <div class="row-label">本数字</div>
                    <div class="ball-container">
                        {main_balls}
                    </div>
                </div>
                <div class="numbers-row" style="margin-bottom: 0; background-color: #fff1f2; border-color: #fecdd3;">
                    <div class="row-label" style="background-color: #ffe4e6; color: #be123c;">ボーナス</div>
                    <div class="ball-container">
                        {bonus_ball}
                    </div>
                </div>
            </div>
            <table>
                <thead><tr><th>等級</th><th>当せん金額</th><th>口数</th></tr></thead>
                <tbody>
                    {trs}
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

        <div style="text-align: center; margin: 30px 0;">
    <a href="loto6.html" style="display: inline-block; background-color: #3b82f6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        ◀ ロト6 AI予想トップに戻る
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
            <a href="about.html">運営者情報</a> |
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p>※当サイトのデータは当選を保証するものではありません。宝くじの購入は自己責任でお願いいたします。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 宝くじ当選予想・データ分析ポータル All Rights Reserved.</p>
    </footer>
</body>
</html>"""

    with open("loto6_detail.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ ロト6 詳細ページ(ベースデザイン版) の生成が完了しました！")

# --- 1. 過去データの取得（過去1年分） ---
def fetch_history_data():
    base_url = "https://takarakuji.rakuten.co.jp/backnumber/loto6/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    history_data = []
    
    # 過去12ヶ月分のURLを自動生成（最新ページ ＋ 過去12ヶ月分）
    today = datetime.date.today()
    target_urls = [f"{base_url}lastresults/"]
    
    for i in range(36):
        y = today.year
        m = today.month - i
        if m <= 0:
            m += 12
            y -= 1
        target_urls.append(f"{base_url}{y}{m:02d}/")
    
    for url in target_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200: continue
            res.encoding = 'euc-jp'
            soup = BeautifulSoup(res.content, 'html.parser')
            
            # HTMLタグを完全に消し去り、ただの文章にする
            text = soup.get_text(separator=' ')
            
            # 文章の中から「第〇〇回」をすべて見つける
            for m in re.finditer(r'第\s*(\d+)\s*回', text):
                kai_num = m.group(1).zfill(4)
                kai_str = f"第{kai_num}回"
                
                # 回号のすぐ後ろのテキスト（300文字分）を切り出して解析
                chunk = text[m.end():m.end() + 300]
                
                # ★【修正部分】別の回号のデータが混ざらないよう、次の「第〇〇回」が現れたらそこでカットする
                next_kai_match = re.search(r'第\s*\d+\s*回', chunk)
                if next_kai_match:
                    chunk = chunk[:next_kai_match.start()]
                
                # 切り出した中から「日付」を見つける
                date_m = re.search(r'(\d{4})[/年]\s*(\d{1,2})\s*[/月]\s*(\d{1,2})', chunk)
                if not date_m: continue
                
                date_str = f"{date_m.group(1)}/{date_m.group(2).zfill(2)}/{date_m.group(3).zfill(2)}"
                
                # ★超重要：日付の直後から残りのテキストを切り出す（日付の数字誤飲防止）
                num_chunk = chunk[date_m.end():]
                
                # 残った文章から「すべての数字」を抽出
                all_digits = re.findall(r'\d+', num_chunk)
                
                # ★ロト6の範囲（1〜43）の数字だけを残す
                valid_nums = [n.zfill(2) for n in all_digits if 1 <= int(n) <= 43]
                
                # ★上から順番に、本数字6個とボーナス数字1個（合計7個）が揃っていれば大成功
                if len(valid_nums) >= 7:
                    main_nums = valid_nums[:6]
                    bonus_nums = valid_nums[6:7]
                    
                    # まだ追加されていない回号なら保存
                    if not any(d['kai'] == kai_str for d in history_data):
                        history_data.append({
                            "kai": kai_str,
                            "date": date_str,
                            "main": main_nums,
                            "bonus": bonus_nums
                        })
        except Exception:
            pass # エラーが起きても止まらずに次の月の取得へ進む
            
    if not history_data:
        raise ValueError("過去データが取得できませんでした。サイトの構造が変わった可能性があります。")
        
    # 最新の回号が一番上に来るように並び替え
    history_data.sort(key=lambda x: int(re.search(r'\d+', x['kai']).group()), reverse=True)
    return history_data

# --- 2. ホット＆コールド算出 (HTML表示用維持) ---
def analyze_trends(history_data):
    all_nums = []
    for data in history_data:
        all_nums.extend(data['main'])
    
    counts = Counter(all_nums)
    for i in range(1, 44):
        num_str = str(i).zfill(2)
        if num_str not in counts: counts[num_str] = 0
            
    sorted_counts = counts.most_common()
    hot = sorted_counts[:5]
    cold = list(reversed(sorted_counts))[:5]
    
    return hot, cold

# --- 3. 複合アルゴリズム予想生成（★機械学習ハイブリッド版に刷新） ---
def generate_advanced_predictions(history_data):
    print("🧠 AI（Random Forest）が過去の傾向と数字の共起性を学習中...")
    if not history_data or len(history_data) < 20:
        return [] 

    main_draws = [list(map(int, d['main'])) for d in reversed(history_data)]
    
    # --- 1. 共起性行列（ペア相性）の作成 ---
    pair_counts = Counter()
    for draw in main_draws:
        for pair in itertools.combinations(sorted(draw), 2):
            pair_counts[pair] += 1

    # --- 2. 機械学習のためのデータセット作成 ---
    features = []
    labels = []
    window_size = 10 
    
    for i in range(window_size, len(main_draws) - 1):
        past_window = [num for draw in main_draws[i-window_size:i] for num in draw]
        past_counts = Counter(past_window)
        
        target_draw = main_draws[i] 
        for num in range(1, 44): # ★ロト6は1〜43
            feature = [past_counts.get(num, 0)]
            features.append(feature)
            labels.append(1 if num in target_draw else 0)

    X = np.array(features)
    y = np.array(labels)

    # =========================================================
    # ▼▼▼ 古いコード（次回の予測スコアを算出 など）を消してこれに書き換える ▼▼▼
    # =========================================================
    # 1. 次回の予測用データ(43個の数字の出現回数)を作る
    latest_window = [num for draw in main_draws[-window_size:] for num in draw]
    latest_counts = Counter(latest_window)
    next_features = np.array([[latest_counts.get(num, 0)] for num in range(1, 44)])

    # 2. 新しいAIを呼び出す（next_features を渡す）
    global global_confidence_rank, global_confidence_msg
    predictions, global_confidence_rank, global_confidence_msg, top_nums_str = generate_hybrid_predictions(X, y, next_features)

    return predictions, global_confidence_rank, global_confidence_msg, top_nums_str
    # =========================================================
    # ▲▲▲ ここまで ▲▲▲

    # --- 4. 次回の予測スコアを算出 ---
    latest_window = [num for draw in main_draws[-window_size:] for num in draw]
    latest_counts = Counter(latest_window)
    
    next_features = np.array([[latest_counts.get(num, 0)] for num in range(1, 44)]) # ★ロト6は1〜43
    probabilities = model.predict_proba(next_features)[:, 1] 
    
    ml_scores = {num: prob for num, prob in enumerate(probabilities, start=1)}

    # --- 5. ハイブリッド選定（MLスコア × 共起性） ---
    predictions = []
    seen = set()
    
    numbers = list(range(1, 44)) # ★ロト6は1〜43
    weights = [ml_scores[n] for n in numbers]

    candidates = []
    for _ in range(3000): # 3000パターン生成
        cand = []
        pool_nums = list(numbers)
        pool_weights = list(weights)
        for _ in range(6): # ★ロト6は6個選ぶ
            if sum(pool_weights) > 0:
                choice = random.choices(pool_nums, weights=pool_weights)[0]
            else:
                choice = random.choice(pool_nums)
            cand.append(choice)
            idx = pool_nums.index(choice)
            pool_nums.pop(idx)
            pool_weights.pop(idx)
        cand.sort()
        candidates.append(cand)

    valid_candidates = []
    for cand in candidates:
        base_score = sum(ml_scores[n] for n in cand)
        
        pair_bonus = 0
        for pair in itertools.combinations(cand, 2):
            pair_bonus += pair_counts.get(pair, 0)
            
        final_score = base_score + (pair_bonus * 0.05)
        valid_candidates.append((final_score, cand))

    valid_candidates.sort(key=lambda x: x[0], reverse=True)
    for score, cand in valid_candidates:
        t_cand = tuple(cand)
        if t_cand not in seen:
            seen.add(t_cand)
            predictions.append([str(n).zfill(2) for n in cand])
        if len(predictions) == 5:
            break

    return predictions

def manage_history(latest_data, new_predictions):
    # ▼▼▼ 変更点①：ローカルファイルの読み込み処理を削除し、JSONBinから取得 ▼▼▼
    print("☁️ JSONBinから過去の履歴データを取得しています...")
    history_record = load_history_from_jsonbin()
    # ▲▲▲ ここまで ▲▲▲
            
    latest_kai = latest_data['kai']
    latest_kai_num = int(re.search(r'\d+', latest_kai).group()) # 最新回の数字部分だけを抽出
    win_main = set(latest_data['main'])
    win_bonus = set(latest_data['bonus'])
    
    for record in history_record:
        record_kai_match = re.search(r'\d+', record.get('target_kai', ''))
        if record.get('status') == 'waiting' and record_kai_match:
            record_kai_num = int(record_kai_match.group())
            
            # ★修正：「第1900回」と「第01900回」の違いを無視し、数字ベースで判定して更新
            if record_kai_num == latest_kai_num:
                best_match = -1  # ★0個一致でも必ず更新されるように、初期値をマイナス1にする
                best_result = "ハズレ"
                for p in record['predictions']:
                    p_set = set(p)
                    match_main = len(p_set & win_main)
                    has_bonus = len(p_set & win_bonus) > 0
                    
                    if match_main == 6: result = "1等🎯"
                    elif match_main == 5 and has_bonus: result = "2等🎯"
                    elif match_main == 5: result = "3等"
                    elif match_main == 4: result = "4等"
                    elif match_main == 3: result = "5等"
                    else: result = f"ハズレ({match_main}個一致)"
                    
                    # ★一致した数が過去最高（または同点でボーナスあり）なら成績を更新
                    if match_main > best_match or (match_main == best_match and has_bonus and "B" not in best_result):
                        best_match = match_main
                        best_result = result
                        
                record['status'] = 'finished'
                record['actual_main'] = ", ".join(latest_data['main'])
                record['actual_bonus'] = "(B: " + ", ".join(latest_data['bonus']) + ")"
                record['best_result'] = best_result
                record['target_kai'] = latest_kai # フォーマットを最新のゼロ埋めに上書き
                
    # 次回号をゼロ埋めフォーマット（4桁）で生成
    next_kai_num = latest_kai_num + 1
    next_kai = f"第{next_kai_num:04d}回"
    
    # すでに次回号が追加されていないか、数字ベースで重複チェック
    if not any(int(re.search(r'\d+', r.get('target_kai', '0')).group()) == next_kai_num for r in history_record if re.search(r'\d+', r.get('target_kai', '0'))):
        history_record.insert(0, {
            "target_kai": next_kai,
            "status": "waiting",
            "predictions": new_predictions,
            "actual_main": "----",
            "actual_bonus": "",
            "best_result": "抽選待ち..."
        })
    
    cleaned_record = []
    seen_kais = set()
    for record in history_record:
        kai_num_match = re.search(r'\d+', record.get('target_kai', ''))
        if kai_num_match:
            k_num = int(kai_num_match.group())
            if k_num not in seen_kais:
                cleaned_record.append(record)
                seen_kais.add(k_num)
            
    history_record = cleaned_record[:100]
    
    # ▼▼▼ 変更点②：ローカルファイルへの書き込み処理を削除し、JSONBinへ保存 ▼▼▼
    print("☁️ JSONBinに最新の履歴データを保存しています...")
    save_history_to_jsonbin(history_record)
    # ▲▲▲ ここまで ▲▲▲
        
    return history_record

# --- 追加：キャリーオーバー判定（確実・正確なWeb抽出に変更） ---
def check_loto6_carryover():
    """
    楽天宝くじのロト6トップページに直接アクセスし、
    HTML構造（BeautifulSoup）から確実にキャリーオーバーの発生有無を判定します。
    """
    url = "https://takarakuji.rakuten.co.jp/backnumber/loto6/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            res.encoding = 'euc-jp'
            soup = BeautifulSoup(res.content, 'html.parser')
            
            # HTML構造から「キャリーオーバー」を含む要素を探し、その行(tr)の中に「0円」がないかを判定
            carry_element = soup.find(string=re.compile(r'キャリーオーバー'))
            if carry_element:
                parent_row = carry_element.find_parent('tr')
                if parent_row:
                    row_text = parent_row.get_text(strip=True)
                    if "0円" not in row_text:
                        return "💰 キャリーオーバー発生中！(最高6億円)"
    except Exception as e:
        print(f"キャリーオーバー判定エラー: {e}")
    return ""

def get_next_loto6_date():
    """現在時刻から次回のロト6抽選日(月曜または木曜)を自動計算する"""
    now = datetime.datetime.now()
    # 18:30以降に実行された場合は、当日の購入は終了したとみなして翌日基準で計算
    if now.hour >= 19 or (now.hour == 18 and now.minute >= 30):
        base_date = now.date() + datetime.timedelta(days=1)
    else:
        base_date = now.date()

    # ロト6 (月曜: 0, 木曜: 3)
    l6_days = 0
    while (base_date + datetime.timedelta(days=l6_days)).weekday() not in [0, 3]:
        l6_days += 1
    next_date = base_date + datetime.timedelta(days=l6_days)

    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return f"{next_date.month}月{next_date.day}日({weekdays[next_date.weekday()]})"

# --- 5. HTML構築 ---
def build_html():
    print("🔄 ロト6 データ取得＆解析を開始...")
    history_data = fetch_history_data()
    latest_data = history_data[0]
    hot, cold = analyze_trends(history_data)
    
    # ★新設した高度な複合分析ロジックを使用
    predictions, confidence_rank, confidence_msg, top_nums_str = generate_advanced_predictions(history_data)
    
    history_record = manage_history(latest_data, predictions)
    
    print(f"📡 LOTO6 データ取得成功: {latest_data['kai']} ({latest_data['date']})")

    # キャリーオーバー情報の取得とHTMLパーツ作成
    carryover_text = check_loto6_carryover()
    carryover_html = f'<div class="carryover-badge">{carryover_text}</div>' if carryover_text else ''

    next_date_str = get_next_loto6_date()
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【{history_record[0]['target_kai']}】ロト6当選予想・データ分析ポータル | 最新AI予想</title>
    <meta name="description" content="{history_record[0]['target_kai']}のロト6当選予想。過去1年分のデータから導き出したHOT数字・COLD数字と完全無料のAIアルゴリズム予想を公開中！最高6億円のキャリーオーバー情報も。">
    <meta property="og:title" content="【{history_record[0]['target_kai']}】ロト6最新AI予想">
    <meta property="og:description" content="過去1年分のデータから導き出したHOT数字・COLD数字と完全無料のAIアルゴリズム予想を公開中！">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://loto-yosou-ai.com/loto6.html">
    <meta property="og:image" content="https://loto-yosou-ai.com/Lotologo001.png">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="canonical" href="https://loto-yosou-ai.com/loto6.html">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; color: white; padding: 20px; text-align: center; }}
        header h1 {{ margin: 0; font-size: 24px; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #1e3a8a; padding: 15px 20px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; }}
        nav a.active {{ border-bottom: 3px solid #0284c7; color: #0284c7; }}
        nav a:hover {{ background-color: #f0f4f8; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #0284c7; border-bottom: 2px solid #e0f2fe; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; }}
        .prediction-box {{ background-color: #f0f9ff; border: 2px solid #bae6fd; border-radius: 12px; padding: 25px; margin-bottom: 20px;}}
        .numbers-row {{ background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; align-items: center; }}
        .row-label {{ font-size: 18px; font-weight: bold; color: #1e3a8a; background-color: #e0e7ff; padding: 5px 15px; border-radius: 4px; margin-right: 20px; min-width: 60px; text-align: center; }}
        .ball-container {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .ball {{ display: inline-flex; justify-content: center; align-items: center; width: 42px; height: 42px; background: linear-gradient(135deg, #0ea5e9, #0284c7); color: white; border-radius: 50%; font-size: 18px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.3); }}

        /* キャリーオーバーバッジのスタイル（レスポンシブ対応） */
        .carryover-badge {{ background: linear-gradient(135deg, #ef4444, #b91c1c); color: white; font-size: 14px; font-weight: bold; padding: 10px 15px; border-radius: 8px; margin: 15px 0; display: inline-block; animation: pulse 2s infinite; box-shadow: 0 4px 10px rgba(239,68,68,0.4); text-align: center; width: 100%; box-sizing: border-box; }}
        @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.02); }} 100% {{ transform: scale(1); }} }}

        @media (max-width: 600px) {{ 
            .numbers-row {{ flex-direction: column; align-items: flex-start; padding: 15px;}} 
            .row-label {{ margin-bottom: 10px; }} 
            .ball {{ width: 36px; height: 36px; font-size: 16px;}}
            .carryover-badge {{ font-size: 13px; padding: 8px; margin: 10px 0; }} 
        }}
        
        .hc-container {{ display: flex; gap: 20px; flex-wrap: wrap; }}
        .hc-box {{ flex: 1; min-width: 250px; padding: 15px; border-radius: 8px; }}
        .hot-box {{ background-color: #fee2e2; border: 1px solid #fca5a5; }}
        .cold-box {{ background-color: #e0f2fe; border: 1px solid #7dd3fc; }}
        .hc-title {{ font-weight: bold; margin-bottom: 10px; }}
        .hc-number {{ display: inline-block; padding: 5px 10px; margin: 3px; border-radius: 4px; font-weight: bold; background: white; }}
        .hot-box .hc-number {{ color: #ef4444; border: 1px solid #ef4444; }}
        .cold-box .hc-number {{ color: #0ea5e9; border: 1px solid #0ea5e9; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: center; }}
        th, td {{ padding: 12px; border-bottom: 1px solid #e2e8f0; }}
        th {{ background-color: #f8fafc; color: #475569; font-weight: bold; }}
        .result-win {{ color: #16a34a; font-weight: bold; background-color: #dcfce7; padding: 4px 8px; border-radius: 4px; }}
        .result-lose {{ color: #94a3b8; }}
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
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">ロト6当選予想・速報</div>
        </a>
    </header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html" class="active">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="column.html">攻略ガイド🔰</a>
    </nav>

<div class="section-card" style="text-align: center; background: linear-gradient(to right, #ffffff, #eff6ff); border: 2px solid #3b82f6; margin-top: 25px; margin-bottom: 30px; padding: 25px 15px; border-radius: 12px;">
        <h3 style="color: #1d4ed8; margin-top: 0; font-size: 20px; font-weight: bold;">📊 最新の当せん詳細データ</h3>
        <a href="loto6_detail.html" style="display: inline-block; background-color: #2563eb; color: white; text-decoration: none; padding: 15px 35px; border-radius: 30px; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3); transition: transform 0.2s;">
            🔍 詳細ページを確認する
        </a>
    </div>

<div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <script src="https://adm.shinobi.jp/s/4275e4a786993be6d30206e03ec2de0f"></script>
        </div>

    <div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4RGVRU+4GLE+5ZU29" rel="nofollow">
<img border="0" width="320" height="auto" alt="" src="https://www29.a8.net/svt/bgt?aid=260331146288&wid=002&eno=01&mid=s00000020813001007000&mc=1"></a>
<img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=4AZSSQ+4RGVRU+4GLE+5ZU29" alt="">
    </div>
        
        <div class="section-card" style="background: linear-gradient(to right, #ffffff, #f0f9ff); border-left: 5px solid #0284c7; padding: 20px;">
            <div style="font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 10px;">⏰ 次回抽選日と購入期限</div>
            <div style="font-size: 15px; color: #475569;">
                <span style="display:inline-block; margin-right: 20px;">次回抽選: <strong style="color: #0284c7; font-size: 18px;">{next_date_str}</strong></span>
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
            <h2 class="section-header">🎯 次回 ({history_record[0]['target_kai']}) ロト6の予想</h2>
            <p>直近約1年間の傾向からHOT数字とCOLD数字を掛け合わせた独自のアルゴリズム予想です。</p>
            {carryover_html}
            <div class="prediction-box">
"""
    labels = ['予想A', '予想B', '予想C', '予想D', '予想E']
    
    for i, pred in enumerate(history_record[0]['predictions']):
        balls = "".join([f'<span class="ball">{n}</span>' for n in pred])
        html += f'                <div class="numbers-row"><div class="row-label">{labels[i]}</div><div class="ball-container">{balls}</div></div>\n'
    
    # ▼▼▼ 修正箇所：予想A〜Eが終わった直後に、解説ブロックを挿入します ▼▼▼
    html += f"""            </div>
            
            <div style="background-color: #f8fafc; border-left: 5px solid #3b82f6; padding: 20px; border-radius: 8px; margin-top: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <h3 style="color: #1e3a8a; margin-top: 0; font-size: 18px; display: flex; align-items: center;">
                    <span style="font-size: 22px; margin-right: 8px;">🤖</span> AI予測ロジック解説（当サイト独自）
                </h3>
                <p style="font-size: 15px; color: #475569; line-height: 1.7; margin-bottom: 12px;">
                    今回の予測は、過去の膨大なデータを基に、<strong>「Random Forest」「XGBoost」「LSTM（ディープラーニング）」</strong>という3つの異なる最先端AIモデルを用いて多角的に算出されました。
                </p>
                <div style="background-color: #eff6ff; padding: 12px 15px; border-radius: 6px; margin-bottom: 12px; border: 1px dashed #bfdbfe;">
                    <strong style="color: #1e40af; font-size: 16px;">🎯 AI総合判定：{confidence_rank}</strong><br>
                    <span style="color: #1e3a8a; font-weight: bold;">{confidence_msg}</span>
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #bfdbfe;">
                        <strong style="color: #e11d48; font-size: 15px;">🔥 AI特注HOT数字：【 {top_nums_str} 】</strong><br>
                        <span style="color: #475569; font-size: 14px;">※上記を軸に構成された<strong>【予想A】</strong>が当サイトの最もおすすめな本命予想です！</span>
                    </div>
                </div>
                <p style="font-size: 15px; color: #475569; line-height: 1.7; margin-bottom: 0;">
                    当サイトのAIは、単純な出現回数（HOT/COLD）だけでなく、数字同士の「共起性（一緒に選ばれやすい組み合わせ）」や、出目のトレンドの波を複合的にスコアリングしています。
                </p>
            </div>

        <div class="section-card">
            <h2 class="section-header" style="color: #475569; border-bottom: 2px solid #e2e8f0;">🔔 最新の抽選結果 ({latest_data['kai']} - {latest_data['date']})</h2>
            <div class="prediction-box" style="background-color: #f8fafc; border-color: #e2e8f0;">
                <div class="numbers-row">
                    <div class="row-label" style="background-color: #e2e8f0; color: #475569;">本数字</div>
                    <div class="ball-container">
                        {"".join([f'<span class="ball" style="background: linear-gradient(135deg, #94a3b8, #64748b);">{n}</span>' for n in latest_data['main']])}
                    </div>
                </div>
                <div class="numbers-row" style="margin-bottom: 0;">
                    <div class="row-label" style="background-color: #dcfce7; color: #16a34a;">ボーナス</div>
                    <div class="ball-container">
                        {"".join([f'<span class="ball" style="background: linear-gradient(135deg, #22c55e, #16a34a);">{n}</span>' for n in latest_data['bonus']])}
                    </div>
                </div>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">📊 直近の出現傾向 (ホット＆コールド)</h2>
            <div class="hc-container">
                <div class="hc-box hot-box"><div class="hc-title">🔥 よく出ている数字 (HOT)</div>\n"""
    for n, count in hot: html += f'<span class="hc-number">{n} ({count}回)</span>'
    html += """</div>\n                <div class="hc-box cold-box"><div class="hc-title">❄️ 出ていない数字 (COLD)</div>\n"""
    for n, count in cold: html += f'<span class="hc-number">{n} ({count}回)</span>'
    html += """</div>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">📝 当サイトの予想と成績履歴</h2>
            <div class="scroll-table-container">
            <table>
                <thead><tr><th>対象回号</th><th>実際の当選番号</th><th>当サイトの成績照合</th></tr></thead>
                <tbody>\n"""
    for record in history_record:
        res_class = "result-win" if "等" in record.get('best_result', '') else "result-lose"
        html += f"""                    <tr>
                        <td style="font-weight:bold; color:#1e3a8a;">{record.get('target_kai', '----')}</td>
                        <td><span style="font-size:16px; font-weight:bold; letter-spacing:1px;">{record.get('actual_main', '----')}</span><br><span style="color:#888; font-size:12px;">{record.get('actual_bonus', '')}</span></td>
                        <td><span class="{res_class}">{record.get('best_result', '----')}</span></td>
                    </tr>\n"""
                    
    # ▼▼▼ 途切れていた文字列をここから繋ぎ直しました ▼▼▼
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
            <h2 class="section-header">📅 過去1年間の当選番号 (実際のデータ)</h2>
            <p style="font-size: 14px; color: #64748b;">※楽天宝くじの直近データ</p>
            <div class="scroll-table-container">
                <table>
                    <thead>
                        <tr><th>回号 (抽選日)</th><th>本数字</th><th>ボーナス数字</th></tr>
                    </thead>
                    <tbody>\n"""
    # ロト6は週2回あるので、1年分出すためにここを大きく広げておきます
    for row in history_data[:104]:
        html += f"""                        <tr>
                            <td style="font-weight:bold; color:#1e3a8a;">{row['kai']}<br><span style="font-size:12px; font-weight:normal; color:#666;">({row['date']})</span></td>
                            <td><span style="font-size:16px; font-weight:bold; letter-spacing:1px;">{", ".join(row['main'])}</span></td>
                            <td><span style="color:#16a34a; font-size:14px; font-weight:bold;">(B: {", ".join(row['bonus'])})</span></td>
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
            <a href="about.html">運営者情報</a> |
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p>※当サイトの予想・データは当選を保証するものではありません。宝くじの購入は自己責任でお願いいたします。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 宝くじ当選予想・データ分析ポータル All Rights Reserved.</p>
    </footer>
</body>
</html>"""

    # --- ⭐️ 自動ポスト・LINE配信用のメッセージを作成して実行 ⭐️ ---
    import datetime
    
    now = datetime.datetime.now()
    today_weekday = now.weekday() # 0:月, 1:火, 2:水, 3:木, 4:金, 5:土, 6:日
    current_hour = now.hour       # 現在の「時間」を取得
    
    next_kai = history_record[0]['target_kai']
    site_url = "https://loto-yosou-ai.com/loto6.html" 
    
    msg = ""
    send_flag = False  # 初期値は「配信しない」

    # ■【月曜日(0)】と【木曜日(3)】：抽選日当日の配信ロジック
    if today_weekday in [0, 3]:
        send_flag = True
        
        # ①【朝〜夕方 (19時前)】：抽選日予告
        if current_hour < 19:
            msg = f"【本日は #ロト6 抽選日🎯】\nいよいよ本日 {next_kai} の抽選日です！\n"
            if carryover_text:
                msg += f"{carryover_text}\n"
            msg += f"\n当サイトのAIアルゴリズムが弾き出した最新予想を無料で公開中！購入前にぜひチェック👇\n{site_url}"

        # ②【夜 (19時以降)】：結果速報と次回予想
        else:
            finished_record = history_record[1] if len(history_record) > 1 else history_record[0]
            finished_kai = finished_record['target_kai']
            best_res = finished_record.get('best_result', 'ハズレ')
            
            is_high_prize = any(prize in best_res for prize in ["1等", "2等", "3等"])
            
            if is_high_prize:
                # 🌟 【高額当選】豪華な特別メッセージ
                msg = f"🚨【緊急・超特大ニュース】🚨\n\nなんと！本日発表の {finished_kai} で\n当サイトのAI予想が…\n\n🎉👑【 {best_res} 】👑🎉\n\nを超高額的中させました！！！\n"
                msg += f"長年のデータ分析がついに完全一致✨\n歴史的瞬間の詳細と、次回({next_kai})の最新予想はこちら👇\n{site_url}"

                # ------ トップページ表示用のメモを保存 ------
                import json
                achievement_data = {
                    "lottery_name": "ロト6",
                    "kai": finished_kai,
                    "prize": best_res
                }
                with open("latest_achievement.json", "w", encoding="utf-8") as f:
                    json.dump(achievement_data, f, ensure_ascii=False)
            
            elif any(prize in best_res for prize in ["4等", "5等"]):
                # 🎈 【通常当選】いつもの的中メッセージ
                msg = f"【#ロト6 的中速報🎯】\n本日 {finished_kai} の結果発表！\n当サイトのAI予想が見事【{best_res}】を的中させました！\n"
                if carryover_text:
                    msg += f"\n{carryover_text}\n"
                msg += f"\n着実に利益を積み重ねています✨\n次回({next_kai})の最新予想はこちら👇\n{site_url}"
                
            else:
                # 💧 【ハズレ等】通常の速報メッセージ
                msg = f"【#ロト6 抽選結果速報🔔】\n本日 {finished_kai} の結果発表！\n"
                if carryover_text:
                    msg += f"\n{carryover_text}\n"
                msg += f"\nデータは日々学習・進化中！次回({next_kai})の最新予想はこちら👇\n{site_url}"

    # ■【水曜日(2)】と【土曜日(5)】：キャリーオーバー発生時のみ配信
    elif today_weekday in [2, 5]:
        # キャリーオーバーが発生しており、かつ「夜（19時以降）」の場合のみ送る
        if carryover_text and current_hour >= 19:
            send_flag = True
            msg = f"【#ロト6 キャリーオーバー発生中🔥】\n次回({next_kai})は高額当選の大チャンス！\n"
            msg += f"現在、{carryover_text}\n"
            msg += f"\n過去1年分のデータから導き出した最新AI予想はこちら👇\n{site_url}"

    # ■ それ以外の曜日（火・金・日）：配信しない
    else:
        send_flag = False

    # 最後に送信処理をまとめる
    if send_flag and msg:
        # post_to_x(msg)
        post_to_line(msg)
        # --- InstagramとThreadsの配信曜日判定 ---
        # 日本時間の現在時刻を取得
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        current_weekday = now.weekday() # 1:火曜, 4:金曜

        if current_weekday in [1, 4]:
            print(f"📅 本日は火曜または金曜（{current_weekday}）のため、SNSへ投稿します。")
            post_to_threads(msg)
            
            # 画像をアップロードしてInstagramに投稿
            image_url = upload_image_to_server(output_image_path)
            if image_url:
                post_to_instagram(image_url, msg)
        else:
            print(f"💤 本日はSNS投稿日ではないため、LINE配信のみで終了します。")

        # ----------------------------------------------------
        # ★ ここからInstagramの自動投稿処理＆動画生成を追加！
        # ----------------------------------------------------
        base_image = "base_image.png"     
        image_path = "loto6_result.jpg"
        
        # ▼▼▼ 数字リストとキャリーオーバー情報をそのまま取り出す ▼▼▼
        # ※カンマで繋がず、配列（リスト）のまま職人に渡します！
        yosou_a_list = history_record[0]['predictions'][0]
        
        caption = f"🎯最新のロト6 AI予想です！\n\n{msg}\n\n#ロト6 #宝くじ #AI予想 #ロトナンバーズ攻略局"
        
        # ① 今までの職人に「静止画」を作成してもらう
        is_created = create_result_image(yosou_a_list, carryover_text, base_image, image_path, target_kai=next_kai, target_date=next_date_str, confidence_rank=global_confidence_rank)

        # ====================================================
        # 🎬 新機能：ここでリール動画の職人も呼び出して自動作成する！
        # ====================================================
        try:
            from create_reel import generate_loto6_reel
            
            is_carryover = "0円" not in carryover_text and "なし" not in carryover_text
            generate_loto6_reel(numbers=yosou_a_list, carryover=carryover_text, has_carryover=is_carryover, target_kai=next_kai, target_date=next_date_str)
            print("✅ 最新の予想データでリール動画(reel_loto6.mp4)の自動生成が完了しました！")
            
            # ▼▼▼ ロト6版 リール自動投稿ロジック ▼▼▼
            video_url = upload_video_to_cloudinary("reel_loto6.mp4") # ★ ファイル名をロト6用に変更
            if video_url:
                post_reel_to_instagram(video_url, caption)
            # ▲▲▲ ここまで ▲▲▲
            # ▼▼▼ 追加：YouTube Shortsへの投稿 ▼▼▼
                yt_title = "🎯 明日のロト6激アツAI予想！ #shorts"
                yt_tags = ["ロト6", "宝くじ", "AI予想", "ショート"]
                upload_to_youtube_shorts("reel_loto6.mp4", yt_title, caption, yt_tags)
                # ▲▲▲ ここまで ▲▲▲

                # ▼▼▼ 新規追加：TikTokへの投稿 ▼▼▼
            post_to_tiktok("reel_loto6.mp4", caption)
            # ▲▲▲ ここまで ▲▲▲
            
        except Exception as e:
            print(f"❌ 動画の自動生成・投稿エラー: {e}")
        # ====================================================
        
        # ② 画像が無事に作れたら、アップロードしてインスタに投稿する！（今までの処理）
        if is_created:
            public_image_url = upload_image_to_server(image_path)
            if public_image_url:
                post_to_instagram(public_image_url, caption)
            else:
                print("⚠️ 画像のURL化に失敗しました。")
        # ----------------------------------------------------
    else:
        print(f"💤 ロト6：配信対象外（キャリーオーバー無し、または対象外の曜日・時間）のためスキップしました。")

    # --------------------------------------------------------
    return html

# --- 最後にファイルを書き出す ---
if __name__ == "__main__":
    final_html = build_html()
    with open('loto6.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
        real_data = get_loto6_full_detail()
    generate_loto6_detail_page(real_data)
    # ==========================================
    # 🎬 【追加】動画作成用のJSONデータを出力する
    # ==========================================
    import json
    try:
        # JSONBinから最新の履歴を直接取得する！
        history = load_history_from_jsonbin()
        latest_pred = history[0] if history else {}
        
        # 予想A〜Eが何個的中したかを判定する関数（簡易版）
        def count_hit(pred_nums, win_nums):
            return len(set(pred_nums) & set(win_nums))

        # 動画に渡すための完璧なデータセットを作成
        video_export_data = {
            "round": real_data.get("round", ""),
            "date": real_data.get("date", ""),
            "main_nums": real_data.get("numbers", []),
            "bonus": real_data.get("bonus", ""),
            "carryover": real_data.get("carryover", "0円"),
            "prizes": real_data.get("prizes", []),
            "predictions": [
                {
                    "name": f"予想{chr(65+i)}", # 予想A, B, C...
                    "nums": ", ".join(pred),
                    "hit": count_hit(pred, real_data.get("numbers", []))
                } for i, pred in enumerate(latest_pred.get("predictions", []))
            ]
        }
        
        # jsonファイルとして保存
        with open('video_data_loto6.json', 'w', encoding='utf-8') as f:
            json.dump(video_export_data, f, ensure_ascii=False, indent=4)
        print("🎬 動画生成用の連携データ (video_data_loto6.json) を出力しました！")
        
    except Exception as e:
        print(f"⚠️ 動画用JSONの出力に失敗しました: {e}")
    # ==========================================
    print("✨ [自動取得・完全決着版] ロト6 の自動更新とXへのポストが完了しました！")