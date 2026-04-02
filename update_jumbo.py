import os
import datetime

# --- 1. 季節に合わせて「次回のジャンボ」を自動判定する機能 ---
def get_next_jumbo():
    today = datetime.date.today()
    m = today.month
    if m == 1 or m == 2:
        return "🍫 バレンタインジャンボ", "1等・前後賞合わせて 3億円", "2月上旬 〜 3月上旬"
    elif m >= 3 and m <= 5:
        return "🌸 ドリームジャンボ", "1等・前後賞合わせて 5億円", "5月上旬 〜 6月上旬"
    elif m == 6 or m == 7:
        return "🌻 サマージャンボ", "1等・前後賞合わせて 7億円", "7月上旬 〜 8月上旬"
    elif m >= 8 and m <= 10:
        return "🎃 ハロウィンジャンボ", "1等・前後賞合わせて 5億円", "9月下旬 〜 10月下旬"
    else:
        return "⛄ 年末ジャンボ", "1等・前後賞合わせて 10億円", "11月下旬 〜 12月下旬"

# --- 2. HTML構築 ---
def build_html():
    print("🔄 ジャンボ宝くじ ページの生成を開始...")
    
    next_name, next_prize, next_date = get_next_jumbo()
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ジャンボ宝くじ 攻略・吉日カレンダー | 宝くじ当選予想・データ分析ポータル</title>
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; padding: 15px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #1e3a8a; padding: 15px 20px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; transition: all 0.3s; }}
        nav a.active {{ border-bottom: 3px solid #be123c; color: #be123c; background-color: #fff1f2; }}
        nav a:hover {{ background-color: #f0f4f8; }}

        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #be123c; border-bottom: 2px solid #ffe4e6; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; display: flex; align-items: center; }}
        
        .info-box {{ background-color: #fff1f2; border: 2px solid #fecdd3; border-radius: 12px; padding: 25px; margin-bottom: 20px; text-align: center; }}
        
        /* リスト・カードデザイン */
        .grid-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
        .jumbo-card {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; background: #f8fafc; border-left: 4px solid #be123c; }}
        .jumbo-card h3 {{ margin: 0 0 10px 0; color: #0f172a; font-size: 18px; }}
        .jumbo-card p {{ margin: 5px 0; font-size: 14px; color: #475569; }}
        .jumbo-card .prize {{ font-weight: bold; color: #e11d48; }}

        /* カレンダーテーブル */
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 15px; text-align: left; }}
        th, td {{ padding: 12px 15px; border-bottom: 1px solid #e2e8f0; }}
        th {{ background-color: #f8fafc; color: #475569; font-weight: bold; }}
        .lucky-day {{ color: #ea580c; font-weight: bold; background-color: #ffedd5; padding: 4px 8px; border-radius: 4px; display: inline-block; font-size: 13px; }}
        .super-lucky {{ color: white; font-weight: bold; background-color: #ef4444; padding: 4px 8px; border-radius: 4px; display: inline-block; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3); font-size: 13px; }}

        /* 売り場検索ボタン */
        .search-btn {{ display: block; width: 100%; max-width: 300px; margin: 20px auto; padding: 15px; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; text-align: center; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3); transition: transform 0.2s; }}
        .search-btn:hover {{ transform: translateY(-2px); }}

        /* おみくじ */
        .omikuji-box {{ text-align: center; padding: 25px; background: linear-gradient(135deg, #fef08a, #fde047); border-radius: 8px; border: 2px solid #facc15; box-shadow: 0 4px 10px rgba(250, 204, 21, 0.2); }}
        .omikuji-result {{ font-size: 28px; font-weight: bold; color: #b45309; margin: 15px 0; letter-spacing: 2px; background: white; padding: 15px; border-radius: 8px; display: inline-block; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05); }}
        .btn-omikuji {{ background-color: #be123c; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 25px; cursor: pointer; font-weight: bold; transition: background 0.2s; }}
        .btn-omikuji:hover {{ background-color: #9f1239; }}

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
            <div style="color: white; font-size: 16px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">宝くじ当選予想・データ分析ポータル</div>
        </a>
    </header>

    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html" class="active">ジャンボ</a>
    </nav>

    <div class="container">
        <div style="text-align: center; margin-bottom: 40px;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4FK6WI+3A98+64C3L" rel="nofollow">
            <img border="0" width="300" height="250" alt="" src="https://www28.a8.net/svt/bgt?aid=260331146268&wid=001&eno=01&mid=s00000015326001028000&mc=1"></a>
            <img border="0" width="1" height="1" src="https://www14.a8.net/0.gif?a8mat=4AZSSQ+4FK6WI+3A98+64C3L" alt="">
        </div>

        <div class="section-card">
            <h2 class="section-header">🎯 次回のジャンボ宝くじ</h2>
            <div class="info-box">
                <h3 style="margin-top: 0; color: #be123c; font-size: 26px;">{next_name}</h3>
                <p style="font-weight: bold; font-size: 20px; margin-bottom: 10px; color: #0f172a;">
                    {next_prize}
                </p>
                <p style="color: #475569; font-weight: bold; background: white; display: inline-block; padding: 5px 15px; border-radius: 20px;">
                    発売予定：{next_date}
                </p>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">✨ 5大ジャンボ宝くじ 概要</h2>
            <p style="font-size: 14px; margin-bottom: 20px;">年間を通じて5回開催される大型宝くじのスケジュールと賞金目安です。</p>
            <div class="grid-container">
                <div class="jumbo-card">
                    <h3>🍫 バレンタインジャンボ</h3>
                    <p>時期：2月〜3月</p>
                    <p class="prize">賞金：1等前後賞 3億円</p>
                </div>
                <div class="jumbo-card">
                    <h3>🌸 ドリームジャンボ</h3>
                    <p>時期：5月〜6月</p>
                    <p class="prize">賞金：1等前後賞 5億円</p>
                </div>
                <div class="jumbo-card">
                    <h3>🌻 サマージャンボ</h3>
                    <p>時期：7月〜8月</p>
                    <p class="prize">賞金：1等前後賞 7億円</p>
                </div>
                <div class="jumbo-card">
                    <h3>🎃 ハロウィンジャンボ</h3>
                    <p>時期：9月〜10月</p>
                    <p class="prize">賞金：1等前後賞 5億円</p>
                </div>
                <div class="jumbo-card" style="border-left-color: #fbbf24; background-color: #fefce8;">
                    <h3>⛄ 年末ジャンボ</h3>
                    <p>時期：11月〜12月</p>
                    <p class="prize" style="font-size: 18px;">賞金：1等前後賞 10億円！</p>
                </div>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">📢 直近のジャンボ抽選結果</h2>
            <p style="font-size: 14px; color: #64748b;">※最新の確定情報はみずほ銀行または楽天宝くじ公式サイトを必ずご確認ください。</p>
            <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 20px;">
                <h3 style="margin-top: 0; color: #1e3a8a; border-bottom: 1px dashed #cbd5e1; padding-bottom: 10px;">バレンタインジャンボ宝くじ (第1000回)</h3>
                <p style="font-size: 14px; margin-bottom: 15px;">抽選日：2026年3月13日</p>
                <table style="margin-top: 0;">
                    <tr><th style="width: 30%;">1等 (2億円)</th><td style="font-weight: bold; color: #e11d48; font-size: 18px;">16組 123456番</td></tr>
                    <tr><th>1等の前後賞 (5000万円)</th><td>1等の前後の番号</td></tr>
                    <tr><th>1等の組違い賞 (10万円)</th><td>1等の組違い同番号</td></tr>
                    <tr><th>2等 (1000万円)</th><td>45組 112233番</td></tr>
                    <tr><th>3等 (100万円)</th><td>各組共通 987654番</td></tr>
                    <tr><th>4等 (1万円)</th><td>下3ケタ 789番</td></tr>
                    <tr><th>5等 (3000円)</th><td>下2ケタ 55番</td></tr>
                    <tr><th>6等 (300円)</th><td>下1ケタ 7番</td></tr>
                </table>
            </div>
        </div>

        <div class="section-card">
            <h2 class="section-header">🏆 売り場検索＆有名スポット</h2>
            <p style="font-size: 14px; line-height: 1.6;">ジャンボ宝くじは「どこで買うか」も楽しみの一つ！スマートフォンの位置情報を利用して、今いる場所から一番近い宝くじ売り場をGoogleマップで一発検索できます。</p>
            
            <a href="https://www.google.com/maps/search/%E5%AE%9D%E3%81%8F%E3%81%98%E5%A3%B2%E3%82%8A%E5%A0%B4/" target="_blank" class="search-btn">
                📍 近くの宝くじ売り場を探す
            </a>

            <h3 style="font-size: 16px; margin-top: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px;">🔥 高額当選が連発する全国の有名売り場</h3>
            <ul style="font-size: 14px; line-height: 1.8; color: #475569;">
                <li><strong>西銀座チャンスセンター（東京）</strong> - 日本一有名な売り場。「1番窓口」が特に大人気です。</li>
                <li><strong>大阪駅前第4ビル特設売場（大阪）</strong> - 西の横綱。数々の億万長者を輩出。</li>
                <li><strong>大通地下チャンスセンター（札幌）</strong> - 北海道の激アツスポット。旅行のついでに立ち寄るファンも多数！</li>
                <li><strong>名駅前チャンスセンター（名古屋）</strong> - 東海地方の金運メッカ。</li>
            </ul>
        </div>

        <div class="section-card">
            <h2 class="section-header">🗓️ 宝くじ購入 吉日カレンダー（2026年 注目日）</h2>
            <p style="font-size: 14px;">一粒万倍日（いちりゅうまんばいび）や天赦日（てんしゃにち）など、お金にまつわる吉日です。高額当選者がわざわざ並んで購入する日として知られています。</p>
            <table>
                <thead>
                    <tr><th>日付</th><th>吉日の種類</th><th>おすすめ度</th></tr>
                </thead>
                <tbody>
                    <tr><td>2026年 5月11日 (月)</td><td><span class="super-lucky">天赦日 ＋ 一粒万倍日</span></td><td>★★★★★ (最強開運日🔥)</td></tr>
                    <tr><td>2026年 5月23日 (土)</td><td><span class="lucky-day">一粒万倍日 ＋ 大安</span></td><td>★★★★☆ (週末で狙い目)</td></tr>
                    <tr><td>2026年 6月 4日 (木)</td><td><span class="lucky-day">寅の日</span></td><td>★★★☆☆ (金運招来日)</td></tr>
                    <tr><td>2026年 7月23日 (木)</td><td><span class="super-lucky">天赦日 ＋ 一粒万倍日</span></td><td>★★★★★ (サマー狙い目)</td></tr>
                </tbody>
            </table>
        </div>

        <div style="text-align: center; margin-bottom: 40px;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <a href="https://px.a8.net/svt/ejp?a8mat=4AZSSQ+4UG1SQ+3P7U+61JSH" rel="nofollow">
            <img border="0" width="300" height="250" alt="" src="https://www28.a8.net/svt/bgt?aid=260331146293&wid=002&eno=01&mid=s00000017265001015000&mc=1"></a>
            <img border="0" width="1" height="1" src="https://www14.a8.net/0.gif?a8mat=4AZSSQ+4UG1SQ+3P7U+61JSH" alt="">
        </div>

        <div class="section-card" style="background: transparent; box-shadow: none; padding: 0;">
            <div class="omikuji-box">
                <h3 style="margin-top: 0; color: #854d0e; font-size: 20px;">🔮 今日のあなたのラッキーナンバー</h3>
                <p style="font-size: 14px; color: #a16207; margin-bottom: 5px;">窓口での「組指定買い」や、バラを買う際の参考に！</p>
                <div class="omikuji-result" id="omikuji-display">組：<span style="color:#ef4444;">--</span>組 / 下1桁：<span style="color:#ef4444;">-</span></div>
                <br>
                <button class="btn-omikuji" onclick="drawOmikuji()">もう一度占う</button>
            </div>
        </div>

    </div>

    <footer>
        <div class="footer-links">
            <a href="privacy.html">プライバシーポリシー</a> | 
            <a href="disclaimer.html">免責事項</a> | 
            <a href="contact.html">お問い合わせ</a>
        </div>
        <p><strong>【免責事項】</strong><br>当サイトの情報は高額当選を保証するものではありません。宝くじの購入は無理のない範囲で、自己責任にてお楽しみください。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 宝くじ当選予想・データ分析ポータル All Rights Reserved.</p>
    </footer>

    <script>
        function drawOmikuji() {{
            const kumi = Math.floor(Math.random() * 100) + 1; 
            const keta = Math.floor(Math.random() * 10);      
            const resultDiv = document.getElementById('omikuji-display');
            resultDiv.innerHTML = `組：<span style="color:#ef4444;">${{kumi.toString().padStart(2, '0')}}</span>組 / 下1桁：<span style="color:#ef4444;">${{keta}}</span>`;
        }}
        document.addEventListener('DOMContentLoaded', drawOmikuji);
    </script>
</body>
</html>"""
    return html

final_html = build_html()
with open('jumbo.html', 'w', encoding='utf-8') as f:
    f.write(final_html)
print("✨ [完成版] ジャンボ宝くじページの生成が完了しました！")