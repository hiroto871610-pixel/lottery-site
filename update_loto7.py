import random

# 1. 予想番号を5パターン生成する
def generate_all_patterns():
    html = '            \n'
    html += '            <div class="prediction-box">\n'
    for label in ['予想A', '予想B', '予想C', '予想D', '予想E']:
        nums = [str(n).zfill(2) for n in sorted(random.sample(range(1, 38), 7))]
        balls = "".join([f'<span class="ball">{n}</span>' for n in nums])
        html += f'                <div class="numbers-row"><div class="row-label">{label}</div><div class="ball-container">{balls}</div></div>\n'
    html += '            </div>\n'
    html += '            '
    return html

# 2. HTMLの全構造を定義する（デザインはそのまま）
template_before = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ロト7 (LOTO7) 当選予想・分析データ | 宝くじポータル</title>
    <style>
        body { font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }
        header { background-color: #1e3a8a; color: white; padding: 20px; text-align: center; }
        header h1 { margin: 0; font-size: 24px; }
        nav { display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }
        nav a { color: #1e3a8a; padding: 15px 20px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; }
        nav a.active { border-bottom: 3px solid #d97706; color: #d97706; }
        nav a:hover { background-color: #f0f4f8; }
        .container { max-width: 900px; margin: 30px auto; padding: 0 20px; }
        .section-card { background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .section-header { color: #d97706; border-bottom: 2px solid #fef3c7; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; }
        .prediction-box { background-color: #fffbeb; border: 2px solid #fcd34d; border-radius: 12px; padding: 25px; margin-bottom: 20px;}
        .numbers-row { background-color: #ffffff; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; align-items: center; }
        .row-label { font-size: 18px; font-weight: bold; color: #1e3a8a; background-color: #e0e7ff; padding: 5px 15px; border-radius: 4px; margin-right: 20px; min-width: 60px; text-align: center; }
        .ball-container { display: flex; gap: 8px; flex-wrap: wrap; }
        .ball { display: inline-flex; justify-content: center; align-items: center; width: 42px; height: 42px; background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border-radius: 50%; font-size: 18px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.3); }
        @media (max-width: 600px) { .numbers-row { flex-direction: column; align-items: flex-start; padding: 15px;} .row-label { margin-bottom: 10px; } .ball { width: 36px; height: 36px; font-size: 16px;} }
        .hc-container { display: flex; gap: 20px; flex-wrap: wrap; }
        .hc-box { flex: 1; min-width: 250px; padding: 15px; border-radius: 8px; }
        .hot-box { background-color: #fee2e2; border: 1px solid #fca5a5; }
        .cold-box { background-color: #e0f2fe; border: 1px solid #7dd3fc; }
        .hc-title { font-weight: bold; margin-bottom: 10px; }
        .hc-number { display: inline-block; padding: 5px 10px; margin: 3px; border-radius: 4px; font-weight: bold; background: white; }
        .hot-box .hc-number { color: #ef4444; border: 1px solid #ef4444; }
        .cold-box .hc-number { color: #0ea5e9; border: 1px solid #0ea5e9; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: center; }
        th, td { padding: 12px; border-bottom: 1px solid #e2e8f0; }
        th { background-color: #f8fafc; color: #475569; font-weight: bold; }
        .result-win { color: #16a34a; font-weight: bold; background-color: #dcfce7; padding: 4px 8px; border-radius: 4px; }
        footer { background-color: #333; color: #ccc; text-align: center; padding: 30px; margin-top: 50px; font-size: 12px; }
    </style>
</head>
<body>
    <header><h1>宝くじ当選予想・データ分析ポータル</h1></header>
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html" class="active">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
    </nav>
    <div class="container">
        <div style="background: #e2e8f0; padding: 20px; text-align: center; margin-bottom: 30px; border-radius: 8px; font-size: 12px; color: #64748b;">【広告】Google AdSense</div>
        <div class="section-card">
            <h2 class="section-header">🎯 第0000回 ロト7 (〇月〇日 金曜抽選) の予想</h2>
            <p>直近の傾向と独自のアルゴリズムから弾き出した、今回の推奨5パターンです。</p>
"""

template_after = """
        </div>
        <div class="section-card">
            <h2 class="section-header">📊 直近20回の出現傾向 (ホット＆コールド)</h2>
            <div class="hc-container">
                <div class="hc-box hot-box"><div class="hc-title">🔥 HOT</div><span class="hc-number">15</span><span class="hc-number">04</span></div>
                <div class="hc-box cold-box"><div class="hc-title">❄️ COLD</div><span class="hc-number">08</span><span class="hc-number">29</span></div>
            </div>
        </div>
    </div>
    <footer><p>&copy; 2026 宝くじポータル</p></footer>
</body>
</html>"""

# 3. 合体させて上書き保存
final_html = template_before + generate_all_patterns() + template_after
with open('loto7.html', 'w', encoding='utf-8') as f:
    f.write(final_html)

print("✨ ついに大成功！loto7.htmlを新しく作り直しました！")
