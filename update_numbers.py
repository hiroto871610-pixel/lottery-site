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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HISTORY_FILE = 'history_numbers.json'

# =========================================================
# 𝕏 (旧Twitter) API設定
# =========================================================
X_API_KEY = "kjirp4z5V0sQPLdpbakvHUKo7"
X_API_SECRET = "zNEepgKHYsW5OdvHzYLwNwwl9bEa4t7tyGb7QBCkvyPw76jtVF"
X_ACCESS_TOKEN = "2040049940643086336-kBXZWHARtoxpzJaSVR3ZcrAqeeQOyT"
X_ACCESS_SECRET = "r4cMeool2cvMBgUCWvQccL7qJykGQS8lsss6fhG77FquD"

def post_to_x(message):
    """X(Twitter)へ自動投稿する機能"""
    if X_API_KEY.startswith("ここに"):
        print("⚠️ XのAPIキーが設定されていないため、自動ポストをスキップしました。")
        return

    try:
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_SECRET
        )
        client.create_tweet(text=message)
        print("✅ X(Twitter)への自動ポストが成功しました！")
    except Exception as e:
        print(f"❌ Xポストエラー: {e}")
# =========================================================

# --- 1. 過去データの取得（目印に頼らない最強抽出ロジック） ---
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
            
            # 【最強抽出】「第〇〇回」〜「日付」〜「当せん番号」の塊を強制的にぶっこ抜く
            pattern = r'第\s*(\d+)\s*回[^第]*?(\d{4}[/年]\d{1,2}[/月]\d{1,2})[^第]*?当せん番号\D*(\d{' + str(length) + r'})'
            matches = re.finditer(pattern, text)
            
            for m in matches:
                kai = f"第{m.group(1)}回"
                date = m.group(2).replace('年', '/').replace('月', '/')
                win_num = m.group(3)
                
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

# --- 2. ホット＆コールド算出 (0〜9の数字頻度) ---
def analyze_digit_trends(history_data):
    all_digits = []
    for data in history_data:
        all_digits.extend(list(data['n4_win']) + list(data['n3_win']))
    
    counts = Counter(all_digits)
    for i in range(10):
        if str(i) not in counts: counts[str(i)] = 0
            
    sorted_counts = counts.most_common()
    hot = sorted_counts[:3]  # 上位3つ
    cold = list(reversed(sorted_counts))[:3] # 下位3つ
    return hot, cold

# --- 3. アルゴリズム予想生成 ---
def generate_algo_predictions(hot, cold, length):
    hot_digits = [item[0] for item in hot]
    cold_digits = [item[0] for item in cold]
    all_digits = [str(n) for n in range(10)]
    
    predictions = []
    for _ in range(3): # 予想A〜C
        p = [random.choice(hot_digits), random.choice(cold_digits)]
        p += random.choices(all_digits, k=(length - 2))
        random.shuffle(p)
        predictions.append("".join(p))
    return predictions

# --- 4. 履歴の保存と成績の自動照合 ---
def manage_history(latest_data, n4_preds, n3_preds):
    history_record = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_record = json.load(f)
        except Exception:
            print("⚠️ 履歴ファイルが破損しているため新しく作成します。")
            history_record = []
            
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
    
    history_record = history_record[:10]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history_record, f, ensure_ascii=False, indent=2)
        
    return history_record

# --- 5. HTML構築 ---
def build_html():
    history_data = fetch_both_history()
    latest_data = history_data[0]
    hot, cold = analyze_digit_trends(history_data)
    
    n4_preds = generate_algo_predictions(hot, cold, 4)
    n3_preds = generate_algo_predictions(hot, cold, 3)
    history_record = manage_history(latest_data, n4_preds, n3_preds)
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>ナンバーズ3＆4 当選予想・データ分析</title>
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
            <img src="Lotologo.png" alt="ロト＆ナンバーズ攻略局🎯完全無料のAI予想" style="max-width: 100%; height: auto; max-height: 180px;">
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
    <div class="container">
    
        <div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4RGVRU+4GLE+5ZU29" rel="nofollow">
<img border="0" width="320" height="auto" alt="" src="https://www29.a8.net/svt/bgt?aid=260331146288&wid=002&eno=01&mid=s00000020813001007000&mc=1"></a>
<img border="0" width="1" height="1" src="https://www19.a8.net/0.gif?a8mat=4AZSSQ+4RGVRU+4GLE+5ZU29" alt="">
    </div>

        <div class="section-card">
            <h2 class="section-header">🎯 次回 ({history_record[0]['target_kai']}) ナンバーズ4 予想</h2>
            <p>直近の傾向からHOT数字とCOLD数字を掛け合わせたアルゴリズム予想です。</p>
            <div class="prediction-box">
"""
    labels = ['予想A', '予想B', '予想C']
    tags4 = ['<span class="recommend-tag tag-straight">ストレート推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>']
    for i, pred in enumerate(history_record[0]['n4_preds']):
        balls = "".join([f'<span class="ball">{n}</span>' for n in pred])
        html += f'                <div class="numbers-row"><div class="row-label">{labels[i]}</div><div class="ball-container">{balls}</div>{tags4[i]}</div>\n'
    
    html += f"""            </div>
            <h2 class="section-header" style="margin-top: 40px;">🎯 次回 ({history_record[0]['target_kai']}) ナンバーズ3 予想</h2>
            <div class="prediction-box">
"""
    tags3 = ['<span class="recommend-tag tag-straight">ストレート推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>', '<span class="recommend-tag tag-box">ミニ推奨</span>']
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
            <h2 class="section-header">📊 直近の出現傾向 (0〜9の数字)</h2>
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

    # --- ⭐️ 自動ポスト用のメッセージを作成して実行 ⭐️ ---
    import datetime
    
    # 今日の曜日を取得 (0:月, 1:火, 2:水, 3:木, 4:金, 5:土, 6:日)
    today_weekday = datetime.datetime.now().weekday()
    
    next_kai = history_record[0]['target_kai']
    # サイトのURLを設定してください
    site_url = "https://loto-yosou-ai.com/numbers.html" 
    
    # ナンバーズは【月曜〜金曜】が毎日抽選日です
    
    # 【月〜金 (0〜4)】 抽選結果速報と次回予想
    if 0 <= today_weekday <= 4:
        finished_record = history_record[1] if len(history_record) > 1 else history_record[0]
        finished_kai = finished_record['target_kai']
        res_n4 = finished_record.get('result_n4', '----')
        res_n3 = finished_record.get('result_n3', '----')
        
        tweet_msg = f"【#ナンバーズ 抽選結果速報🔔】\n本日 {finished_kai} の結果発表！\n当サイトのAI予想成績\nN4: {res_n4}\nN3: {res_n3}\n\n実際の当選番号と、次回({next_kai})の最新予想はこちら👇\n{site_url}\n#宝くじ結果"

    # 【土・日 (5, 6)】 次回予想の通知のみ
    else:
        tweet_msg = f"【#ナンバーズ 予想更新🎯】\n次回({next_kai})のAI予想を公開中です！\n\n直近の出現傾向データから導き出した最新HOT・COLD数字と推奨予想はこちら👇\n{site_url}\n#宝くじ予想"
    
    # 決定したメッセージをポストする
    post_to_x(tweet_msg)
    # --------------------------------------------------------

    return html

if __name__ == "__main__":
    final_html = build_html()
    with open('numbers.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
    print("✨ [自動取得・完全決着版] ナンバーズ3＆4 の自動更新とXへのポストが完了しました！")