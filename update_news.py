import os
import json
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# JSONBin API設定 (各宝くじの履歴取得用)
# =========================================================
JSONBIN_API_KEY = os.environ.get("JSONBIN_API_KEY")

def fetch_history_from_jsonbin(bin_id):
    """JSONBinから指定されたIDの履歴データを取得する"""
    if not bin_id or not JSONBIN_API_KEY: return []
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    try:
        url = f"https://api.jsonbin.io/v3/b/{bin_id}"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get('record', [])
    except Exception as e:
        print(f"⚠️ JSONBin取得エラー (BIN_ID: {bin_id}): {e}")
    return []

# =========================================================
# 💰 i-mobile 広告共通パーツ（削減せず全て維持）
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
imobile_ad2_pc = """<div id="im-d34f87828c9740a7b9a62172425cfcfd"><script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script><script>(window.adsbyimobile=window.adsbyimobile||[]).push({pid:84847,mid:592459,asid:1929931,type:"banner",display:"inline",elementid:"im-d34f87828c9740a7b9a62172425cfcfd"})</script></div>"""
imobile_ad2_sp = """<div id="im-c4e1d905d99e4087b6a8d79bcd575552"><script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script><script>(window.adsbyimobile=window.adsbyimobile||[]).push({pid:84847,mid:592460,asid:1929935,type:"banner",display:"inline",elementid:"im-c4e1d905d99e4087b6a8d79bcd575552"})</script></div>"""
imobile_ad3_pc = """<div id="im-4465412234044af19505d01849472875"><script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script><script>(window.adsbyimobile=window.adsbyimobile||[]).push({pid:84847,mid:592459,asid:1929933,type:"banner",display:"inline",elementid:"im-4465412234044af19505d01849472875"})</script></div>"""
imobile_ad3_sp = """<div id="im-111a4112bae54171b8c129433281c73c"><script async src="https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104"></script><script>(window.adsbyimobile=window.adsbyimobile||[]).push({pid:84847,mid:592460,asid:1929936,type:"banner",display:"inline",elementid:"im-111a4112bae54171b8c129433281c73c"})</script></div>"""

def fetch_microcms_news():
    """microCMSから管理者のお知らせを取得する"""
    domain = os.environ.get("MICROCMS_SERVICE_DOMAIN")
    api_key = os.environ.get("MICROCMS_API_KEY")
    
    if not domain or not api_key:
        print("⚠️ microCMSの環境変数が設定されていません。手動ニュースの取得をスキップします。")
        return []

    url = f"https://{domain}.microcms.io/api/v1/news"
    headers = {"X-MICROCMS-API-KEY": api_key}
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            news_list = []
            for item in data.get("contents", []):
                # publishedAt (例: 2026-05-01T10:00:00Z) の日付部分だけ取得
                date_str = item.get("publishedAt", "")[:10]
                # セレクトフィールドがリストで返る場合と単体の場合を考慮
                tag_val = item.get("tag", ["info"])
                tag = tag_val[0] if isinstance(tag_val, list) else tag_val
                
                news_list.append({
                    "date": date_str,
                    "tag": tag,
                    "title": item.get("title", ""),
                    "content": item.get("content", "")
                })
            return news_list
        else:
            print(f"❌ microCMS取得エラー: {res.status_code}")
    except Exception as e:
        print(f"❌ microCMS通信エラー: {e}")
    return []

def generate_auto_wins_news():
    """JSONBinの履歴を直接確認し、最新回で的中があれば自動で号外を作成する"""
    auto_news = []
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # ロト7の判定
    l7_history = fetch_history_from_jsonbin(os.environ.get("JSONBIN_BIN_ID_LOTO7"))
    if l7_history and l7_history[0].get('status') == 'finished':
        best = l7_history[0].get('best_result', '')
        if "🎯" in best:
            auto_news.append({
                "date": today_str,
                "tag": "win",
                "title": f"🚨 号外：ロト7 {l7_history[0]['target_kai']} で的中発生！",
                "content": f"当サイトのAI予想が見事【{best}】を的中させました！詳細はロト7のページでご確認ください。"
            })

    # ロト6の判定 (Loto6は元のJSONBIN_BIN_IDを使用)
    l6_history = fetch_history_from_jsonbin(os.environ.get("JSONBIN_BIN_ID"))
    if l6_history and l6_history[0].get('status') == 'finished':
        best = l6_history[0].get('best_result', '')
        if "🎯" in best:
            auto_news.append({
                "date": today_str,
                "tag": "win",
                "title": f"🚨 号外：ロト6 {l6_history[0]['target_kai']} で的中発生！",
                "content": f"当サイトのAI予想が見事【{best}】を的中させました！詳細はロト6のページでご確認ください。"
            })

    # ナンバーズの判定
    nm_history = fetch_history_from_jsonbin(os.environ.get("JSONBIN_BIN_ID_NUMBERS"))
    if nm_history and nm_history[0].get('status') == 'finished':
        n4_res = nm_history[0].get('result_n4', '')
        n3_res = nm_history[0].get('result_n3', '')
        hits = []
        if "🎯" in n4_res: hits.append(f"N4: {n4_res}")
        if "🎯" in n3_res: hits.append(f"N3: {n3_res}")
        
        if hits:
            auto_news.append({
                "date": today_str,
                "tag": "win",
                "title": f"🚨 号外：ナンバーズ {nm_history[0]['target_kai']} で的中発生！",
                "content": f"当サイトのAI予想が的中しました！ ({' / '.join(hits)}) 詳細はナンバーズのページでご確認ください。"
            })

    return auto_news

def build_news_html():
    print("🔄 NEWS・速報ページを生成中...")
    
    # 1. microCMSから手動のお知らせを取得
    manual_news = fetch_microcms_news()
    
    # 2. JSONBinから自動で的中の号外を生成
    auto_news = generate_auto_wins_news()

    # 3. 合体させて日付順（新しい順）に並び替え
    all_news = manual_news + auto_news
    all_news.sort(key=lambda x: x["date"], reverse=True)

    # ニュースのHTMLブロックを生成
    news_items_html = ""
    for item in all_news:
        date_str = item["date"].replace("-", "/")
        
        # タグによってデザイン（色）を変える
        if item["tag"] == "win":
            tag_html = '<span style="background: #ef4444; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; display: inline-block; box-shadow: 0 2px 4px rgba(239,68,68,0.3); animation: pulse 2s infinite;">🎯 的中速報</span>'
            border_color = "#fecaca"
            bg_color = "#fff1f2"
        elif item["tag"] == "update":
            tag_html = '<span style="background: #3b82f6; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; display: inline-block;">✨ アップデート</span>'
            border_color = "#bfdbfe"
            bg_color = "#eff6ff"
        else: # info
            tag_html = '<span style="background: #10b981; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; display: inline-block;">📢 お知らせ</span>'
            border_color = "#bbf7d0"
            bg_color = "#f0fdf4"

        news_items_html += f"""
        <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 20px; margin-bottom: 20px; display: flex; flex-direction: column; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px dashed {border_color}; padding-bottom: 10px; margin-bottom: 15px;">
                {tag_html}
                <span style="color: #64748b; font-size: 14px; font-weight: bold;">{date_str}</span>
            </div>
            <h3 style="margin: 0 0 10px 0; color: #1e293b; font-size: 18px;">{item["title"]}</h3>
            <p style="margin: 0; color: #475569; font-size: 15px; line-height: 1.6; white-space: pre-wrap;">{item["content"]}</p>
        </div>
        """

    if not news_items_html:
        news_items_html = "<p style='text-align: center; color: #64748b;'>現在お知らせはありません。</p>"

    # HTML全体の組み立て（トップページとデザインを統一）
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEWS・的中速報 | ロト＆ナンバーズ攻略局🎯完全無料のAI予想</title>
    <link rel="icon" type="image/png" href="favicon.icon.png">
    <link rel="apple-touch-icon" href="favicon.icon.png">
    <meta name="description" content="AI予想の的中速報や、サイトの最新アップデート情報をお届けします。">
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #2d3748; line-height: 1.6; }}
        header {{ background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%); color: white; padding: 30px 20px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        header a {{ text-decoration: none; color: white; display: block; }}
        nav {{ display: flex; justify-content: center; background-color: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 100; border-bottom: 1px solid #e2e8f0; }}
        /* ▼ PCでのナビゲーション設定 ▼ */
        nav a {{
            color: #1e3a8a; 
            padding: 14px 15px; /* クリックしやすいように少し広げる */
            font-size: 15px;    /* PCでは少し大きめ */
            text-decoration: none; 
            font-weight: bold; 
            border-bottom: 3px solid transparent; 
            transition: all 0.3s; 
        }}
        nav a:hover {{ color: #1e3a8a; background-color: #f8fafc; }}
        nav a.active {{ color: #1e3a8a; border-bottom: 3px solid #1e3a8a; }}
        .container {{ max-width: 800px; margin: 40px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px; }}
        .section-header {{ color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 25px; font-size: 22px; text-align: center; }}
        
        @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.05); }} 100% {{ transform: scale(1); }} }}

        footer {{ background-color: #1e293b; color: #94a3b8; text-align: center; padding: 40px 20px; margin-top: 60px; font-size: 13px; }}
        .footer-links a {{ color: #cbd5e1; text-decoration: none; margin: 0 10px; }}
        
        .ad-pc {{ display: block; }} .ad-sp {{ display: none; }}
        @media (max-width: 600px) {{ .ad-pc {{ display: none; }} .ad-sp {{ display: block; }} 
        
        /* ▼ ここから追加：スマホでメニューを2段に収める魔法 ▼ */
            nav {{
                padding: 0 2px; /* スマホ画面の横幅ギリギリまで使う */
            }}
            nav a {{
                font-size: 12px; /* スマホでは文字を小さく */
                padding: 10px 5px; /* 左右の余白を削って横並びにさせる */
                letter-spacing: -0.5px; /* 文字の間隔を少しだけ詰める */
            }}
            /* ▲ ここまで追加 ▲ */

        }}
    </style>
</head>
<body>
    <header>
        <a href="index.html">
            <img src="Lotologo001.png" alt="ロト＆ナンバーズ攻略局🎯完全無料のAI予想" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="font-size: 24px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">NEWS・的中速報</div>
        </a>
    </header>
    
    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="column.html">攻略ガイド🔰</a>
        <a href="horoscope.html">占い🔮</a>
        <a href="archive.html" >YOUTUBE🎥</a>
        <a href="news.html" class="active">NEWS📰</a>
    </nav>

    <div class="container">
        <!-- 広告エリア 上部 -->
        <div style="text-align: center; margin-bottom: 30px;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <div class="ad-pc">{imobile_ad2_pc}</div>
            <div class="ad-sp">{imobile_ad2_sp}</div>
        </div>

        <div class="section-card">
            <h2 class="section-header">📢 最新のお知らせ・的中速報</h2>
            <p style="font-size: 14px; color: #64748b; text-align: center; margin-bottom: 30px;">
                サイトのアップデート情報や、AI予想の的中結果を自動でお届けします。
            </p>
            
            {news_items_html}
            
        </div>

        <!-- 広告エリア 下部 -->
        <div style="text-align: center; margin-bottom: 30px;">
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
        <p>※当サイトの予想・データは当選を保証するものではありません。宝くじの購入は自己責任でお願いいたします。</p>
        <p style="margin-top: 10px; color: #64748b;">&copy; 2026 ロト＆ナンバーズ攻略局🎯完全無料のAI予想 All Rights Reserved.</p>
    </footer>

    {imobile_overlay}
</body>
</html>"""

    with open('news.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("✨ NEWSページ (news.html) の生成が完了しました！")

if __name__ == "__main__":
    build_news_html()