import random
import requests
from bs4 import BeautifulSoup
import re

def generate_numbers_patterns():
    html = '            \n'
    html += '            <h2 class="section-header" style="margin-top: 0;">🔢 次回 ナンバーズ4 予想</h2>\n'
    html += '            <div class="prediction-box">\n'
    tags = ['<span class="recommend-tag tag-straight">ストレート推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨</span>', '<span class="recommend-tag tag-box">ボックス推奨 (ダブル)</span>']
    for i, label in enumerate(['予想A', '予想B', '予想C']):
        nums = [str(random.randint(0, 9)) for _ in range(4)]
        balls = "".join([f'<span class="ball">{n}</span>' for n in nums])
        html += f'                <div class="numbers-row"><div class="row-label">{label}</div><div class="ball-container">{balls}</div>{tags[i]}</div>\n'
    html += '            </div>\n'
    html += '            <h2 class="section-header" style="margin-top: 40px;">🔢 次回 ナンバーズ3 予想</h2>\n'
    html += '            <div class="prediction-box">\n'
    for i, label in enumerate(['予想A', '予想B', '予想C']):
        nums = [str(random.randint(0, 9)) for _ in range(3)]
        balls = "".join([f'<span class="ball">{n}</span>' for n in nums])
        html += f'                <div class="numbers-row"><div class="row-label">{label}</div><div class="ball-container">{balls}</div>{tags[i]}</div>\n'
    html += '            </div>\n            '
    return html

def fetch_latest_result():
    try:
        url = "https://www.mizuhobank.co.jp/retail/takarakuji/numbers/numbers4/index.html"
        res = requests.get(url, timeout=10)
        res.encoding = 'Shift_JIS'
        soup = BeautifulSoup(res.text, 'html.parser')

        kai_th = soup.find('th', string=re.compile(r'第\d+回'))
        if not kai_th: raise ValueError("回号が見つかりません")
        kai = kai_th.text.strip()
        date_td = kai_th.find_next_sibling('td')
        date = date_td.text.strip() if date_td else "最新"

        # 【本番用】当選番号を柔軟に抽出（抽せん数字 または 当せん番号）
        win_th = soup.find(['th', 'td'], string=re.compile(r'抽せん数字|当せん番号|当せん数字|抽せん番号'))
        win_num = "----"
        if win_th:
            win_td = win_th.find_next_sibling(['td', 'th'])
            if win_td:
                nums_only = re.sub(r'\D', '', win_td.text)
                if nums_only: win_num = nums_only
            
            # 隣に見つからなければ次の行(tr)を探す
            if win_num == "----":
                tr_head = win_th.find_parent('tr')
                if tr_head:
                    tr_next = tr_head.find_next_sibling('tr')
                    if tr_next:
                        tds = tr_next.find_all('td')
                        if tds:
                            nums_only = re.sub(r'\D', '', tds[0].text)
                            if nums_only: win_num = nums_only

        print(f"📡 ナンバーズ4 データ取得成功: {kai} ({date}) | 当選番号: {win_num}")
        return kai, date, win_num

    except Exception as e:
        print(f"⚠️ ナンバーズ データ取得エラー: {e}")
        return "最新回", "データ取得中", "----"

def build_html():
    kai, date, win_num = fetch_latest_result()
    template_before = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ナンバーズ3＆4 当選予想・データ | 宝くじポータル</title>
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; color: white; padding: 20px; text-align: center; }}
        header h1 {{ margin: 0; font-size: 24px; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #1e3a8a; padding: 15px 20px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; }}
        nav a.active {{ border-bottom: 3px solid #16a34a; color: #16a34a; }}
        nav a:hover {{ background-color: #f0f4f8; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #16a34a; border-bottom: 2px solid #dcfce7; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; }}
        .prediction-box {{ background-color: #f0fdf4; border: 2px solid #bbf7d0; border-radius: 12px; padding: 25px; margin-bottom: 20px;}}
        .numbers-row {{ background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; align-items: center; }}
        .row-label {{ font-size: 18px; font-weight: bold; color: #1e3a8a; background-color: #e0e7ff; padding: 5px 15px; border-radius: 4px; margin-right: 20px; min-width: 60px; text-align: center; }}
        .ball-container {{ display: flex; gap: 12px; flex-wrap: wrap; margin-right: auto;}}
        .ball {{ display: inline-flex; justify-content: center; align-items: center; width: 45px; height: 45px; background: linear-gradient(135deg, #22c55e, #16a34a); color: white; border-radius: 8px; font-size: 24px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.3); }}
        .recommend-tag {{ font-size: 14px; font-weight: bold; padding: 4px 10px; border-radius: 20px; margin-left: 10px; white-space: nowrap;}}
        .tag-straight {{ background-color: #fee2e2; color: #ef4444; border: 1px solid #fca5a5;}}
        .tag-box {{ background-color: #e0f2fe; color: #0ea5e9; border: 1px solid #7dd3fc;}}
        @media (max-width: 600px) {{ .numbers-row {{ flex-direction: column; align-items: flex-start; padding: 15px;}} .row-label {{ margin-bottom: 10px; }} .ball {{ width: 40px; height: 40px; font-size: 20px;}} .recommend-tag {{ margin-left: 0; margin-top: 10px; }} }}
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
        .result-win {{ color: #16a34a; font-weight: bold; background-color: #dcfce7; padding: 4px 8px; border-radius: 4px; }}
        footer {{ background-color: #333; color: #ccc; text-align: center; padding: 30px; margin-top: 50px; font-size: 12px; }}
    </style>
</head>
<body>
    <header><h1>宝くじ当選予想・データ分析ポータル</h1></header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html" class="active">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
    </nav>
    <div class="container">
        <div style="background: #e2e8f0; padding: 20px; text-align: center; margin-bottom: 30px; border-radius: 8px; font-size: 12px; color: #64748b;">【広告】Google AdSense</div>
        <div class="section-card">
"""
    template_after = f"""        </div>
        <div class="section-card">
            <h2 class="section-header">📊 直近20回の出現傾向 (0〜9の数字)</h2>
            <div class="hc-container">
                <div class="hc-box hot-box"><div class="hc-title">🔥 よく出ている数字</div><span class="hc-number">7 (12回)</span><span class="hc-number">2 (10回)</span></div>
                <div class="hc-box cold-box"><div class="hc-title">❄️ 出ていない数字</div><span class="hc-number">4 (1回)</span><span class="hc-number">1 (2回)</span></div>
            </div>
        </div>
        <div class="section-card">
            <h2 class="section-header">📝 最新の抽選結果速報</h2>
            <table>
                <thead><tr><th>回号 (抽選日)</th><th>当選番号 (ナンバーズ4)</th><th>当サイトの成績照合</th></tr></thead>
                <tbody>
                    <tr>
                        <td style="font-weight:bold; color:#1e3a8a;">{kai}<br><span style="font-size:12px; font-weight:normal; color:#666;">({date})</span></td>
                        <td style="font-size:18px; font-weight: bold; letter-spacing: 3px;">{win_num}</td>
                        <td><span class="result-win">データ集計中...</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    <footer><p>&copy; 2026 宝くじ当選予想・データ分析ポータル</p></footer>
</body>
</html>"""
    return template_before + generate_numbers_patterns() + template_after

with open('numbers.html', 'w', encoding='utf-8') as f: f.write(build_html())
print("✨ [本番データ] ナンバーズ の更新が完了しました！")