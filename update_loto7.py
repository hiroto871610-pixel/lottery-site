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
# ▲▲▲ ここまで ▲▲▲

# =========================================================
# JSONBin API設定 (Loto 7専用)
# =========================================================
JSONBIN_BIN_ID = os.environ.get("JSONBIN_BIN_ID_LOTO7") # LOTO7用に変更
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

# ▼▼▼ 追加：.envファイルを読み込むためのライブラリ ▼▼▼
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()
# ▲▲▲ ここまで追加 ▲▲▲

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HISTORY_FILE = 'history_loto7.json'

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

def post_to_threads(message):
    """Threadsへ自動投稿する機能（2ステップ方式）"""
    if not all([THREADS_USER_ID, THREADS_ACCESS_TOKEN]):
        print("⚠️ ThreadsのAPI情報が.envから取得できないため、自動ポストをスキップしました。")
        return

    try:
        # ステップ1：メディアコンテナ（下書き）を作成する
        create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
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
        publish_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
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

# --- 1. 過去データの取得（過去1年分・約50回） ---
def fetch_history_data():
    base_url = "https://takarakuji.rakuten.co.jp/backnumber/loto7/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    history_data = []
    
    # 過去12ヶ月分のURLを自動生成（最新ページ ＋ 過去12ヶ月分）
    today = datetime.date.today()
    target_urls = [f"{base_url}lastresults/"]
    
    for i in range(12):
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
                
                # ★超重要：日付の直後から残りのテキストを切り出す（これで日付の数字を誤飲しない）
                num_chunk = chunk[date_m.end():]
                
                # 残った文章から「すべての数字」を抽出
                all_digits = re.findall(r'\d+', num_chunk)
                
                # ロト7の範囲（1〜37）の数字だけを残す
                valid_nums = [n.zfill(2) for n in all_digits if 1 <= int(n) <= 37]
                
                # 上から順番に、本数字7個とボーナス数字2個が揃っていれば大成功
                if len(valid_nums) >= 9:
                    main_nums = valid_nums[:7]
                    bonus_nums = valid_nums[7:9]
                    
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

# --- 2. ホット＆コールド算出（HTML表示用はそのまま維持） ---
def analyze_trends(history_data):
    all_nums = []
    for data in history_data:
        all_nums.extend(data['main'])
    
    counts = Counter(all_nums)
    for i in range(1, 38):
        num_str = str(i).zfill(2)
        if num_str not in counts: counts[num_str] = 0
            
    sorted_counts = counts.most_common()
    hot = sorted_counts[:5]
    cold = list(reversed(sorted_counts))[:5]
    
    return hot, cold

# --- 3. 複合アルゴリズム予想生成（★今回のご指示で全面的に刷新・強化した部分） ---
def generate_advanced_predictions(history_data):
    main_draws = [[int(n) for n in d['main']] for d in history_data]
    if not main_draws:
        return []

    # 【分析1】合計値分析
    sums = [sum(draw) for draw in main_draws]
    min_sum, max_sum = min(sums), max(sums)

    # 【分析2】奇数偶数バランス分析
    odd_counts = [sum(1 for n in draw if n % 2 != 0) for draw in main_draws]
    avg_odd = round(sum(odd_counts) / len(odd_counts)) if odd_counts else 4
    target_odds = [avg_odd - 1, avg_odd, avg_odd + 1] # 平均値±1の範囲を許容

    # 【分析3】連続数字分析 (12, 13などの連続)
    seq_count = sum(1 for draw in main_draws if any(draw[i]+1 == draw[i+1] for i in range(len(draw)-1)))
    seq_prob = seq_count / len(main_draws)

    # 【分析4】連続出現数字分析 (前回と同じ数字が引っ張られる確率)
    repeat_count = sum(len(set(main_draws[i]) & set(main_draws[i+1])) for i in range(len(main_draws)-1))
    total_nums = 7 * (len(main_draws) - 1) if len(main_draws) > 1 else 1
    repeat_prob = repeat_count / total_nums

    # 【分析5＆6】過去1年の傾向 (HOT/COLD) ＆ 最新最古数字分析
    freq = {i: 0 for i in range(1, 38)}
    freq_10 = {i: 0 for i in range(1, 38)}
    last_seen = {i: 999 for i in range(1, 38)}

    for idx, draw in enumerate(main_draws):
        for n in draw:
            freq[n] += 1
            if idx < 10:
                freq_10[n] += 1
            if last_seen[n] == 999:
                last_seen[n] = idx

    # 【分析7】各数字の順位付け（確率スコアリング）
    scores = {}
    for n in range(1, 38):
        score = 1.0
        # 過去一年間の傾向 (ベースポイント)
        score += freq[n] * 0.5 
        # ★直近の傾向(過去10回)に重点をおく (高ウェイト)
        score += freq_10[n] * 2.5 

        # 最新・最古および連続出現の反映
        if last_seen[n] == 0:
            # 前回出た数字は、連続出現確率(repeat_prob)を元にスコア加算
            score += (repeat_prob * 10)
        elif last_seen[n] > 15:
            # 最も出ていない古い数字は「そろそろ出る」として優先度(確率)を上げる
            score += 3.0
        else:
            score += 1.0

        scores[n] = max(0.1, score)

    # --- 分析結果の掛け合わせによる選定・抽出 ---
    predictions = []
    numbers = list(range(1, 38))
    weights = [scores[n] for n in numbers]

    # 大量の候補セットを生成し、すべての分析条件をクリアしたものだけを抽出
    candidates = []
    for _ in range(2000):
        # 順位付け(スコア)に基づいた重み付きランダム抽出
        cand = []
        pool_nums = list(numbers)
        pool_weights = list(weights)
        for _ in range(7):
            choice = random.choices(pool_nums, weights=pool_weights)[0]
            cand.append(choice)
            idx = pool_nums.index(choice)
            pool_nums.pop(idx)
            pool_weights.pop(idx)
        cand.sort()
        candidates.append(cand)

    valid_candidates = []
    for cand in candidates:
        # 条件適用①: 合計値分析 (最大値〜最小値の間に収める)
        if not (min_sum <= sum(cand) <= max_sum): 
            continue

        # 条件適用②: 奇数偶数バランス
        odds = sum(1 for n in cand if n % 2 != 0)
        if odds not in target_odds: 
            continue

        # 条件適用③: 連続数字分析の確率を掛け合わせ (スコア補正)
        has_seq = any(cand[i]+1 == cand[i+1] for i in range(6))
        cand_score = sum(scores[n] for n in cand)
        
        if (has_seq and seq_prob > 0.5) or (not has_seq and seq_prob <= 0.5):
            cand_score *= 1.2 # 確率の高い傾向に沿っている組み合わせのスコアを強化

        valid_candidates.append((cand_score, cand))

    # スコア順にランキングし、上位5つの予想を選定
    valid_candidates.sort(key=lambda x: x[0], reverse=True)
    seen = set()
    for score, cand in valid_candidates:
        t_cand = tuple(cand)
        if t_cand not in seen:
            seen.add(t_cand)
            predictions.append([str(n).zfill(2) for n in cand])
        if len(predictions) == 5:
            break

    # 万が一、条件が厳しすぎて5個揃わなかった場合の安全処理
    while len(predictions) < 5:
        cand = random.sample(numbers, 7)
        cand.sort()
        t_cand = tuple(cand)
        if t_cand not in seen:
            seen.add(t_cand)
            predictions.append([str(n).zfill(2) for n in cand])

    return predictions

# --- 4. 履歴の保存と成績の自動照合 ---
def manage_history(latest_data, new_predictions):
    # ▼▼▼ 変更①：ファイルの読み込みを削除し、JSONBinから取得 ▼▼▼
    print("☁️ JSONBin(Loto7)から履歴を取得中...")
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
            
            # ★修正：「第671回」と「第0671回」の違いを無視し、数字ベースで判定して更新
            if record_kai_num == latest_kai_num:
                best_match = -1  # ★0個一致でも必ず更新されるように、初期値をマイナス1にする
                best_has_bonus = False  # ★追加：ボーナスの一致状態を記憶
                best_result = "ハズレ"
                for p in record['predictions']:
                    p_set = set(p)
                    match_main = len(p_set & win_main)
                    has_bonus = len(p_set & win_bonus) > 0
                    
                    if match_main == 7: result = "1等🎯"
                    elif match_main == 6 and has_bonus: result = "2等🎯"
                    elif match_main == 6: result = "3等"
                    elif match_main == 5: result = "4等"
                    elif match_main == 4: result = "5等"
                    elif match_main == 3 and has_bonus: result = "6等"
                    else: result = f"ハズレ({match_main}個一致)"
                    
                    if match_main > best_match or (match_main == best_match and has_bonus and not best_has_bonus):
                        best_match = match_main
                        best_has_bonus = has_bonus
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
    
    # ▼▼▼ 変更②：ファイルへの書き込みを削除し、JSONBinへ保存 ▼▼▼
    print("☁️ JSONBin(Loto7)へ最新データを保存中...")
    save_history_to_jsonbin(history_record)
    # ▲▲▲ ここまで ▲▲▲
        
    return history_record

# --- 追加：キャリーオーバー判定（内部データ利用） ---
def check_loto7_carryover(history_record):
    """
    history_loto7.json の最新の「確定」データから、
    1等が出ているかどうかでキャリーオーバーの有無を判定します。
    """
    for record in history_record:
        if record.get('status') == 'finished':
            best_res = record.get('best_result', '')
            if '1等' not in best_res and best_res != '----':
                return "💰 キャリーオーバー発生中！(最高12億円)"
            break
    return ""

def get_next_loto7_date():
    """現在時刻から次回のロト7抽選日(金曜)を自動計算する"""
    now = datetime.datetime.now()
    # 18:30以降に実行された場合は、当日の購入は終了したとみなして翌日基準で計算
    if now.hour >= 19 or (now.hour == 18 and now.minute >= 30):
        base_date = now.date() + datetime.timedelta(days=1)
    else:
        base_date = now.date()

    # ロト7 (金: 4)
    l7_days = 0
    while (base_date + datetime.timedelta(days=l7_days)).weekday() != 4:
        l7_days += 1
    next_date = base_date + datetime.timedelta(days=l7_days)

    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return f"{next_date.month}月{next_date.day}日({weekdays[next_date.weekday()]})"

# --- 5. HTML構築 ---
def build_html():
    print("🔄 ロト7 データ取得＆アルゴリズム解析を開始...")
    history_data = fetch_history_data()
    latest_data = history_data[0]
    hot, cold = analyze_trends(history_data)
    
    # ★新設した高度な複合分析ロジックを使用
    predictions = generate_advanced_predictions(history_data)
    
    history_record = manage_history(latest_data, predictions)
    
    print(f"📡 データ取得成功: 最新回 {latest_data['kai']} ({latest_data['date']})")
    
    # キャリーオーバー情報の取得とHTMLパーツ作成
    carryover_text = check_loto7_carryover(history_record)
    carryover_html = f'<div class="carryover-badge">{carryover_text}</div>' if carryover_text else ''

    next_date_str = get_next_loto7_date()
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>【{history_record[0]['target_kai']}】ロト7当選予想・データ分析ポータル | 最新AI予想</title>
    <meta name="description" content="{history_record[0]['target_kai']}のロト7当選予想。過去1年分のデータから導き出したHOT数字・COLD数字と完全無料のAIアルゴリズム予想を公開中！最高12億円のキャリーオーバー情報も。">
    <meta property="og:title" content="【{history_record[0]['target_kai']}】ロト7最新AI予想">
    <meta property="og:description" content="過去1年分のデータから導き出したHOT数字・COLD数字と完全無料のAIアルゴリズム予想を公開中！">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://loto-yosou-ai.com/loto7.html">
    <meta property="og:image" content="https://loto-yosou-ai.com/Lotologo001.png">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="canonical" href="https://loto-yosou-ai.com/loto7.html">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; padding: 10px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #1e3a8a; padding: 15px 20px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; }}
        nav a.active {{ border-bottom: 3px solid #d97706; color: #d97706; }}
        nav a:hover {{ background-color: #f0f4f8; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #d97706; border-bottom: 2px solid #fef3c7; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; }}
        .prediction-box {{ background-color: #fffbeb; border: 2px solid #fcd34d; border-radius: 12px; padding: 25px; margin-bottom: 20px;}}
        .numbers-row {{ background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; align-items: center; }}
        .row-label {{ font-size: 18px; font-weight: bold; color: #1e3a8a; background-color: #e0e7ff; padding: 5px 15px; border-radius: 4px; margin-right: 20px; min-width: 60px; text-align: center; }}
        .ball-container {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .ball {{ display: inline-flex; justify-content: center; align-items: center; width: 42px; height: 42px; background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border-radius: 50%; font-size: 18px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.3); }}
        
        /* キャリーオーバーバッジのスタイル追加 */
        .carryover-badge {{ background: linear-gradient(135deg, #ef4444, #b91c1c); color: white; font-size: 14px; font-weight: bold; padding: 10px 15px; border-radius: 8px; margin: 15px 0; display: inline-block; animation: pulse 2s infinite; box-shadow: 0 4px 10px rgba(239,68,68,0.4); text-align: center; width: 100%; box-sizing: border-box; }}
        @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.02); }} 100% {{ transform: scale(1); }} }}

        @media (max-width: 600px) {{ .numbers-row {{ flex-direction: column; align-items: flex-start; padding: 15px;}} .row-label {{ margin-bottom: 10px; }} .ball {{ width: 36px; height: 36px; font-size: 16px;}} .carryover-badge {{ font-size: 13px; padding: 8px; }} }}
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
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1431683156739681" crossorigin="anonymous"></script>
</head>
<body>
    <header>
        <a href="index.html" style="text-decoration: none;">
            <img src="Lotologo001.png" alt="ロト＆ナンバーズ攻略局🎯完全無料のAI予想" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">ロト7当選予想・速報</div>
        </a>
    </header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html" class="active">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="column.html">攻略ガイド🔰</a>
    </nav>

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

    <div class="section-card" style="background: linear-gradient(to right, #ffffff, #fffbeb); border-left: 5px solid #d97706; padding: 20px;">
            <div style="font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 10px;">⏰ 次回抽選日と購入期限</div>
            <div style="font-size: 15px; color: #475569;">
                <span style="display:inline-block; margin-right: 20px;">次回抽選: <strong style="color: #d97706; font-size: 18px;">{next_date_str}</strong></span>
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
            <h2 class="section-header">🎯 次回 ({history_record[0]['target_kai']}) ロト7の予想</h2>
            <p>直近約1年間の傾向からHOT数字とCOLD数字を掛け合わせた独自のアルゴリズム予想です。</p>
            {carryover_html}
            <div class="prediction-box">
"""
    labels = ['予想A', '予想B', '予想C', '予想D', '予想E']
    for i, pred in enumerate(history_record[0]['predictions']):
        balls = "".join([f'<span class="ball">{n}</span>' for n in pred])
        html += f'                <div class="numbers-row"><div class="row-label">{labels[i]}</div><div class="ball-container">{balls}</div></div>\n'
    
    html += f"""            </div>
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
                        <td style="font-weight:bold; color:#1e3a8a;">{record.get('target_kai', '----')}</td>
                        <td><span style="font-size:16px; font-weight:bold; letter-spacing:1px;">{record.get('actual_main', '----')}</span><br><span style="color:#888; font-size:12px;">{record.get('actual_bonus', '')}</span></td>
                        <td><span class="{res_class}">{record.get('best_result', '----')}</span></td>
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
            <h2 class="section-header">📅 過去1年間の当選番号 (実際のデータ)</h2>
            <p style="font-size: 14px; color: #64748b;">※楽天宝くじのアーカイブデータより抽出（過去1年分）</p>
            <div class="scroll-table-container">
                <table>
                    <thead>
                        <tr><th>回号 (抽選日)</th><th>本数字</th><th>ボーナス数字</th></tr>
                    </thead>
                    <tbody>
"""
    for row in history_data[:52]:
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
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p>※当サイトの予想・データは当選を保証するものではありません。宝くじの購入は自己責任でお願いいたします。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 ロト＆ナンバーズ攻略局🎯完全無料のAI予想 All Rights Reserved.</p>
    </footer>
</body>
</html>"""

    # --- ⭐️ 自動ポスト・LINE配信用のメッセージを作成して実行 ⭐️ ---
    import datetime
    
    now = datetime.datetime.now()
    today_weekday = now.weekday() # 0:月, 1:火, 2:水, 3:木, 4:金, 5:土, 6:日
    current_hour = now.hour       # 現在の「時間」を取得
    
    next_kai = history_record[0]['target_kai']
    site_url = "https://loto-yosou-ai.com/loto7.html" 
    
    msg = ""
    send_flag = False  # 初期値は「配信しない」

    # ■【金曜日(4)】：抽選日当日の配信ロジック
    if today_weekday == 4:
        send_flag = True
        # ①【朝〜夕方 (19時前)】：抽選日予告
        if current_hour < 19:
            msg = f"【本日は #ロト7 抽選日🎯】\nついに本日 {next_kai} の抽選日です！\n"
            if carryover_text:
                msg += f"{carryover_text}\n"
            msg += f"\n最高12億円のチャンス！AIが導き出した最新予想を無料で公開中。購入前にチェック👇\n{site_url}"

        # ②【夜 (19時以降)】：結果速報と次回予想
        else:
            finished_record = history_record[1] if len(history_record) > 1 else history_record[0]
            finished_kai = finished_record['target_kai']
            best_res = finished_record.get('best_result', 'ハズレ')
            
            is_high_prize = any(prize in best_res for prize in ["1等", "2等", "3等"])
            
            if is_high_prize:
                msg = f"🚨【号外：超高額当選発生】🚨\n\nなんと！本日発表の {finished_kai} で\n当サイトのAI予想が…\n\n🎉👑【 {best_res} 】👑🎉\n\nを超高額的中させました！！！\n"
                msg += f"最高12億円のロト7で歴史的快挙✨\n興奮の的中実績と、次回({next_kai})の最新予想はこちら👇\n{site_url}"

                # 実績バッジ用のメモ保存
                import json
                achievement_data = {
                    "lottery_name": "ロト7",
                    "kai": finished_kai,
                    "prize": best_res
                }
                with open("latest_achievement.json", "w", encoding="utf-8") as f:
                    json.dump(achievement_data, f, ensure_ascii=False)
            
            elif any(prize in best_res for prize in ["4等", "5等", "6等"]):
                msg = f"【#ロト7 的中速報🎯】\n本日 {finished_kai} の結果発表！\n当サイトのAI予想が見事【{best_res}】を的中させました！\n"
                if carryover_text:
                    msg += f"\n{carryover_text}\n"
                msg += f"\n着実に利益を積み重ねています✨\n次回({next_kai})の最新予想はこちら👇\n{site_url}"
                
            else:
                msg = f"【#ロト7 抽選結果速報🔔】\n本日 {finished_kai} の結果発表！\n"
                if carryover_text:
                    msg += f"\n{carryover_text}\n"
                msg += f"\nAIはさらにデータを学習し進化します！次回({next_kai})の最新予想はこちら👇\n{site_url}"

    # ■【日曜日(6)】：週の終わりの「予想更新通知」
    elif today_weekday == 6:
        # 夜（19時以降）に実行された場合のみ配信
        if current_hour >= 19:
            send_flag = True
            msg = f"【#ロト7 予想更新🎯】\n次回({next_kai})のAI予想を公開中！\n"
            if carryover_text:
                msg += f"現在、{carryover_text}\n"
            msg += f"\n過去データから厳選したAI予想はこちらから👇\n{site_url}"

    # ■ それ以外の曜日（月・火・水・木・土）：配信しない
    else:
        send_flag = False

    # 最後に送信処理をまとめる
    if send_flag and msg:
        post_to_x(msg)
        post_to_line(msg)
        print(f"✅ ロト7の配信条件に合致したため実行しました。")
    else:
        print(f"💤 ロト7：配信対象外（または時間外）のため、送信をスキップしました。")
    
    return html

# 最終実行部分（ここは関数の外側に戻します）
if __name__ == "__main__":
    final_html = build_html()
    with open('loto7.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
    print("✨ ロト7の全データ取得と自動ポストが完了しました！")