import random
import requests
from bs4 import BeautifulSoup
import re
import json
import os
import datetime
from collections import Counter

HISTORY_FILE = 'history_loto7.json'

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

# --- 2. ホット＆コールド算出 ---
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

# --- 3. アルゴリズム予想生成 ---
def generate_algo_predictions(hot, cold):
    hot_nums = [item[0] for item in hot]
    cold_nums = [item[0] for item in cold]
    all_nums = [str(n).zfill(2) for n in range(1, 38)]
    
    predictions = []
    for _ in range(5):
        p_hot = random.sample(hot_nums, 2)
        p_cold = random.sample(cold_nums, 1)
        remaining_pool = list(set(all_nums) - set(p_hot) - set(p_cold))
        p_other = random.sample(remaining_pool, 4)
        
        pred = sorted(p_hot + p_cold + p_other)
        predictions.append(pred)
        
    return predictions

# --- 4. 履歴の保存と成績の自動照合 ---
def manage_history(latest_data, new_predictions):
    history_record = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_record = json.load(f)
        except Exception:
            history_record = []
            
    latest_kai = latest_data['kai']
    win_main = set(latest_data['main'])
    win_bonus = set(latest_data['bonus'])
    
    for record in history_record:
        if record.get('status') == 'waiting' and record.get('target_kai') == latest_kai:
            best_match = 0
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
                
                if match_main > best_match:
                    best_match = match_main
                    best_result = result
                    
            record['status'] = 'finished'
            record['actual_main'] = ", ".join(latest_data['main'])
            record['actual_bonus'] = "(B: " + ", ".join(latest_data['bonus']) + ")"
            record['best_result'] = best_result
            
    next_kai_num = int(re.search(r'\d+', latest_kai).group()) + 1
    next_kai = f"第{next_kai_num}回"
    
    if not any(r.get('target_kai') == next_kai for r in history_record):
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
        if record.get('target_kai') not in seen_kais:
            cleaned_record.append(record)
            seen_kais.add(record.get('target_kai'))
            
    history_record = cleaned_record[:10]
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history_record, f, ensure_ascii=False, indent=2)
        
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
                return "💰 キャリーオーバー発生中！(最高10億円)"
            break
    return ""

# --- 5. HTML構築 ---
def build_html():
    print("🔄 ロト7 データ取得＆アルゴリズム解析を開始...")
    history_data = fetch_history_data()
    latest_data = history_data[0]
    hot, cold = analyze_trends(history_data)
    predictions = generate_algo_predictions(hot, cold)
    history_record = manage_history(latest_data, predictions)
    
    print(f"📡 データ取得成功: 最新回 {latest_data['kai']} ({latest_data['date']})")
    
    # キャリーオーバー情報の取得とHTMLパーツ作成
    carryover_text = check_loto7_carryover(history_record)
    carryover_html = f'<div class="carryover-badge">{carryover_text}</div>' if carryover_text else ''
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ロト7 当選予想・データ分析ポータル</title>
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
            <img src="Lotologo.png" alt="宝くじ当選予想・データ分析ポータル" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">ロト7当選予想・速報</div>
        </a>
    </header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html" class="active">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
    </nav>
    <div class="container">
        <div style="text-align: center; margin-bottom: 40px;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4FK6WI+3A98+64C3L" rel="nofollow">
            <img border="0" width="300" height="250" alt="" src="https://www28.a8.net/svt/bgt?aid=260331146268&wid=001&eno=01&mid=s00000015326001028000&mc=1"></a>
            <img border="0" width="1" height="1" src="https://www14.a8.net/0.gif?a8mat=4AZSSQ+4FK6WI+3A98+64C3L" alt="">
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
    return html

final_html = build_html()
with open('loto7.html', 'w', encoding='utf-8') as f:
    f.write(final_html)
print("✨ [完全無敵版] ロト7の全データ取得が完了しました！")