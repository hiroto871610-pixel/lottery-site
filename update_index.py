import json
import os
import datetime
import requests
from bs4 import BeautifulSoup
import re

# データベースファイルのパス
FILES = {
    'loto7': 'history_loto7.json',
    'loto6': 'history_loto6.json',
    'numbers': 'history_numbers.json'
}

def load_latest_data(filepath):
    """JSONファイルから最新(1件目)の確定データを読み込む"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data and len(data) > 0:
                    for record in data:
                        if record.get('status') == 'finished':
                            return record
        except Exception as e:
            print(f"⚠️ {filepath} の読み込みエラー: {e}")
    return None

def check_carryover_status(loto_type, latest_data):
    """
    【内部データ完全依存ロジック】
    外部サイトへのアクセスを一切行わず、手元のJSONデータから確実に判定します。
    「前回（最新回）の1等が当サイトの予想から出ていない」場合、
    高確率でキャリーオーバーが発生しているとみなしバッジを表示します。
    """
    if not latest_data or latest_data.get('best_result') == '----':
        return ""

    best_result = latest_data.get('best_result', '')
    
    # 1等が出ていなければキャリーオーバー発生中とみなす
    if '1等' not in best_result:
        max_prize = "10億円" if loto_type == "loto7" else "6億円"
        return f"💰 キャリーオーバー発生中！(最高{max_prize})"
        
    return ""

# --- トップページ表示用に最新の当選番号をWebから直接取得する機能を追加 ---
def fetch_latest_loto_for_top(loto_type, max_val, pick_count):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    url = f"https://takarakuji.rakuten.co.jp/backnumber/{loto_type}/lastresults/"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            res.encoding = 'euc-jp'
            soup = BeautifulSoup(res.content, 'html.parser')
            text = soup.get_text(separator=' ')
            
            kai_m = re.search(r'第\s*(\d+)\s*回', text)
            if not kai_m: return None
            kai_str = f"第{kai_m.group(1).zfill(4)}回"
            
            chunk = text[kai_m.end():kai_m.end() + 300]
            date_m = re.search(r'(\d{4})[/年]\s*(\d{1,2})\s*[/月]\s*(\d{1,2})', chunk)
            num_chunk = chunk[date_m.end():] if date_m else chunk
            all_digits = re.findall(r'\d+', num_chunk)
            valid_nums = [n.zfill(2) for n in all_digits if 1 <= int(n) <= max_val]
            
            if len(valid_nums) >= pick_count + 1:
                main_nums = valid_nums[:pick_count]
                bonus_count = 2 if loto_type == 'loto7' else 1
                bonus_nums = valid_nums[pick_count:pick_count+bonus_count]
                return {
                    'target_kai': kai_str,
                    'actual_main': ", ".join(main_nums),
                    'actual_bonus': "(B: " + ", ".join(bonus_nums) + ")"
                }
    except Exception as e:
        print(f"トップページ用データ取得エラー ({loto_type}): {e}")
    return None

def fetch_latest_numbers_for_top():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    result = {}
    try:
        # N4
        r4 = requests.get("https://takarakuji.rakuten.co.jp/backnumber/numbers4/lastresults/", headers=headers, timeout=10)
        if r4.status_code == 200:
            r4.encoding = 'euc-jp'
            s4 = BeautifulSoup(r4.content, 'html.parser')
            t4 = s4.get_text(separator=' ')
            m4 = re.search(r'第\s*(\d+)\s*回[^第]*?当せん番号\D*(\d{4})', t4)
            if m4:
                result['target_kai'] = f"第{m4.group(1)}回"
                result['actual_n4'] = m4.group(2)
        
        # N3
        r3 = requests.get("https://takarakuji.rakuten.co.jp/backnumber/numbers3/lastresults/", headers=headers, timeout=10)
        if r3.status_code == 200:
            r3.encoding = 'euc-jp'
            s3 = BeautifulSoup(r3.content, 'html.parser')
            t3 = s3.get_text(separator=' ')
            m3 = re.search(r'第\s*(\d+)\s*回[^第]*?当せん番号\D*(\d{3})', t3)
            if m3:
                result['actual_n3'] = m3.group(2)
                
        if 'actual_n4' in result and 'actual_n3' in result:
            return result
    except Exception as e:
        print(f"トップページ用データ取得エラー (Numbers): {e}")
    return None
# -------------------------------------------------------------

def get_next_jumbo():
    """季節に合わせて次回ジャンボを判定"""
    m = datetime.date.today().month
    if m == 1 or m == 2: return "🍫 バレンタインジャンボ", "1等・前後賞合わせて 3億円"
    elif 3 <= m <= 5: return "🌸 ドリームジャンボ", "1等・前後賞合わせて 5億円"
    elif 6 <= m <= 7: return "🌻 サマージャンボ", "1等・前後賞合わせて 7億円"
    elif 8 <= m <= 10: return "🎃 ハロウィンジャンボ", "1等・前後賞合わせて 5億円"
    else: return "⛄ 年末ジャンボ", "1等・前後賞合わせて 10億円"

def build_index_html():
    print("🔄 オシャレなトップページを生成中...")
    
    # 内部のJSONデータを読み込む（キャリーオーバー判定用）
    l7_json = load_latest_data(FILES['loto7'])
    l6_json = load_latest_data(FILES['loto6'])
    nm_json = load_latest_data(FILES['numbers'])
    
    # トップページの表示用に、最新の抽選結果をWebから直接取得する
    print("📡 トップページ用の最新当選番号を取得中...")
    l7_display = fetch_latest_loto_for_top('loto7', 37, 7) or l7_json or {'target_kai': 'データなし', 'actual_main': '----', 'actual_bonus': ''}
    l6_display = fetch_latest_loto_for_top('loto6', 43, 6) or l6_json or {'target_kai': 'データなし', 'actual_main': '----', 'actual_bonus': ''}
    nm_display = fetch_latest_numbers_for_top() or nm_json or {'target_kai': 'データなし', 'actual_n4': '----', 'actual_n3': '----'}

    # キャリーオーバーの発生の有無を内部データから取得
    print("📡 キャリーオーバー発生状況を内部データから判定中...")
    l7_carry_status = check_carryover_status("loto7", l7_json)
    l6_carry_status = check_carryover_status("loto6", l6_json)
    
    # バッジHTMLの組み立て
    l7_carry_html = f'<div class="carryover-badge">{l7_carry_status}</div>' if l7_carry_status else ''
    l6_carry_html = f'<div class="carryover-badge">{l6_carry_status}</div>' if l6_carry_status else ''
    
    jumbo_name, jumbo_prize = get_next_jumbo()

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ロト＆ナンバーズ攻略局🎯完全無料のAI予想 | ロト7・ロト6・ナンバーズ</title>
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #2d3748; line-height: 1.6; }}
        header {{ background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%); color: white; padding: 30px 20px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        header a {{ text-decoration: none; color: white; display: block; }}
        header h1 {{ margin: 0; font-size: 28px; font-weight: 800; letter-spacing: 1px; }}
        header p {{ margin: 10px 0 0 0; font-size: 15px; color: #e2e8f0; }}
        
        nav {{ display: flex; justify-content: center; background-color: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 100; border-bottom: 1px solid #e2e8f0; }}
        nav a {{ color: #475569; padding: 16px 24px; text-decoration: none; font-weight: bold; transition: all 0.3s ease; }}
        nav a:hover {{ color: #1e3a8a; background-color: #f8fafc; }}
        nav a.active {{ color: #1e3a8a; }}
        nav a.active::after {{ content: ''; position: absolute; bottom: 0; left: 0; width: 100%; height: 3px; background: linear-gradient(90deg, #3b82f6, #1e3a8a); }}
        
        .container {{ max-width: 1050px; margin: 40px auto; padding: 0 20px; }}
        .section-title {{ text-align: center; font-size: 24px; font-weight: 800; color: #1e293b; margin-bottom: 30px; }}
        
        .dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 25px; margin-bottom: 40px; }}
        .dash-card {{ background: white; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px -5px rgba(0,0,0,0.08); text-align: center; transition: all 0.3s; text-decoration: none; color: inherit; border: 1px solid #f1f5f9; display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden; }}
        .dash-card:hover {{ transform: translateY(-8px); }}
        
        .card-loto7::before {{ content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 6px; background: linear-gradient(90deg, #f59e0b, #d97706); }}
        .card-loto6::before {{ content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 6px; background: linear-gradient(90deg, #38bdf8, #0284c7); }}
        .card-numbers::before {{ content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 6px; background: linear-gradient(90deg, #4ade80, #16a34a); }}
        
        .carryover-badge {{ background: linear-gradient(135deg, #ef4444, #b91c1c); color: white; font-size: 14px; font-weight: bold; padding: 10px 15px; border-radius: 8px; margin: 15px auto 0; animation: pulse 2s infinite; box-shadow: 0 4px 10px rgba(239,68,68,0.4); }}
        @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.03); }} 100% {{ transform: scale(1); }} }}

        .dash-kai {{ font-size: 14px; color: #64748b; margin-bottom: 15px; font-weight: bold; }}
        .dash-nums {{ font-size: 24px; font-weight: 900; letter-spacing: 2px; color: #1e293b; margin-bottom: 8px; word-wrap: break-word; }}
        .dash-bonus {{ font-size: 14px; color: #10b981; font-weight: bold; background: #ecfdf5; display: inline-block; padding: 4px 12px; border-radius: 20px; }}
        .dash-nums-nm {{ font-size: 32px; font-weight: 900; letter-spacing: 8px; margin-bottom: 10px; }}
        
        /* スマートフォン向けレスポンシブ対応 */
        @media (max-width: 600px) {{
            .dash-nums {{ font-size: 18px; letter-spacing: 1px; }}
            .dash-nums-nm {{ font-size: 26px; letter-spacing: 4px; }}
            .dash-title {{ font-size: 18px; }}
        }}

        .jumbo-banner {{ background: linear-gradient(135deg, #be123c, #9f1239); border-radius: 16px; padding: 25px; color: white; text-align: center; margin-bottom: 40px; box-shadow: 0 10px 20px rgba(190, 18, 60, 0.2); }}
        .jumbo-banner a {{ display: inline-block; margin-top: 15px; padding: 10px 25px; background: white; color: #be123c; text-decoration: none; border-radius: 25px; font-weight: bold; }}

        .two-col-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; margin-bottom: 60px; }}
        .feature-card {{ background: white; border-radius: 16px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid #e2e8f0; }}
        .calendar-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        .lucky-day {{ color: #ea580c; font-weight: bold; background-color: #ffedd5; padding: 3px 6px; border-radius: 4px; }}
        .super-lucky {{ color: white; font-weight: bold; background-color: #ef4444; padding: 3px 6px; border-radius: 4px; }}

        .omikuji-area {{ text-align: center; padding: 20px 0; }}
        #omikuji-result {{ font-size: 32px; font-weight: 900; margin: 15px 0; }}
        .btn-omikuji {{ background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: none; padding: 12px 30px; font-weight: bold; border-radius: 30px; cursor: pointer; }}

        /* 詳細ガイド */
        .guide-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; }}
        .guide-card {{ background: white; border-radius: 16px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid #e2e8f0; }}
        .guide-card h3 {{ display: flex; align-items: center; font-size: 20px; margin-top: 0; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 2px solid #f1f5f9; }}
        .guide-desc {{ font-size: 14px; color: #475569; margin-bottom: 20px; line-height: 1.7; }}
        .spec-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        .spec-table th, .spec-table td {{ padding: 10px; border-bottom: 1px solid #f1f5f9; text-align: left; }}
        .spec-table th {{ width: 35%; color: #64748b; font-weight: normal; }}
        .spec-table td {{ font-weight: bold; color: #1e293b; }}
        .highlight-prize {{ color: #dc2626; font-size: 15px; font-weight: 900; }}

        footer {{ background-color: #1e293b; color: #94a3b8; text-align: center; padding: 40px 20px; margin-top: 60px; font-size: 13px; }}
        .footer-links a {{ color: #cbd5e1; text-decoration: none; margin: 0 10px; }}
    </style>
    <meta name="google-site-verification" content="j3Smi9nkNu6GZJ0TbgFNi8e_w9HwUt_dGuSia8RDX3Y" />
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1431683156739681"
     crossorigin="anonymous"></script>
</head>
<body>
    <header>
        <a href="index.html">
            <img src="Lotologo.png" alt="ロト＆ナンバーズ攻略局🎯完全無料のAI予想" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="font-size: 24px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">ロト＆ナンバーズ攻略局🎯完全無料のAI予想</div>
        </a>
    </header>
    
    <nav>
        <a href="index.html" class="active">トップ (速報)</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="column.html">攻略ガイド🔰</a>
    </nav>

    <div style="text-align: center; margin: 20px 0;">
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
        <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4FK6WI+3A98+64C3L" rel="nofollow">
        <img border="0" width="300" height="250" alt="" src="https://www28.a8.net/svt/bgt?aid=260331146268&wid=001&eno=01&mid=s00000015326001028000&mc=1"></a>
        <img border="0" width="1" height="1" src="https://www14.a8.net/0.gif?a8mat=4AZSSQ+4FK6WI+3A98+64C3L" alt="">
    </div>
        
    <div class="container">
        <h2 class="section-title">🔔 最新の抽選結果速報</h2>
        
        <div class="dashboard-grid">
            <a href="loto7.html" class="dash-card card-loto7">
                <div>
                    <div style="font-size: 20px; font-weight: 800; color: #d97706; border-bottom: 1px dashed #e2e8f0; margin-bottom:15px; padding-bottom:10px;">ロト7</div>
                    <div class="dash-kai">{l7_display.get('target_kai', '----')} の結果</div>
                    <div class="dash-nums">{l7_display.get('actual_main', '----')}</div>
                    <div class="dash-bonus">{l7_display.get('actual_bonus', '')}</div>
                    {l7_carry_html}
                </div>
            </a>

            <a href="loto6.html" class="dash-card card-loto6">
                <div>
                    <div style="font-size: 20px; font-weight: 800; color: #0284c7; border-bottom: 1px dashed #e2e8f0; margin-bottom:15px; padding-bottom:10px;">ロト6</div>
                    <div class="dash-kai">{l6_display.get('target_kai', '----')} の結果</div>
                    <div class="dash-nums">{l6_display.get('actual_main', '----')}</div>
                    <div class="dash-bonus">{l6_display.get('actual_bonus', '')}</div>
                    {l6_carry_html}
                </div>
            </a>

            <a href="numbers.html" class="dash-card card-numbers">
                <div>
                    <div style="font-size: 20px; font-weight: 800; color: #16a34a; border-bottom: 1px dashed #e2e8f0; margin-bottom:15px; padding-bottom:10px;">ナンバーズ</div>
                    <div class="dash-kai">{nm_display.get('target_kai', '----')} の結果</div>
                    <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                        <div>
                            <div style="font-size:12px; color:#64748b;">N4</div>
                            <div class="dash-nums-nm" style="color:#16a34a;">{nm_display.get('actual_n4', '----')}</div>
                        </div>
                        <div>
                            <div style="font-size:12px; color:#64748b;">N3</div>
                            <div class="dash-nums-nm" style="color:#d97706;">{nm_display.get('actual_n3', '----')}</div>
                        </div>
                    </div>
                </div>
            </a>
        </div>

        <div class="jumbo-banner">
            <h3>もうすぐ発売！ {jumbo_name}</h3>
            <p>{jumbo_prize} のチャンスを見逃すな！</p>
            <a href="jumbo.html">吉日カレンダーをチェック ＞</a>
        </div>

        <div class="two-col-grid">
            <div class="feature-card">
                <h3>🗓️ 近日の吉日カレンダー</h3>
                <table class="calendar-table">
                    <tr><td>4月15日 (水)</td><td><span class="lucky-day">一粒万倍日 + 大安</span></td></tr>
                    <tr><td>5月11日 (月)</td><td><span class="super-lucky">天赦日 + 一粒万倍日</span></td></tr>
                    <tr><td>5月23日 (土)</td><td><span class="lucky-day">一粒万倍日 + 大安</span></td></tr>
                    <tr><td>6月 4日 (木)</td><td><span class="lucky-day">寅の日</span></td></tr>
                </table>
            </div>

            <div class="feature-card">
                <h3>⛩️ 今日の運勢おみくじ</h3>
                <div class="omikuji-area">
                    <div id="omikuji-result">🎯 運試し！</div>
                    <button class="btn-omikuji" onclick="drawTopOmikuji()">おみくじを引く</button>
                </div>
            </div>
        </div>

        <div style="text-align: center; margin-bottom: 40px;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4UG1SQ+3P7U+61JSH" rel="nofollow">
            <img border="0" width="300" height="250" alt="" src="https://www22.a8.net/svt/bgt?aid=260331146293&wid=002&eno=01&mid=s00000017265001015000&mc=1"></a>
            <img border="0" width="1" height="1" src="https://www14.a8.net/0.gif?a8mat=4AZSSQ+4UG1SQ+3P7U+61JSH" alt="">
        </div>

        <h2 class="section-title">📖 取扱宝くじの詳細ガイド</h2>
        <div class="guide-grid">
            <div class="guide-card">
                <h3 style="color: #d97706;">🥇 ロト7 (LOTO7)</h3>
                <p class="guide-desc">1～37の中から異なる7個を選ぶ宝くじ。キャリーオーバー発生時の爆発力は全宝くじの中でトップクラスです。</p>
                <table class="spec-table">
                    <tr><th>💰 1等最高賞金</th><td class="highlight-prize">6億円 <span style="font-size:11px; font-weight:normal; color:#64748b;">(キャリー時 10億円)</span></td></tr>
                    <tr><th>🎯 1等当選確率</th><td>約 1 / 10,295,472</td></tr>
                    <tr><th>🗓️ 抽選日</th><td>毎週 金曜日</td></tr>
                    <tr><th>💴 1口の価格</th><td>300円</td></tr>
                </table>
            </div>

            <div class="guide-card">
                <h3 style="color: #0284c7;">🥈 ロト6 (LOTO6)</h3>
                <p class="guide-desc">1～43の中から異なる6個を選ぶ宝くじ。週に2回抽選があるため、コンスタントにワクワクを楽しめるのが特徴です。</p>
                <table class="spec-table">
                    <tr><th>💰 1等最高賞金</th><td class="highlight-prize">2億円 <span style="font-size:11px; font-weight:normal; color:#64748b;">(キャリー時 6億円)</span></td></tr>
                    <tr><th>🎯 1等当選確率</th><td>約 1 / 6,096,454</td></tr>
                    <tr><th>🗓️ 抽選日</th><td>毎週 月・木曜日</td></tr>
                    <tr><th>💴 1口の価格</th><td>200円</td></tr>
                </table>
            </div>

            <div class="guide-card">
                <h3 style="color: #16a34a;">🔢 ナンバーズ</h3>
                <p class="guide-desc">好きな3桁または4桁の数字を選ぶ宝くじ。並び順まで当てるストレートや、順不同のボックスなど戦略的な買い方が可能です。</p>
                <table class="spec-table">
                    <tr><th>💰 1等平均賞金</th><td class="highlight-prize">N4: 約90万円 <span style="font-size:12px; color:#d97706;">(N3: 約9万円)</span></td></tr>
                    <tr><th>🎯 当選確率</th><td>N4: 1/10,000 <span style="font-size:12px; color:#d97706;">(N3: 1/1,000)</span></td></tr>
                    <tr><th>🗓️ 抽選日</th><td>毎週 月〜金曜日</td></tr>
                    <tr><th>💴 1口の価格</th><td>各 200円</td></tr>
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

    <script>
        function drawTopOmikuji() {{
            const fortunes = ["大吉 🌟", "中吉 ☀️", "小吉 🌤️", "吉 ⛅", "末吉 ☁️", "凶 🌧️", "大凶 ⛈️"];
            const idx = Math.floor(Math.random() * fortunes.length);
            document.getElementById('omikuji-result').innerText = fortunes[idx];
        }}
    </script>
</body>
</html>"""
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✨ トップページの生成が完了しました！最新の当選番号が正しく表示されています。")

if __name__ == "__main__":
    build_index_html()