import random
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
        res = requests.get(JSONBIN_URL, headers=headers)
        return res.json().get('record', []) if res.status_code == 200 else []
    except Exception: return []

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
    """ImgBBがインスタにブロックされるため、制限のない別サーバー(Catbox)を使用"""
    url = "https://catbox.moe/user/api.php"
    print("☁️ 画像をアップロードサーバー(Catbox)に送信中...")
    
    # ★ここを追加：一般のパソコンからのアクセスに見せかける「偽装」設定
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        with open(image_path, "rb") as file:
            payload = {"reqtype": "fileupload"}
            files = {"fileToUpload": file}
            # headers を通信に組み込む
            response = requests.post(url, data=payload, files=files, headers=headers)
            
        if response.status_code == 200 and response.text.strip() != "":
            image_url = response.text.strip()
            print(f"✅ 画像のURL化成功: {image_url}")
            return image_url
        else:
            print(f"❌ サーバーエラーまたは空の応答: {response.text}")
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

def create_result_image(n4_text, n3_text, base_image_path, output_image_path):
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

    # 全体の上下バランスを見て、描画開始Y位置を決める
    current_y = 250 

    # ------------------------------------------------
    # 描画1：ナンバーズ4
    # ------------------------------------------------
    title4 = "【ナンバーズ4 予想A】"
    
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
    
    # タイトルの中央位置を計算
    left, top, right, bottom = draw.textbbox((0, 0), title3, font=font_title)
    text_w = right - left
    title_x = (W - text_w) / 2
    
    draw.text((title_x + shadow_offset, current_y + shadow_offset), title3, font=font_title, fill=shadow_color)
    draw.text((title_x, current_y), title3, font=font_title, fill=n3_color)
    
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

# --- 1. 過去データの取得（★ロトと同様のカット方式に修正） ---
def fetch_single_history(base_url, length):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    data = []
    
    # ★過去1年分（12ヶ月分）のURLを自動生成
    today = datetime.date.today()
    target_urls = [base_url]
    
    for i in range(12):
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

# --- 3. 複合アルゴリズム予想生成（★ナンバーズ専用：ポジション分析型へ超強化） ---
def generate_advanced_predictions(history_data, length, win_key):
    draws = [d[win_key] for d in history_data]
    if not draws:
        return []

    # 【分析1】合計値の範囲を取得
    sums = [sum(int(n) for n in draw) for draw in draws]
    min_sum, max_sum = min(sums), max(sums)

    # 【分析2】全体の出現傾向
    overall_freq = {str(i): 0 for i in range(10)}
    for draw in draws:
        for n in draw: overall_freq[n] += 1

    # 【分析3】★桁(ポジション)ごとの出現傾向（ナンバーズにおいて最重要）
    pos_freq = [{str(i): 0 for i in range(10)} for _ in range(length)]
    pos_freq_10 = [{str(i): 0 for i in range(10)} for _ in range(length)] # 直近10回

    for idx, draw in enumerate(draws):
        for pos, n in enumerate(draw):
            pos_freq[pos][n] += 1
            if idx < 10:
                pos_freq_10[pos][n] += 1

    # 【分析4】各桁ごとに数字のスコア（確率）を計算
    pos_scores = []
    for pos in range(length):
        scores = {}
        for i in range(10):
            n = str(i)
            # 全体の傾向 + その桁での過去1年の傾向
            score = 1.0 + (overall_freq[n] * 0.1) + (pos_freq[pos][n] * 0.5)
            # ★直近10回のその桁でのトレンドを最も強く評価
            score += pos_freq_10[pos][n] * 2.5
            scores[n] = score
        pos_scores.append(scores)

    # --- 分析結果を元に候補を生成 ---
    predictions = []
    digits = [str(i) for i in range(10)]
    
    # 大量の候補セットを生成
    candidates = []
    for _ in range(3000):
        cand_chars = []
        # 各桁ごとに、その桁のスコア(重み)に基づいて数字を選ぶ
        for pos in range(length):
            weights = [pos_scores[pos][n] for n in digits]
            chosen = random.choices(digits, weights=weights, k=1)[0]
            cand_chars.append(chosen)
        candidates.append("".join(cand_chars))

    valid_candidates = []
    for cand in candidates:
        cand_nums = [int(x) for x in cand]
        
        # 条件適用①: 合計値分析
        if not (min_sum <= sum(cand_nums) <= max_sum): 
            continue

        # 条件適用②: トリプル(同じ数字が3つ)の除外フィルター
        # ナンバーズにおいて同じ数字が3つ以上出る確率は極めて低いため除外して精度を上げる
        counts = Counter(cand)
        if any(v >= 3 for v in counts.values()):
            continue

        # 候補全体の強さ(スコア)を計算
        cand_score = sum(pos_scores[pos][cand[pos]] for pos in range(length))
        valid_candidates.append((cand_score, cand))

    # スコア順にランキングし、上位5つの予想を選定
    valid_candidates.sort(key=lambda x: x[0], reverse=True)
    seen = set()
    seen_box = set() # ボックスでの重複も避ける（カバー範囲を広げるため）
    
    for score, cand in valid_candidates:
        box_cand = "".join(sorted(cand))
        if cand not in seen and box_cand not in seen_box:
            seen.add(cand)
            seen_box.add(box_cand)
            predictions.append(cand)
        if len(predictions) == 5:
            break

    # 安全処理
    while len(predictions) < 5:
        cand = "".join(str(random.randint(0,9)) for _ in range(length))
        if cand not in seen:
            seen.add(cand)
            predictions.append(cand)

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
        post_to_threads(msg)
        print(f"✅ 条件に合致したため配信を実行しました。")
        # ----------------------------------------------------
        # ★ ここからInstagramの自動投稿処理を追加！
        # ----------------------------------------------------
        # ※ "loto7_result.png" の部分は、実際にプログラムが生成・保存している
        # 画像のファイル名（パス）に書き換えてください。
        base_image = "base_image.png"     # ← ※ここはPNGのままでOKです（読み込む元画像なので）
        image_path = "numbers_result.jpg" # ← ★ここを .png から .jpg に変更！
        
        # ▼▼▼ 数字を職人に渡すために取り出す ▼▼▼
        n4_yosou_a = history_record[0]['n4_preds'][0]
        n3_yosou_a = history_record[0]['n3_preds'][0]
        
        caption = f"🎯最新のナンバーズ AI予想です！\n\n{msg}\n\n#ナンバーズ #宝くじ #AI予想 #ロトナンバーズ攻略局"
        
        # ① 新しい職人に、N4とN3の数字を別々に渡してデザイン作成を依頼する！
        is_created = create_result_image(n4_yosou_a, n3_yosou_a, base_image, image_path)
        
        # ② 画像が無事に作れたら、ImgBBにアップロードしてインスタに投稿する！
        if is_created:
            public_image_url = upload_image_to_server(image_path)
            if public_image_url:
                post_to_instagram(public_image_url, caption)
            else:
                print("⚠️ 画像のURL化に失敗しました。")
        # ----------------------------------------------------
    else:
        print(f"💤 配信条件外（的中なし、または配信時間外）のためスキップしました。")
    # --------------------------------------------------------

    return html

if __name__ == "__main__":
    final_html = build_html()
    with open('numbers.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
    print("✨ [自動取得・完全決着版] ナンバーズ3＆4 の自動更新とXへのポストが完了しました！")