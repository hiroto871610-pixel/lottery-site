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
import os
import datetime
from collections import Counter
import tweepy
import urllib3

# ▼▼▼ .envファイルの読み込み ▼▼▼
from dotenv import load_dotenv
load_dotenv()
import base64
import urllib.request
from PIL import Image, ImageDraw, ImageFont
import time
import cloudinary
import cloudinary.uploader
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# =========================================================
# JSONBin API設定 (ビンゴ5専用)
# =========================================================
JSONBIN_BIN_ID = os.environ.get("JSONBIN_BIN_ID_BINGO5") # ビンゴ5用のIDを設定してください
JSONBIN_API_KEY = os.environ.get("JSONBIN_API_KEY")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}" if JSONBIN_BIN_ID else ""

def load_history_from_jsonbin():
    if not JSONBIN_BIN_ID: return []
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    max_retries = 3
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            res = requests.get(JSONBIN_URL, headers=headers, timeout=60)
            if res.status_code == 200:
                return res.json().get('record', [])
            else:
                print(f"⚠️ JSONBin取得エラー: {res.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    raise SystemExit(f"🚨 JSONBin強制終了: {res.text}")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                raise SystemExit("🚨 通信エラー強制終了")
    return []

def save_history_to_jsonbin(data):
    if not JSONBIN_BIN_ID: return
    headers = {"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}
    try:
        requests.put(JSONBIN_URL, json=data, headers=headers)
    except Exception as e: print(f"保存エラー: {e}")

# =========================================================
# 💰 i-mobile 広告共通パーツ
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

# =========================================================
# 𝕏, Threads, Instagram API等設定
# =========================================================
X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET")
THREADS_USER_ID = os.environ.get("THREADS_USER_ID")
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")

def auto_refresh_threads_token():
    global THREADS_ACCESS_TOKEN
    if not THREADS_ACCESS_TOKEN: return None
    url = f"https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token={THREADS_ACCESS_TOKEN}"
    try:
        res = requests.get(url)
        data = res.json()
        if "access_token" in data:
            new_token = data["access_token"]
            env_path = ".env"
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as file: lines = file.readlines()
                with open(env_path, "w", encoding="utf-8") as file:
                    for line in lines:
                        if line.startswith("THREADS_ACCESS_TOKEN="): file.write(f"THREADS_ACCESS_TOKEN={new_token}\n")
                        else: file.write(line)
            if "GITHUB_ENV" in os.environ:
                with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as f:
                    f.write(f"NEW_THREADS_TOKEN={new_token}\n")
            THREADS_ACCESS_TOKEN = new_token
            return new_token
    except Exception as e: pass
    return THREADS_ACCESS_TOKEN

def post_to_threads(message):
    auto_refresh_threads_token()
    if not all([THREADS_USER_ID, THREADS_ACCESS_TOKEN]): return
    try:
        create_url = f"https://graph.threads.net/v1.0/me/threads"
        res_create = requests.post(create_url, data={"media_type": "TEXT", "text": message, "access_token": THREADS_ACCESS_TOKEN})
        if res_create.status_code != 200: return
        creation_id = res_create.json().get("id")
        publish_url = f"https://graph.threads.net/v1.0/me/threads_publish"
        requests.post(publish_url, data={"creation_id": creation_id, "access_token": THREADS_ACCESS_TOKEN})
    except Exception as e: print(f"Threads通信エラー: {e}")

def upload_image_to_server(image_path):
    url = "https://freeimage.host/api/1/upload"
    try:
        with open(image_path, "rb") as file:
            b64_image = base64.b64encode(file.read()).decode('utf-8')
        payload = {"key": "6d207e02198a847aa98d0a2a901485a5", "action": "upload", "source": b64_image, "format": "json"}
        response = requests.post(url, data=payload)
        result = response.json()
        if result.get("status_code") == 200: return result["image"]["url"]
    except Exception as e: pass
    return None

def post_to_instagram(image_url, caption_text):
    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    container_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
    container_payload = {'image_url': image_url, 'caption': caption_text, 'access_token': access_token}
    container_response = requests.post(container_url, data=container_payload)
    container_data = container_response.json()
    if 'id' not in container_data: return
    creation_id = container_data['id']
    time.sleep(60) 
    publish_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
    requests.post(publish_url, data={'creation_id': creation_id, 'access_token': access_token})

def upload_video_to_cloudinary(video_path):
    cloudinary.config(cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"), api_key=os.environ.get("CLOUDINARY_API_KEY"), api_secret=os.environ.get("CLOUDINARY_API_SECRET"), secure=True)
    try:
        response = cloudinary.uploader.upload(video_path, resource_type="video")
        return response.get("secure_url")
    except Exception as e: return None

def post_reel_to_instagram(video_url, caption_text):
    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    container_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
    container_payload = {'media_type': 'REELS', 'video_url': video_url, 'caption': caption_text, 'access_token': access_token}
    container_response = requests.post(container_url, data=container_payload)
    container_data = container_response.json()
    if 'id' not in container_data: return
    creation_id = container_data['id']
    time.sleep(60) 
    publish_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
    requests.post(publish_url, data={'creation_id': creation_id, 'access_token': access_token})

def add_pinned_comment(video_id, comment_text):
    token_str = os.environ.get("YOUTUBE_TOKEN_JSON")
    try:
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        youtube = build('youtube', 'v3', credentials=creds)
        comment_res = youtube.commentThreads().insert(part="snippet", body={"snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": comment_text}}}}).execute()
        comment_id = comment_res['snippet']['topLevelComment']['id']
        youtube.comments().setModerationStatus(id=comment_id, moderationStatus="published", ban=False).execute()
    except Exception as e: pass

def upload_to_youtube_shorts(video_path, title, description, tags):
    token_str = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not token_str: return
    try:
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        youtube = build('youtube', 'v3', credentials=creds)
        body = {'snippet': {'title': title, 'description': description, 'tags': tags, 'categoryId': '24'}, 'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}}
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
        request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
        response = request.execute()
        video_id = response.get('id')
        fixed_msg = "🎯 本日のAI全予想はこちら（完全無料）！\n👉 https://loto-yosou-ai.com/\n\n次回の予想も見逃さないよう、チャンネル登録お願いします！✨"
        add_pinned_comment(video_id, fixed_msg)
    except Exception as e: pass

def post_to_tiktok(video_path, caption):
    session_id = os.environ.get("TIKTOK_SESSION_ID")
    if not session_id: return
    cookie_content = f".tiktok.com\tTRUE\t/\tFALSE\t2147483647\tsessionid\t{session_id}\n"
    cookie_file = "tiktok_cookies.txt"
    with open(cookie_file, "w") as f: f.write(cookie_content)
    try:
        from tiktok_uploader.upload import upload_video
        upload_video(video_path, description=caption, cookies=cookie_file, headless=True)
    except Exception as e: pass
    finally:
        if os.path.exists(cookie_file): os.remove(cookie_file)

# =========================================================
# ビンゴ5 データ処理・AI予測・画像生成
# =========================================================

def fetch_history_data():
    """楽天宝くじからビンゴ5の過去データを取得（過去1年分）"""
    base_url = "https://takarakuji.rakuten.co.jp/backnumber/bingo5/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    history_data = []
    
    today = datetime.date.today()
    target_urls = [f"{base_url}lastresults/"]
    for i in range(12): # ビンゴ5は週1回なので12ヶ月分で約50回分
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
            text = soup.get_text(separator=' ')
            
            for m in re.finditer(r'第\s*(\d+)\s*回', text):
                kai_num = m.group(1).zfill(4)
                kai_str = f"第{kai_num}回"
                chunk = text[m.end():m.end() + 300]
                
                next_kai_match = re.search(r'第\s*\d+\s*回', chunk)
                if next_kai_match: chunk = chunk[:next_kai_match.start()]
                
                date_m = re.search(r'(\d{4})[/年]\s*(\d{1,2})\s*[/月]\s*(\d{1,2})', chunk)
                if not date_m: continue
                date_str = f"{date_m.group(1)}/{date_m.group(2).zfill(2)}/{date_m.group(3).zfill(2)}"
                
                num_chunk = chunk[date_m.end():]
                all_digits = re.findall(r'\d+', num_chunk)
                valid_nums = [n.zfill(2) for n in all_digits if 1 <= int(n) <= 40]
                
                # ビンゴ5はボーナスなしの計8個
                if len(valid_nums) >= 8:
                    main_nums = valid_nums[:8]
                    if not any(d['kai'] == kai_str for d in history_data):
                        history_data.append({"kai": kai_str, "date": date_str, "main": main_nums})
        except Exception: pass
            
    history_data.sort(key=lambda x: int(re.search(r'\d+', x['kai']).group()), reverse=True)
    return history_data

def analyze_trends(history_data):
    all_nums = []
    for data in history_data: all_nums.extend(data['main'])
    counts = Counter(all_nums)
    for i in range(1, 41):
        num_str = str(i).zfill(2)
        if num_str not in counts: counts[num_str] = 0
    sorted_counts = counts.most_common()
    hot = sorted_counts[:5]
    cold = list(reversed(sorted_counts))[:5]
    return hot, cold

def generate_hybrid_predictions(X_train, y_train, X_latest, window_size=10, num_predictions=5):
    import numpy as np
    print("🧠 ハイブリッドAI（RF + XGB + LSTM）による予測を開始します...")

    # 1〜40の数字の確率を算出
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    rf_preds = rf_model.predict_proba(X_latest)
    
    prob_rf = np.zeros(41)
    if isinstance(rf_preds, list):
        for i, p in enumerate(rf_preds):
            if i + 1 <= 40: prob_rf[i+1] = p[0][1] if p.shape[1] > 1 else 0
    else:
        for idx, cls in enumerate(rf_model.classes_):
            if 1 <= int(cls) <= 40: prob_rf[int(cls)] = rf_preds[0][idx]

    xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', random_state=42)
    xgb_model.fit(X_train, y_train)
    xgb_preds = xgb_model.predict_proba(X_latest)
    
    prob_xgb = np.zeros(41)
    if isinstance(xgb_preds, list):
        for i, p in enumerate(xgb_preds):
            if i + 1 <= 40: prob_xgb[i+1] = p[0][1] if p.shape[1] > 1 else 0
    else:
        xgb_preds = xgb_preds[0]
        if hasattr(xgb_model, 'classes_') and len(xgb_model.classes_) == len(xgb_preds):
            for idx, cls in enumerate(xgb_model.classes_):
                if 1 <= int(cls) <= 40: prob_xgb[int(cls)] = xgb_preds[idx]
        else:
            for i in range(min(len(xgb_preds), 40)): prob_xgb[i+1] = xgb_preds[i]

    X_train_3d = X_train.reshape((X_train.shape[0], 1, X_train.shape[1]))
    X_latest_3d = X_latest.reshape((1, 1, X_latest.shape[1]))
    lstm_model = Sequential([
        LSTM(64, activation='relu', input_shape=(1, X_train.shape[1])),
        Dense(41, activation='softmax')
    ])
    lstm_model.compile(optimizer='adam', loss='sparse_categorical_crossentropy')
    lstm_model.fit(X_train_3d, y_train, epochs=10, verbose=0)
    prob_lstm = lstm_model.predict(X_latest_3d)[0]

    final_prob = (prob_rf + prob_xgb + prob_lstm) / 3.0
    
    # ランク判定
    avg_max_score = np.mean(np.sort(final_prob)[-8:])
    if avg_max_score > 0.3:
        confidence_rank, confidence_msg = "Sランク", "🔥 激アツ！3つの最先端AIの予測が強く一致しました！"
    elif avg_max_score > 0.15:
        confidence_rank, confidence_msg = "Aランク", "✨ チャンス！複数のAIが同じ傾向を示しています。"
    else:
        confidence_rank, confidence_msg = "Bランク", "⚠️ 波乱含み。AI間で意見が分かれており、荒れる可能性があります。"

    # ビンゴ5独自の8枠ルールを適用した予測生成
    bingo_bins = [
        list(range(1, 6)), list(range(6, 11)), list(range(11, 16)), list(range(16, 21)),
        list(range(21, 26)), list(range(26, 31)), list(range(31, 36)), list(range(36, 41))
    ]
    
    predictions = []
    seen = set()
    
    for _ in range(3000):
        cand = []
        for b_nums in bingo_bins:
            weights = [final_prob[n] for n in b_nums]
            if sum(weights) > 0:
                cand.append(random.choices(b_nums, weights=weights)[0])
            else:
                cand.append(random.choice(b_nums))
        
        t_cand = tuple(cand)
        if t_cand not in seen:
            seen.add(t_cand)
            predictions.append([str(n).zfill(2) for n in cand])
        if len(predictions) == num_predictions:
            break

    top3_indices = np.argsort(final_prob)[::-1]
    top_nums = [str(i).zfill(2) for i in top3_indices if 1 <= i <= 40][:3]
    top_nums_str = "、".join(top_nums)

    return predictions, confidence_rank, confidence_msg, top_nums_str

def generate_advanced_predictions(history_data):
    print("🧠 AI（Random Forest）が過去の傾向を学習中...")
    if not history_data or len(history_data) < 20: return [], "Cランク", "データ不足です", ""
    main_draws = [list(map(int, d['main'])) for d in reversed(history_data)]
    features, labels = [], []
    window_size = 10 
    for i in range(window_size, len(main_draws) - 1):
        past_window = [num for draw in main_draws[i-window_size:i] for num in draw]
        past_counts = Counter(past_window)
        target_draw = main_draws[i] 
        for num in range(1, 41):
            features.append([past_counts.get(num, 0)])
            labels.append(1 if num in target_draw else 0)

    X = np.array(features)
    y = np.array(labels)
    latest_window = [num for draw in main_draws[-window_size:] for num in draw]
    latest_counts = Counter(latest_window)
    X_latest = np.array([[latest_counts.get(num, 0)] for num in range(1, 41)])
    
    predictions, confidence_rank, confidence_msg, top_nums_str = generate_hybrid_predictions(X, y, X_latest)
    return predictions, confidence_rank, confidence_msg, top_nums_str

def evaluate_bingo_lines(pred_nums, win_nums):
    """ビンゴ5の成立ライン数を正確に計算するチェッカー"""
    if win_nums == "----" or not win_nums: return "抽選待ち"
    m = [p in win_nums for p in pred_nums]
    if len(m) != 8: return "ハズレ"
    
    lines = 0
    if m[0] and m[1] and m[2]: lines += 1 # 上ヨコ
    if m[3] and m[4]: lines += 1          # 中ヨコ（FREE含む）
    if m[5] and m[6] and m[7]: lines += 1 # 下ヨコ
    if m[0] and m[3] and m[5]: lines += 1 # 左タテ
    if m[1] and m[6]: lines += 1          # 中タテ（FREE含む）
    if m[2] and m[4] and m[7]: lines += 1 # 右タテ
    if m[0] and m[7]: lines += 1          # ナナメ1（FREE含む）
    if m[2] and m[5]: lines += 1          # ナナメ2（FREE含む）
    
    if lines == 8: return "1等🎯"
    elif lines == 6: return "2等🎯"
    elif lines == 5: return "3等🎯"
    elif lines == 4: return "4等"
    elif lines == 3: return "5等"
    elif lines == 2: return "6等"
    elif lines == 1: return "7等"
    else: return f"ハズレ({sum(m)}個一致)"

def manage_history(latest_data, new_predictions):
    print("☁️ JSONBin(Bingo5)から履歴を取得中...")
    history_record = load_history_from_jsonbin()
            
    latest_kai = latest_data['kai']
    latest_kai_num = int(re.search(r'\d+', latest_kai).group())
    
    for record in history_record:
        record_kai_match = re.search(r'\d+', record.get('target_kai', ''))
        if record.get('status') == 'waiting' and record_kai_match:
            record_kai_num = int(record_kai_match.group())
            if record_kai_num == latest_kai_num:
                best_lines = -1
                best_result = "ハズレ"
                for p in record['predictions']:
                    res = evaluate_bingo_lines(p, latest_data['main'])
                    line_num = 8 if "1等" in res else (6 if "2等" in res else (5 if "3等" in res else (4 if "4等" in res else (3 if "5等" in res else (2 if "6等" in res else (1 if "7等" in res else 0))))))
                    if line_num > best_lines:
                        best_lines = line_num
                        best_result = res
                        
                record['status'] = 'finished'
                record['actual_main'] = ", ".join(latest_data['main'])
                record['best_result'] = best_result
                record['target_kai'] = latest_kai 
                
    next_kai_num = latest_kai_num + 1
    next_kai = f"第{next_kai_num:04d}回"
    
    if not any(int(re.search(r'\d+', r.get('target_kai', '0')).group()) == next_kai_num for r in history_record if re.search(r'\d+', r.get('target_kai', '0'))):
        history_record.insert(0, {
            "target_kai": next_kai,
            "status": "waiting",
            "predictions": new_predictions,
            "actual_main": "----",
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
    print("☁️ JSONBin(Bingo5)へ最新データを保存中...")
    save_history_to_jsonbin(history_record)
    return history_record

def get_next_bingo5_date():
    """次回抽選日(水曜)を計算"""
    now = datetime.datetime.now()
    if now.hour >= 19 or (now.hour == 18 and now.minute >= 30):
        base_date = now.date() + datetime.timedelta(days=1)
    else:
        base_date = now.date()
    n_days = 0
    while (base_date + datetime.timedelta(days=n_days)).weekday() != 2: # 2 = 水曜
        n_days += 1
    next_date = base_date + datetime.timedelta(days=n_days)
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return f"{next_date.month}月{next_date.day}日({weekdays[next_date.weekday()]})"

def get_bingo5_full_detail():
    print("☁️ 楽天宝くじからビンゴ5の詳細データを抽出中...")
    url = "https://takarakuji.rakuten.co.jp/backnumber/bingo5/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    result_data = {"round": "", "date": "", "numbers": [], "prizes": []}

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            res.encoding = 'euc-jp'
            soup = BeautifulSoup(res.content, 'html.parser')

            target_table = None
            for table in soup.find_all('table'):
                text = table.get_text()
                if '1等' in text and '2等' in text:
                    target_table = table
                    break
            
            if not target_table: return None

            for tr in target_table.find_all('tr'):
                header_cell = tr.find(['th', 'td'])
                if not header_cell: continue
                header_text = header_cell.get_text(strip=True)
                
                if '数字' in header_text or '当せん' in header_text:
                    row_text = tr.get_text(separator=' ')
                    nums = re.findall(r'(?<!\d)\d{1,2}(?!\d)', row_text)
                    valid_n = [str(n).zfill(2) for n in nums if 1 <= int(n) <= 40]
                    if len(valid_n) >= 8: result_data["numbers"] = valid_n[:8]
                
                for i in range(1, 8):
                    if f'{i}等' in header_text:
                        tds = tr.find_all('td')
                        if len(tds) >= 2:
                            result_data["prizes"].append({"grade": f"{i}等", "winners": tds[-2].get_text(strip=True), "prize": tds[-1].get_text(strip=True)})

            table_text = target_table.get_text(separator=' ', strip=True)
            m_round = re.search(r'第\s*\d+\s*回', table_text)
            m_date = re.search(r'\d{4}[年/]\d{1,2}[月/]\d{1,2}日?', table_text)
            if m_round: result_data["round"] = m_round.group().replace(' ', '')
            if m_date: result_data["date"] = m_date.group()

            return result_data
    except Exception as e:
        print(f"❌ ビンゴ5データ解析エラー: {e}")
        return None

def create_result_image(bingo5_nums, base_image_path, output_image_path, target_kai="", target_date="", confidence_rank="Aランク"):
    print("🎨 ビンゴ5専用の予想画像を生成中（ピンクテーマ・2段組）...")
    try:
        img = Image.open(base_image_path)
        W, H = img.size 
    except FileNotFoundError: return False

    draw = ImageDraw.Draw(img)
    font_path = "NotoSansJP-Bold.ttf"
    if not os.path.exists(font_path): urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/notosansjp/static/NotoSansJP-Bold.ttf", font_path)

    shadow_color = (100, 100, 100)
    white = (255, 255, 255)
    title_color = white          
    ball_color = (219, 39, 119) # ピンク #db2777

    ball_dia = 200  
    ball_space_x = 40 
    ball_space_y = 60 
    shadow_offset = 8 

    font_title = ImageFont.truetype(font_path, 90)
    font_num = ImageFont.truetype(font_path, 115) 
    font_sub = ImageFont.truetype(font_path, 50)

    current_y = 300 
    title = f"【ビンゴ5 最新AI予想A {confidence_rank}】"
    subtitle = f"{target_kai} ({target_date})"
    
    left, top, right, bottom = draw.textbbox((0, 0), title, font=font_title)
    title_x = (W - (right - left)) / 2
    draw.text((title_x + shadow_offset, current_y + shadow_offset), title, font=font_title, fill=shadow_color)
    draw.text((title_x, current_y), title, font=font_title, fill=title_color)

    left_s, top_s, right_s, bottom_s = draw.textbbox((0, 0), subtitle, font=font_sub)
    sub_x = (W - (right_s - left_s)) / 2
    draw.text((sub_x + shadow_offset, current_y + 110 + shadow_offset), subtitle, font=font_sub, fill=shadow_color)
    draw.text((sub_x, current_y + 110), subtitle, font=font_sub, fill=white)
    
    current_y += (bottom - top) + 80 

    rows = [bingo5_nums[:4], bingo5_nums[4:8]]

    for row_nums in rows:
        total_ball_w = (ball_dia * len(row_nums)) + (ball_space_x * (len(row_nums) - 1))
        ball_x = (W - total_ball_w) / 2 

        for digit in row_nums:
            draw.ellipse([ball_x + shadow_offset, current_y + shadow_offset, ball_x + ball_dia + shadow_offset, current_y + ball_dia + shadow_offset], fill=shadow_color)
            draw.ellipse([ball_x, current_y, ball_x + ball_dia, current_y + ball_dia], fill=ball_color)
            left, top, right, bottom = draw.textbbox((0, 0), digit, font=font_num)
            num_x = ball_x + (ball_dia - (right - left)) / 2
            num_y = current_y + (ball_dia - (bottom - top)) / 2 - 15 
            draw.text((num_x, num_y), digit, font=font_num, fill=white)
            ball_x += ball_dia + ball_space_x
        current_y += ball_dia + ball_space_y

    img = img.convert("RGB") 
    img.save(output_image_path, "JPEG", quality=95)
    return True

# --- HTML構築 ---
def build_html():
    print("🔄 ビンゴ5 データ取得＆解析を開始...")
    history_data = fetch_history_data()
    latest_data = history_data[0]
    hot, cold = analyze_trends(history_data)
    
    predictions, confidence_rank, confidence_msg, top_nums_str = generate_advanced_predictions(history_data)
    history_record = manage_history(latest_data, predictions)
    next_date_str = get_next_bingo5_date()
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【{history_record[0]['target_kai']}】ビンゴ5当選予想・データ分析ポータル | 最新AI予想</title>
    <meta name="description" content="{history_record[0]['target_kai']}のビンゴ5当選予想。過去のデータから導き出したHOT数字・COLD数字と完全無料のAIアルゴリズム予想を公開中！">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #fdf2f8; color: #333; }}
        header {{ background-color: #be185d; padding: 10px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #be185d; padding: 12px 12px; font-size: 14px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; transition: all 0.3s; }}
        nav a.active {{ border-bottom: 3px solid #db2777; color: #db2777; }}
        nav a:hover {{ background-color: #fdf2f8; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #db2777; border-bottom: 2px solid #fbcfe8; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; }}
        .prediction-box {{ background-color: #fdf2f8; border: 2px solid #f9a8d4; border-radius: 12px; padding: 25px; margin-bottom: 20px;}}
        .numbers-row {{ background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; align-items: center; }}
        .row-label {{ font-size: 18px; font-weight: bold; color: #9d174d; background-color: #fce7f3; padding: 5px 15px; border-radius: 4px; margin-right: 20px; min-width: 60px; text-align: center; }}
        .ball-container {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .ball {{ display: inline-flex; justify-content: center; align-items: center; width: 42px; height: 42px; background: linear-gradient(135deg, #f472b6, #db2777); color: white; border-radius: 50%; font-size: 18px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.3); }}

        @media (max-width: 600px) {{ .numbers-row {{ flex-direction: column; align-items: flex-start; padding: 15px;}} .row-label {{ margin-bottom: 10px; }} .ball {{ width: 36px; height: 36px; font-size: 16px;}} }}
        
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
        .result-win {{ color: #db2777; font-weight: bold; background-color: #fce7f3; padding: 4px 8px; border-radius: 4px; }}
        .result-lose {{ color: #94a3b8; }}
        .scroll-table-container {{ max-height: 400px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 15px; }}
        .scroll-table-container table {{ margin-top: 0; border-collapse: separate; border-spacing: 0; }}
        .scroll-table-container th {{ position: sticky; top: 0; z-index: 1; box-shadow: 0 2px 2px -1px rgba(0,0,0,0.1); }}
        footer {{ background-color: #1e293b; color: #94a3b8; text-align: center; padding: 40px 20px; margin-top: 60px; font-size: 13px; border-top: 4px solid #db2777; }}
        .footer-links {{ margin-bottom: 15px; }}
        .footer-links a {{ color: #cbd5e1; text-decoration: none; margin: 0 10px; transition: color 0.2s; }}
        .footer-links a:hover {{ color: white; text-decoration: underline; }}
        .ad-pc {{ display: block; }}
        .ad-sp {{ display: none; }}
        @media (max-width: 600px) {{ .ad-pc {{ display: none; }} .ad-sp {{ display: block; }} }}
    </style>
</head>
<body>
    <header>
        <a href="index.html" style="text-decoration: none;">
            <img src="Lotologo001.png" alt="宝くじ当選予想・データ分析ポータル" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">ビンゴ5当選予想・速報</div>
        </a>
    </header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="bingo5.html" class="active">ビンゴ5</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="column.html">攻略ガイド🔰</a>
        <a href="archive.html" >YOUTUBE🎥</a>
    </nav>

<div class="section-card" style="text-align: center; background: linear-gradient(to right, #ffffff, #fdf2f8); border: 2px solid #db2777; margin-top: 25px; margin-bottom: 30px; padding: 25px 15px; border-radius: 12px;">
        <h3 style="color: #9d174d; margin-top: 0; font-size: 20px; font-weight: bold;">📊 最新の当せん詳細データ</h3>
        <a href="bingo5_detail.html" style="display: inline-block; background-color: #db2777; color: white; text-decoration: none; padding: 15px 35px; border-radius: 30px; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(219, 39, 119, 0.3); transition: transform 0.2s;">
            🔍 詳細ページを確認する
        </a>
    </div>

    <div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <div class="ad-pc">{imobile_ad2_pc}</div>
        <div class="ad-sp">{imobile_ad2_sp}</div>
    </div>

    <div class="container">
        <div class="section-card" style="background: linear-gradient(to right, #ffffff, #fdf2f8); border-left: 5px solid #db2777; padding: 20px;">
            <div style="font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 10px;">⏰ 次回抽選日と購入期限</div>
            <div style="font-size: 15px; color: #475569;">
                <span style="display:inline-block; margin-right: 20px;">次回抽選: <strong style="color: #db2777; font-size: 18px;">{next_date_str}</strong></span>
                <span style="display:inline-block;">購入期限: 当日 <strong style="color: #ef4444; font-size: 18px;">18:30</strong> まで</span>
            </div>
            <div style="font-size:11px; color:#64748b; margin-top: 5px;">※ネット購入（楽天銀行等）の原則的な締め切り時間です。</div>
        </div>

        <div class="section-card">
            <h2 class="section-header">🎯 次回 ({history_record[0]['target_kai']}) ビンゴ5の予想</h2>
            <p>ビンゴ5の「各枠から1つ選ぶ」ルールに完全対応した3つのAI複合予測です。</p>
            <div class="prediction-box">
"""
    labels = ['予想A', '予想B', '予想C', '予想D', '予想E']
    for i, pred in enumerate(history_record[0]['predictions']):
        balls = "".join([f'<span class="ball">{n}</span>' for n in pred])
        html += f'                <div class="numbers-row"><div class="row-label">{labels[i]}</div><div class="ball-container">{balls}</div></div>\n'
    
    html += f"""            </div>
            
            <div style="background-color: #f8fafc; border-left: 5px solid #db2777; padding: 20px; border-radius: 8px; margin-top: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <h3 style="color: #9d174d; margin-top: 0; font-size: 18px; display: flex; align-items: center;">
                    <span style="font-size: 22px; margin-right: 8px;">🤖</span> AI予測ロジック解説（当サイト独自）
                </h3>
                <p style="font-size: 15px; color: #475569; line-height: 1.7; margin-bottom: 12px;">
                    過去のデータを基に、<strong>「Random Forest」「XGBoost」「LSTM（ディープラーニング）」</strong>の3つのAIが各枠（8箇所）の出現確率を算出。ビンゴ5の公式ルールに従って最適解を生成しています。
                </p>
                <div style="background-color: #fdf2f8; padding: 12px 15px; border-radius: 6px; margin-bottom: 12px; border: 1px dashed #fbcfe8;">
                    <strong style="color: #9d174d; font-size: 16px;">🎯 AI総合判定：{confidence_rank}</strong><br>
                    <span style="color: #be185d; font-weight: bold;">{confidence_msg}</span>
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #fbcfe8;">
                        <strong style="color: #e11d48; font-size: 15px;">🔥 AI特注HOT数字：【 {top_nums_str} 】</strong><br>
                        <span style="color: #475569; font-size: 14px;">※上記を軸に構成された<strong>【予想A】</strong>がおすすめの本命予想です！</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header" style="color: #475569; border-bottom: 2px solid #e2e8f0;">🔔 最新の抽選結果 ({latest_data['kai']} - {latest_data['date']})</h2>
            <div class="prediction-box" style="background-color: #f8fafc; border-color: #e2e8f0;">
                <div class="numbers-row">
                    <div class="row-label" style="background-color: #e2e8f0; color: #475569;">抽せん数字</div>
                    <div class="ball-container">
                        {"".join([f'<span class="ball" style="background: linear-gradient(135deg, #94a3b8, #64748b);">{n}</span>' for n in latest_data['main']])}
                    </div>
                </div>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">📊 直近の出現傾向 (過去1年分の集計)</h2>
            <div class="hc-container">
                <div class="hc-box hot-box"><div class="hc-title">🔥 よく出ている数字 (HOT)</div>"""
    for n, count in hot:
        html += f'<span class="hc-number">{n} ({count}回)</span>'
    html += """</div>
                <div class="hc-box cold-box"><div class="hc-title">❄️ 出ていない数字 (COLD)</div>"""
    for n, count in cold:
        html += f'<span class="hc-number">{n} ({count}回)</span>'
    html += """</div>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">📝 当サイトの予想と成績履歴</h2>
            <div class="scroll-table-container">
            <table>
                <thead><tr><th>対象回号</th><th>実際の当選番号</th><th>当サイトの成績照合</th></tr></thead>
                <tbody>
"""
    for record in history_record:
        res_class = "result-win" if "等" in record.get('best_result', '') else "result-lose"
        html += f"""                    <tr>
                        <td style="font-weight:bold; color:#be185d;">{record.get('target_kai', '----')}</td>
                        <td><span style="font-size:16px; font-weight:bold; letter-spacing:1px;">{record.get('actual_main', '----')}</span></td>
                        <td><span class="{res_class}">{record.get('best_result', '----')}</span></td>
                    </tr>\n"""

    html += f"""                </tbody>
            </table>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">📅 過去1年間の当選番号 (実際のデータ)</h2>
            <p style="font-size: 14px; color: #64748b;">※楽天宝くじのアーカイブデータより抽出（過去1年分）</p>
            <div class="scroll-table-container">
                <table>
                    <thead>
                        <tr><th>回号 (抽選日)</th><th>抽せん数字</th></tr>
                    </thead>
                    <tbody>
"""
    for row in history_data[:52]:
        html += f"""                        <tr>
                            <td style="font-weight:bold; color:#be185d;">{row['kai']}<br><span style="font-size:12px; font-weight:normal; color:#666;">({row['date']})</span></td>
                            <td><span style="font-size:16px; font-weight:bold; letter-spacing:1px;">{", ".join(row['main'])}</span></td>
                        </tr>\n"""

    html += f"""                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <div class="ad-pc">{imobile_ad3_pc}</div>
        <div class="ad-sp">{imobile_ad3_sp}</div>
    </div>

    <footer>
        <div class="footer-links">
            <a href="about.html">運営者情報</a> |
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p>※当サイトの予想・データは当選を保証するものではありません。宝くじの購入は自己責任でお願いいたします。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 ロト＆ナンバーズ攻略局🎯完全無料のAI予想 All Rights Reserved.</p>
    </footer>

    <div class="ad-sp">
        {imobile_overlay}
    </div>

</body>
</html>"""

    # --- ⭐️ SNS配信用ロジック（火曜と木曜） ⭐️ ---
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today_weekday = now.weekday()
    current_hour = now.hour
    
    next_kai = history_record[0]['target_kai']
    site_url = "https://loto-yosou-ai.com/bingo5.html" 
    
    sns_send_flag = False
    sns_msg = ""

    # 水曜が抽選なので、火曜(1)と木曜(3)の夜に配信
    if today_weekday == 1 and current_hour >= 19: # 火曜日（前日）
        sns_send_flag = True
        sns_msg = f"【明日は #ビンゴ5 抽選日🎯】\n明日 {next_kai} の最新AI予想を無料公開中！\n\nビンゴ5の複雑な確率をAIが攻略✨激アツ本命予想はこちら👇\n{site_url}"
        
    elif today_weekday == 3 and current_hour >= 19: # 木曜日（翌日速報）
        sns_send_flag = True
        finished_record = history_record[1] if len(history_record) > 1 else history_record[0]
        finished_kai = finished_record['target_kai']
        best_res = finished_record.get('best_result', 'ハズレ')
        
        if any(prize in best_res for prize in ["1等", "2等", "3等"]):
            sns_msg = f"🚨【号外：高額当選発生】🚨\n\nなんと！昨日発表の {finished_kai} で\n当サイトのAI予想が…\n\n🎉👑【 {best_res} 】👑🎉\n\nを見事的中させました！！！\n次回({next_kai})の最新予想はこちら👇\n{site_url}"
        elif any(prize in best_res for prize in ["4等", "5等", "6等", "7等"]):
            sns_msg = f"【#ビンゴ5 的中速報🎯】\n昨日 {finished_kai} の結果発表！\n当サイトのAI予想が見事【{best_res}】を的中させました！\n\n着実に利益を積み重ねています✨次回({next_kai})の最新予想はこちら👇\n{site_url}"
        else:
            sns_msg = f"【#ビンゴ5 抽選結果速報🔔】\n昨日 {finished_kai} の結果発表！\nAIはデータを学習し進化します！次回({next_kai})の最新予想はこちら👇\n{site_url}"

    if sns_send_flag and sns_msg:
        print(f"📅 本日はSNS投稿タイミング（曜日:{today_weekday}、{current_hour}時台）のため、SNSへ投稿します。")
        post_to_threads(sns_msg)
        
        base_image = "base_image.png"     
        image_path = "bingo5_result.jpg"
        yosou_a_list = history_record[0]['predictions'][0]
        caption = f"🎯最新のビンゴ5 AI予想です！\n\n{sns_msg}\n\n#ビンゴ5 #宝くじ #AI予想 #ロトナンバーズ攻略局"
        
        is_created = create_result_image(yosou_a_list, base_image, image_path, target_kai=next_kai, target_date=next_date_str, confidence_rank=confidence_rank)

        try:
            from create_reel import generate_bingo5_reel
            generate_bingo5_reel(numbers=yosou_a_list, target_kai=next_kai, target_date=next_date_str)
            video_url = upload_video_to_cloudinary("reel_bingo5.mp4")
            if video_url:
                post_reel_to_instagram(video_url, caption)
                
            yt_title = "🎯 明日のビンゴ5激アツAI予想！ #shorts"
            yt_tags = ["ビンゴ5", "宝くじ", "AI予想", "ショート"]
            upload_to_youtube_shorts("reel_bingo5.mp4", yt_title, caption, yt_tags)
            post_to_tiktok("reel_bingo5.mp4", caption)
        except Exception as e:
            print(f"❌ 動画の自動生成・投稿エラー: {e}")
        
        if is_created:
            public_image_url = upload_image_to_server(image_path)
            if public_image_url:
                post_to_instagram(public_image_url, caption)
    else:
        print("💤 ビンゴ5：SNS動画配信対象外のためスキップしました。")

    return html

def generate_bingo5_detail_page(result_data):
    print("🔄 ビンゴ5 詳細ページ(HTML)をベースデザインで生成中...")
    if not result_data:
        result_data = {"round": "第----回", "date": "----/--/--", "numbers": ["-","-","-","-","-","-","-","-"], "prizes": []}

    main_balls = "".join([f'<span class="ball">{n}</span>' for n in result_data.get("numbers", [])])
    trs = ""
    for p in result_data.get("prizes", []):
        trs += f"<tr><td style='font-weight:bold; color:#9d174d;'>{p['grade']}</td><td style='color:#db2777; font-weight:bold; font-size:16px;'>{p['prize']}</td><td style='color:#64748b;'>{p['winners']}</td></tr>"

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【{result_data.get('round', '')}】ビンゴ5 抽選結果詳細データ</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #fdf2f8; color: #333; }}
        header {{ background-color: #be185d; padding: 10px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #be185d; padding: 12px 12px; font-size: 14px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; transition: all 0.3s; }}
        nav a.active {{ border-bottom: 3px solid #db2777; color: #db2777; }}
        nav a:hover {{ background-color: #fdf2f8; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #db2777; border-bottom: 2px solid #fbcfe8; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; }}
        .prediction-box {{ background-color: #fdf2f8; border: 2px solid #f9a8d4; border-radius: 12px; padding: 25px; margin-bottom: 20px;}}
        .numbers-row {{ background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; align-items: center; wrap; }}
        .row-label {{ font-size: 18px; font-weight: bold; color: #9d174d; background-color: #fce7f3; padding: 5px 15px; border-radius: 4px; margin-right: 20px; min-width: 60px; text-align: center; }}
        .ball-container {{ display: flex; gap: 8px; flex-wrap: wrap; margin-right: auto;}}
        .ball {{ display: inline-flex; justify-content: center; align-items: center; width: 42px; height: 42px; background: linear-gradient(135deg, #f472b6, #db2777); color: white; border-radius: 50%; font-size: 18px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.3); }}
        @media (max-width: 600px) {{ .numbers-row {{ flex-direction: column; align-items: flex-start; padding: 15px; gap: 10px;}} .row-label {{ margin-right: 0; margin-bottom: 5px; }} .ball {{ width: 36px; height: 36px; font-size: 16px;}} }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 15px; text-align: center; }}
        th, td {{ padding: 15px; border-bottom: 1px solid #e2e8f0; }}
        th {{ background-color: #f8fafc; color: #475569; font-weight: bold; }}
        footer {{ background-color: #1e293b; color: #94a3b8; text-align: center; padding: 40px 20px; margin-top: 60px; font-size: 13px; border-top: 4px solid #db2777; }}
        .footer-links {{ margin-bottom: 15px; }}
        .footer-links a {{ color: #cbd5e1; text-decoration: none; margin: 0 10px; transition: color 0.2s; }}
        .footer-links a:hover {{ color: white; text-decoration: underline; }}
        .ad-pc {{ display: block; }}
        .ad-sp {{ display: none; }}
        @media (max-width: 600px) {{ .ad-pc {{ display: none; }} .ad-sp {{ display: block; }} }}
    </style> 
</head>
<body>
    <header>
        <a href="index.html" style="text-decoration: none;">
            <img src="Lotologo001.png" alt="ロト＆ナンバーズ攻略局" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">ビンゴ5詳細データ</div>
        </a>
    </header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="bingo5.html" class="active">ビンゴ5</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="column.html">攻略ガイド🔰</a>
        <a href="archive.html" >YOUTUBE🎥</a>
    </nav>

    <div class="container">
        <h1 style="color: #9d174d; font-size: 26px; text-align: center; border-bottom: 3px solid #db2777; padding-bottom: 15px; margin-bottom: 30px;">
            {result_data.get('round', '')} ({result_data.get('date', '')}) 抽選結果詳細
        </h1>

        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <div class="ad-pc">{imobile_ad2_pc}</div>
            <div class="ad-sp">{imobile_ad2_sp}</div>
        </div>

        <div class="section-card">
            <h2 class="section-header">🎯 ビンゴ5 抽選結果</h2>
            <div class="prediction-box">
                <div class="numbers-row">
                    <div class="row-label">抽せん数字</div>
                    <div class="ball-container">{main_balls}</div>
                </div>
            </div>
            <table>
                <thead><tr><th>等級</th><th>当せん金額</th><th>口数</th></tr></thead>
                <tbody>{trs}</tbody>
            </table>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="bingo5.html" style="display: inline-block; background-color: #db2777; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                ◀ ビンゴ5 AI予想トップに戻る
            </a>
        </div>
        
        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <div class="ad-pc">{imobile_ad3_pc}</div>
            <div class="ad-sp">{imobile_ad3_sp}</div>
        </div>
    </div>
    
    <footer>
        <div class="footer-links">
            <a href="about.html">運営者情報</a> |
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p>※当サイトのデータは当選を保証するものではありません。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 ロト＆ナンバーズ攻略局🎯完全無料のAI予想 All Rights Reserved.</p>
    </footer>
    <div class="ad-sp">{imobile_overlay}</div>
</body>
</html>"""
    with open("bingo5_detail.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ ビンゴ5 詳細ページ(ベースデザイン版) の生成が完了しました！")

if __name__ == "__main__":
    final_html = build_html()
    with open('bingo5.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    real_data = get_bingo5_full_detail()
    generate_bingo5_detail_page(real_data)
    
    try:
        history = load_history_from_jsonbin()
        latest_pred = history[0] if history else {}
        
        video_export_data = {
            "round": real_data.get("round", ""),
            "date": real_data.get("date", ""),
            "main_nums": real_data.get("numbers", []),
            "prizes": real_data.get("prizes", []),
            "predictions": [
                {
                    "name": f"予想{chr(65+i)}", 
                    "nums": ", ".join(pred),
                    "result": evaluate_bingo_lines(pred, real_data.get("numbers", []))
                } for i, pred in enumerate(latest_pred.get("predictions", []))
            ]
        }
        with open('video_data_bingo5.json', 'w', encoding='utf-8') as f:
            json.dump(video_export_data, f, ensure_ascii=False, indent=4)
        print("🎬 動画生成用の連携データ (video_data_bingo5.json) を出力しました！")
    except Exception as e:
        print(f"⚠️ 動画用JSONの出力に失敗しました: {e}")
    print("✨ ビンゴ5の全データ取得と自動処理が完了しました！")