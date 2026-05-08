import os
import json
import datetime
import re
import requests
from bs4 import BeautifulSoup
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

def get_carryover(lottery_type):
    """楽天宝くじのページから【最新回】のキャリーオーバーを正確に取得する"""
    if lottery_type not in ["loto6", "loto7"]:
        return "" # ナンバーズにはキャリーオーバーがないため空白を返す

    url = f"https://takarakuji.rakuten.co.jp/backnumber/{lottery_type}/"
    try:
        res = requests.get(url, timeout=5)
        res.encoding = 'euc-jp'
        soup = BeautifulSoup(res.text, 'html.parser')

        # 「本数字」と「1等」が含まれている最初のテーブル（＝最新回の結果）だけを探す
        for table in soup.find_all('table'):
            text = table.get_text()
            if '本数字' in text and '1等' in text:
                # 最新回のテーブルが見つかったら、その中だけでキャリーオーバーを探す
                if 'キャリーオーバー' in text:
                    for tr in table.find_all('tr'):
                        if 'キャリーオーバー' in tr.get_text():
                            tds = tr.find_all('td')
                            if tds:
                                val = tds[-1].get_text(strip=True)
                                if val and "0円" not in val:
                                    return f"💰 キャリーオーバー発生中！ ({val})"
                
                # 最新テーブルを調べ終わったら、過去のテーブルは見ずに即終了する（誤飲防止）
                break
    except Exception as e:
        print(f"⚠️ キャリーオーバー取得エラー: {e}")
        
    return "キャリーオーバー：なし"

def generate_auto_result_news():
    """JSONBinの履歴(インデックス1＝最新の確定結果)を確認し、抽選速報を自動作成する"""
    auto_news = []
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # ロト7の速報
    l7_history = fetch_history_from_jsonbin(os.environ.get("JSONBIN_BIN_ID_LOTO7"))
    if l7_history and len(l7_history) > 1 and l7_history[1].get('status') == 'finished':
        latest = l7_history[1]
        kai_str = latest['target_kai']
        kai_num = re.search(r'\d+', kai_str).group().zfill(4) if re.search(r'\d+', kai_str) else "0000"
        carryover = get_carryover("loto7")
        auto_news.append({
            "date": today_str,
            "tag": "result",
            "title": f"【速報】ロト7 {kai_str} 抽選結果とAI予想成績",
            "content": f"ロト7 {kai_str} の抽選結果が発表されました！\n当サイトのAI予想成績は【{latest.get('best_result', '----')}】です。\n\n{carryover}\n\n詳細な出目分析とすべての予想結果は、以下のアーカイブページよりご確認ください。",
            "archive_link": f"../archive/loto7_{kai_num}.html",
            "unique_id": f"loto7_{kai_num}" # 重複生成防止用のID
        })

    # ロト6の速報
    l6_history = fetch_history_from_jsonbin(os.environ.get("JSONBIN_BIN_ID"))
    if l6_history and len(l6_history) > 1 and l6_history[1].get('status') == 'finished':
        latest = l6_history[1]
        kai_str = latest['target_kai']
        kai_num = re.search(r'\d+', kai_str).group().zfill(4) if re.search(r'\d+', kai_str) else "0000"
        carryover = get_carryover("loto6")
        auto_news.append({
            "date": today_str,
            "tag": "result",
            "title": f"【速報】ロト6 {kai_str} 抽選結果とAI予想成績",
            "content": f"ロト6 {kai_str} の抽選結果が発表されました！\n当サイトのAI予想成績は【{latest.get('best_result', '----')}】です。\n\n{carryover}\n\n詳細な出目分析とすべての予想結果は、以下のアーカイブページよりご確認ください。",
            "archive_link": f"../archive/loto6_{kai_num}.html",
            "unique_id": f"loto6_{kai_num}"
        })

    # ナンバーズの速報
    nm_history = fetch_history_from_jsonbin(os.environ.get("JSONBIN_BIN_ID_NUMBERS"))
    if nm_history and len(nm_history) > 1 and nm_history[1].get('status') == 'finished':
        latest = nm_history[1]
        kai_str = latest['target_kai']
        kai_num = re.search(r'\d+', kai_str).group().zfill(4) if re.search(r'\d+', kai_str) else "0000"
        auto_news.append({
            "date": today_str,
            "tag": "result",
            "title": f"【速報】ナンバーズ {kai_str} 抽選結果とAI予想成績",
            "content": f"ナンバーズ {kai_str} の抽選結果が発表されました！\n\n・ナンバーズ4 AI成績：【{latest.get('result_n4', '----')}】\n・ナンバーズ3 AI成績：【{latest.get('result_n3', '----')}】\n\n詳細な出目分析とすべての予想結果は、以下のアーカイブページよりご確認ください。",
            "archive_link": f"../archive/numbers_{kai_num}.html",
            "unique_id": f"numbers_{kai_num}"
        })

    return auto_news

def build_news_html():
    print("🔄 NEWS・速報ページを生成中...")
    
    manual_news = fetch_microcms_news()
    auto_news = generate_auto_result_news()

    all_news = manual_news + auto_news
    all_news.sort(key=lambda x: x["date"], reverse=True)

    news_items_html = ""
    os.makedirs("news", exist_ok=True) 

    for item in all_news:
        date_str = item["date"].replace("-", "/")
        
        safe_title = item["title"].replace(" ", "_").replace("：", "_").replace("！", "")
        file_id = item.get("unique_id", f"{hash(safe_title) % 10000}")
        file_name = f"news_{item['date']}_{item['tag']}_{file_id}.html"
        file_path = os.path.join("news", file_name)
        
        if item["tag"] == "win":
            tag_html = '<span style="background: #ef4444; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; display: inline-block; box-shadow: 0 2px 4px rgba(239,68,68,0.3); animation: pulse 2s infinite;">🎯 的中速報</span>'
            border_color = "#fecaca"
            bg_color = "#fff1f2"
        elif item["tag"] == "result":
            tag_html = '<span style="background: #8b5cf6; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; display: inline-block;">🔔 抽選結果</span>'
            border_color = "#ddd6fe"
            bg_color = "#f5f3ff"
        elif item["tag"] == "update":
            tag_html = '<span style="background: #3b82f6; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; display: inline-block;">✨ アップデート</span>'
            border_color = "#bfdbfe"
            bg_color = "#eff6ff"
        else:
            tag_html = '<span style="background: #10b981; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; display: inline-block;">📢 お知らせ</span>'
            border_color = "#bbf7d0"
            bg_color = "#f0fdf4"

        news_items_html += f"""
        <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 20px; margin-bottom: 20px; display: flex; flex-direction: column; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px dashed {border_color}; padding-bottom: 10px; margin-bottom: 15px;">
                {tag_html}
                <span style="color: #64748b; font-size: 14px; font-weight: bold;">{date_str}</span>
            </div>
            <h3 style="margin: 0 0 10px 0; font-size: 18px;">
                <a href="news/{file_name}" style="color: #1e293b; text-decoration: none;">{item["title"]} ＞</a>
            </h3>
            <p style="margin: 0; color: #475569; font-size: 15px; line-height: 1.6; white-space: pre-wrap;">{item["content"][:60]}...</p>
        </div>
        """

        # 個別ページの生成
        if not os.path.exists(file_path):
            generate_single_news_page(item, file_path, date_str, tag_html, bg_color, border_color)

    if not news_items_html:
        news_items_html = "<p style='text-align: center; color: #64748b; padding: 30px;'>現在お知らせはありません。</p>"

    # === ▼ 欠落していた news.html 本体を生成するコード ▼ ===
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="google-site-verification" content="j3Smi9nkNu6GZJ0TbgFNi8e_w9HwUt_dGuSia8RDX3Y" />
    <title>NEWS・的中速報 | ロト＆ナンバーズ攻略局🎯</title>
    <link rel="icon" type="image/png" href="favicon.icon.png">
    <link rel="apple-touch-icon" href="favicon.icon.png">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; line-height: 1.6; }}
        header {{ background-color: #1e3a8a; padding: 10px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #1e3a8a; padding: 14px 15px; font-size: 15px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; transition: all 0.3s; }}
        nav a.active {{ border-bottom: 3px solid #1e3a8a; color: #1e3a8a; }}
        nav a:hover {{ background-color: #f0f4f8; }}
        .container {{ max-width: 800px; margin: 30px auto; padding: 0 20px; }}
        footer {{ background-color: #1e293b; color: #94a3b8; text-align: center; padding: 40px 20px; margin-top: 60px; font-size: 13px; border-top: 4px solid #3b82f6; }}
        .footer-links {{ margin-bottom: 15px; }}
        .footer-links a {{ color: #cbd5e1; text-decoration: none; margin: 0 10px; transition: color 0.2s; }}
        .footer-links a:hover {{ color: white; text-decoration: underline; }}
        .ad-pc {{ display: block; }} .ad-sp {{ display: none; }}
        @media (max-width: 600px) {{ 
            .ad-pc {{ display: none; }} .ad-sp {{ display: block; }} 
            nav {{ padding: 0 2px; }}
            nav a {{ font-size: 12px; padding: 10px 5px; letter-spacing: -0.5px; }}
        }}
    </style>
</head>
<body>
    <header>
        <a href="index.html" style="text-decoration: none;">
            <img src="Lotologo001.png" alt="宝くじ当選予想・データ分析ポータル" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">NEWS・的中速報</div>
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
        <h1 style="color: #1e3a8a; text-align: center; border-bottom: 3px solid #1e3a8a; padding-bottom: 10px; margin-bottom: 30px;">📰 NEWS・お知らせ一覧</h1>
        
        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <div class="ad-pc">{imobile_ad2_pc}</div>
            <div class="ad-sp">{imobile_ad2_sp}</div>
        </div>

        {news_items_html}

        <div style="text-align: center; margin: 30px 0;">
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

    # 広告の置換処理
    html = html.replace("{imobile_ad2_pc}", imobile_ad2_pc)
    html = html.replace("{imobile_ad2_sp}", imobile_ad2_sp)
    html = html.replace("{imobile_ad3_pc}", imobile_ad3_pc)
    html = html.replace("{imobile_ad3_sp}", imobile_ad3_sp)
    html = html.replace("{imobile_overlay}", imobile_overlay)

    with open("news.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ NEWS一覧ページ(news.html)の生成が完了しました！")

