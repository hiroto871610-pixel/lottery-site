import os
import datetime
import random
import requests
import urllib.request
import base64
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import time

# 環境変数の読み込み
load_dotenv()

# =========================================================
# 星座と占いテキストのデータ定義
# =========================================================
ZODIACS = [
    {"name": "牡羊座", "date": "3/21〜4/19", "emoji": "♈"},
    {"name": "牡牛座", "date": "4/20〜5/20", "emoji": "♉"},
    {"name": "双子座", "date": "5/21〜6/21", "emoji": "♊"},
    {"name": "蟹座",   "date": "6/22〜7/22", "emoji": "♋"},
    {"name": "獅子座", "date": "7/23〜8/22", "emoji": "♌"},
    {"name": "乙女座", "date": "8/23〜9/22", "emoji": "♍"},
    {"name": "天秤座", "date": "9/23〜10/23", "emoji": "♎"},
    {"name": "蠍座",   "date": "10/24〜11/22", "emoji": "♏"},
    {"name": "射手座", "date": "11/23〜12/21", "emoji": "♐"},
    {"name": "山羊座", "date": "12/22〜1/19", "emoji": "♑"},
    {"name": "水瓶座", "date": "1/20〜2/18", "emoji": "♒"},
    {"name": "魚座",   "date": "2/19〜3/20", "emoji": "♓"}
]

# ランキング順位に応じた「もっともらしい」占い文章
FORTUNE_TEXTS = {
    "excellent": [ # 1位〜3位用
        "これまでの努力が実を結び、素晴らしい成果を手にする一日です。",
        "直感が冴え渡っています！迷っていた決断を下すのに最高のタイミングです。",
        "新しいことに挑戦すると大きな運気を引き寄せます。宝くじの購入も吉！"
    ],
    "good": [ # 4位〜8位用
        "穏やかで落ち着いた一日になるでしょう。自分のペースを守ることが鍵です。",
        "周囲とのコミュニケーションから思わぬヒントが得られそうです。",
        "小さなラッキーが重なる予感。直感を信じて行動してみましょう。"
    ],
    "caution": [ # 9位〜12位用
        "少し疲れが出やすいかもしれません。無理をせず、休息を意識してください。",
        "思い込みでの行動は避けて、慎重な確認を心がけるとトラブルを防げます。",
        "焦りは禁物です。今日はリラックスして、次のチャンスに備える充電期間にしましょう。"
    ]
}

LOTTERY_TYPES = ["ロト7", "ロト6", "ナンバーズ4", "ナンバーズ3", "ビンゴ5"]

# =========================================================
# 日替わりの占いデータを生成する関数
# =========================================================
def generate_daily_horoscope():
    today = datetime.date.today()
    date_str = f"{today.year}年{today.month}月{today.day}日"
    
    # 今日の日付をシード値にすることで、1日中同じランキング結果を保持する
    seed = today.toordinal()
    random.seed(seed)
    
    # 星座をシャッフルしてランキングを作成
    ranking = list(ZODIACS)
    random.shuffle(ranking)
    
    daily_data = []
    for i, zodiac in enumerate(ranking):
        rank = i + 1
        
        # 順位に応じたステータスとテキストを割り当て
        if rank <= 3:
            status_type = "excellent"
            stars = "★★★★★"
            money = random.choice([5, 4])
            work = random.choice([5, 4])
            love = random.choice([5, 4])
        elif rank <= 8:
            status_type = "good"
            stars = "★★★☆☆"
            money = random.choice([4, 3, 2])
            work = random.choice([4, 3, 2])
            love = random.choice([4, 3, 2])
        else:
            status_type = "caution"
            stars = "★★☆☆☆"
            money = random.choice([3, 2, 1])
            work = random.choice([3, 2, 1])
            love = random.choice([3, 2, 1])
            
        text = random.choice(FORTUNE_TEXTS[status_type])
        lucky_num = random.randint(0, 9)
        
        daily_data.append({
            "rank": rank,
            "name": zodiac["name"],
            "date": zodiac["date"],
            "emoji": zodiac["emoji"],
            "text": text,
            "lucky_num": lucky_num,
            "stars": stars,
            "money": "★" * money + "☆" * (5 - money),
            "work": "★" * work + "☆" * (5 - work),
            "love": "★" * love + "☆" * (5 - love)
        })
        
    return date_str, daily_data

# =========================================================
# HTML生成関数
# =========================================================
def build_html(date_str, daily_data):
    print("🔄 星座占いページの生成を開始...")
    
    # --- ランキング部分のHTMLを構築 ---
    ranking_html = ""
    for item in daily_data:
        # 順位による装飾の変更
        if item['rank'] == 1:
            crown = "🥇"
            border_color = "#fbbf24"
            bg_color = "#fefce8"
        elif item['rank'] == 2:
            crown = "🥈"
            border_color = "#94a3b8"
            bg_color = "#f8fafc"
        elif item['rank'] == 3:
            crown = "🥉"
            border_color = "#b45309"
            bg_color = "#fffbeb"
        else:
            crown = f"{item['rank']}位"
            border_color = "#e2e8f0"
            bg_color = "#ffffff"

        ranking_html += f"""
        <div class="ranking-card" style="border-left: 6px solid {border_color}; background-color: {bg_color};">
            <div class="rank-header">
                <div class="rank-title">{crown} {item['emoji']} {item['name']}</div>
                <div class="lucky-number">ラッキーナンバー: <span>{item['lucky_num']}</span></div>
            </div>
            <p class="fortune-text">{item['text']}</p>
            <div class="fortune-stats">
                <div class="stat-item">💰 金運: <span style="color: #ea580c;">{item['money']}</span></div>
                <div class="stat-item">💼 仕事運: <span style="color: #2563eb;">{item['work']}</span></div>
                <div class="stat-item">💖 恋愛運: <span style="color: #e11d48;">{item['love']}</span></div>
            </div>
        </div>
        """

    # --- HTML全体 ---
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>【毎日更新】タロット＆12星座占い×宝くじ | ロト＆ナンバーズ攻略局</title>
    <meta name="description" content="本日の12星座占いランキングと、あなたの生年月日から導く今日のラッキーナンバー・おすすめ宝くじを無料診断！">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; padding: 15px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ color: #1e3a8a; padding: 15px 20px; text-decoration: none; font-weight: bold; border-bottom: 3px solid transparent; transition: all 0.3s; }}
        nav a.active {{ border-bottom: 3px solid #8b5cf6; color: #8b5cf6; background-color: #f5f3ff; }}
        nav a:hover {{ background-color: #f0f4f8; }}

        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #4c1d95; border-bottom: 2px solid #ede9fe; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; display: flex; align-items: center; }}

        /* ▼▼▼ 生年月日＆タロット占いの演出用CSS ▼▼▼ */
        .tarot-area {{ text-align: center; background: linear-gradient(135deg, #1e1b4b, #4c1d95); color: white; padding: 40px 20px; border-radius: 12px; box-shadow: inset 0 0 20px rgba(0,0,0,0.5); }}
        .input-group {{ margin-bottom: 20px; }}
        input[type="date"] {{ padding: 12px; font-size: 16px; border-radius: 8px; border: none; outline: none; }}
        .btn-divination {{ background: linear-gradient(135deg, #fbbf24, #d97706); color: white; border: none; padding: 15px 40px; font-size: 18px; border-radius: 30px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 10px rgba(217, 119, 6, 0.4); transition: transform 0.2s; }}
        .btn-divination:hover {{ transform: scale(1.05); }}
        
        .card-scene {{ perspective: 1000px; width: 220px; height: 340px; margin: 20px auto; display: none; }}
        .card {{ width: 100%; height: 100%; transition: transform 1s cubic-bezier(0.175, 0.885, 0.32, 1.275); transform-style: preserve-3d; position: relative; }}
        .card.is-flipped {{ transform: rotateY(180deg); }}
        .card.is-shaking {{ animation: shake 0.5s infinite; }}
        @keyframes shake {{ 0% {{transform: translate(1px, 1px) rotate(0deg);}} 50% {{transform: translate(-1px, 2px) rotate(-1deg);}} 100% {{transform: translate(1px, -2px) rotate(1deg);}} }}
        
        .card-face {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 15px; box-shadow: 0 10px 20px rgba(0,0,0,0.3); border: 2px solid #fbbf24; }}
        .card-front {{ background: repeating-linear-gradient(45deg, #312e81, #312e81 10px, #1e1b4b 10px, #1e1b4b 20px); display: flex; align-items: center; justify-content: center; }}
        .card-front::after {{ content: '🔮'; font-size: 60px; }}
        .card-back {{ background: #ffffff; transform: rotateY(180deg); color: #333; padding: 15px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }}
        .result-title {{ font-size: 18px; color: #4c1d95; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #ede9fe; padding-bottom: 5px; }}
        .result-number {{ font-size: 40px; color: #e11d48; font-weight: bold; margin: 10px 0; }}
        .result-loto {{ font-size: 16px; background: #f0fdf4; color: #16a34a; padding: 5px 10px; border-radius: 8px; font-weight: bold; }}

        /* ▼▼▼ ランキング用CSS ▼▼▼ */
        .ranking-card {{ padding: 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }}
        .rank-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #cbd5e1; padding-bottom: 10px; margin-bottom: 10px; flex-wrap: wrap; gap: 10px; }}
        .rank-title {{ font-size: 20px; font-weight: bold; color: #1e293b; }}
        .lucky-number {{ background: #fee2e2; color: #be123c; padding: 5px 15px; border-radius: 20px; font-size: 14px; font-weight: bold; }}
        .lucky-number span {{ font-size: 20px; }}
        .fortune-text {{ font-size: 15px; color: #475569; line-height: 1.6; }}
        .fortune-stats {{ display: flex; gap: 15px; flex-wrap: wrap; margin-top: 10px; font-size: 14px; background: white; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0; }}
        .stat-item {{ font-weight: bold; }}

        footer {{ background-color: #1e293b; color: #94a3b8; text-align: center; padding: 40px 20px; margin-top: 60px; font-size: 13px; border-top: 4px solid #3b82f6; }}
    </style>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1431683156739681" crossorigin="anonymous"></script>
</head>
<body>
    <header>
        <a href="index.html" style="text-decoration: none;">
            <img src="Lotologo001.png" alt="ロト＆ナンバーズ攻略局🎯完全無料のAI予想" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">今日の星座占い＆宝くじ</div>
        </a>
    </header>

    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="horoscope.html" class="active">占い🔮</a>
    </nav>

    <div class="container">
        <div class="tarot-area">
            <h2 style="margin-top: 0; color: #fbbf24;">🌟 生年月日×タロット 宝くじ診断</h2>
            <p style="font-size: 14px; margin-bottom: 20px; color: #e2e8f0;">生年月日を入力して、今日のあなたにピッタリの「宝くじ」と「ラッキーナンバー」を導き出します。</p>
            
            <div id="input-section" class="input-group">
                <input type="date" id="birthdate" required>
                <br><br>
                <button class="btn-divination" onclick="startDivination()">カードを引く</button>
            </div>

            <div class="card-scene" id="tarot-scene">
                <div class="card" id="tarot-card">
                    <div class="card-face card-front"></div>
                    <div class="card-face card-back">
                        <div class="result-title" id="res-zodiac">星座</div>
                        <div style="font-size: 12px; color: #64748b;">今日のラッキーナンバー</div>
                        <div class="result-number" id="res-num">7</div>
                        <div style="font-size: 12px; color: #64748b; margin-top: 10px;">おすすめの宝くじ</div>
                        <div class="result-loto" id="res-loto">ロト6</div>
                    </div>
                </div>
            </div>
            
            <p id="loading-text" style="display: none; color: #fbbf24; font-weight: bold; margin-top: 15px;">星の導きを読み解いています...</p>
        </div>
        
        <div style="text-align: center; margin: 25px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <script src="https://adm.shinobi.jp/s/4275e4a786993be6d30206e03ec2de0f"></script>
        </div>

        <div class="section-card">
            <h2 class="section-header"><span>👑</span> 本日（{date_str}）の12星座 運勢ランキング</h2>
            {ranking_html}
        </div>
    </div>

    <footer>
        <p>&copy; 2026 ロト＆ナンバーズ攻略局🎯完全無料のAI予想 All Rights Reserved.</p>
    </footer>

    <script>
        const lotteries = ["ロト7", "ロト6", "ナンバーズ4", "ナンバーズ3", "ビンゴ5"];
        const zodiacs = ["水瓶座","魚座","牡羊座","牡牛座","双子座","蟹座","獅子座","乙女座","天秤座","蠍座","射手座","山羊座"];
        
        function getZodiac(month, day) {{
            const dates = [20, 19, 21, 20, 21, 22, 23, 23, 23, 24, 23, 22];
            let index = month - 1;
            if (day < dates[index]) {{
                index = (index === 0) ? 11 : index - 1;
            }}
            return zodiacs[index];
        }}

        function startDivination() {{
            const dateInput = document.getElementById('birthdate').value;
            if(!dateInput) {{
                alert('生年月日を入力してください');
                return;
            }}

            const [year, month, day] = dateInput.split('-');
            const myZodiac = getZodiac(parseInt(month), parseInt(day));
            
            // 日付と生年月日からハッシュを作って、その日は同じ結果になるようにする
            const today = new Date();
            const seedStr = dateInput + today.getFullYear() + today.getMonth() + today.getDate();
            let hash = 0;
            for (let i = 0; i < seedStr.length; i++) {{
                hash = seedStr.charCodeAt(i) + ((hash << 5) - hash);
            }}
            
            const luckyNum = Math.abs(hash % 10);
            const loto = lotteries[Math.abs(hash) % lotteries.length];

            document.getElementById('res-zodiac').innerText = myZodiac;
            document.getElementById('res-num').innerText = luckyNum;
            document.getElementById('res-loto').innerText = loto;

            // 演出スタート（滞在時間をここで稼ぐ！）
            document.getElementById('input-section').style.display = 'none';
            document.getElementById('tarot-scene').style.display = 'block';
            const card = document.getElementById('tarot-card');
            const loadText = document.getElementById('loading-text');
            
            card.classList.remove('is-flipped');
            card.classList.add('is-shaking');
            loadText.style.display = 'block';

            // 3秒間揺らした後にめくる（これがアドセンス収益UPの秘訣）
            setTimeout(() => {{
                card.classList.remove('is-shaking');
                loadText.style.display = 'none';
                card.classList.add('is-flipped');
            }}, 3000);
        }}
    </script>
</body>
</html>"""

    with open('horoscope.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ 星座占いページ (horoscope.html) の生成が完了しました！")

# =========================================================
# インスタストーリーズ用の縦長画像を生成する関数
# =========================================================
def create_story_image(date_str, daily_data):
    print("🎨 Instagramストーリーズ用のランキング画像を生成中...")
    width, height = 1080, 1920
    
    # 濃い青ベースの背景を作成（画像がなくても動くようにPythonで直接描画）
    img = Image.new('RGB', (width, height), (30, 58, 138))
    draw = ImageDraw.Draw(img)
    
    # フォントの準備
    font_path = "NotoSansJP-Bold.ttf"
    if not os.path.exists(font_path):
        font_url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/static/NotoSansJP-Bold.ttf"
        urllib.request.urlretrieve(font_url, font_path)

    font_title = ImageFont.truetype(font_path, 80)
    font_date = ImageFont.truetype(font_path, 60)
    font_rank = ImageFont.truetype(font_path, 100)
    font_desc = ImageFont.truetype(font_path, 50)
    
    # タイトルと日付
    draw.text((80, 150), f"本日の星座占いランキング", font=font_title, fill=(255, 255, 255))
    draw.text((80, 250), f"{date_str}", font=font_date, fill=(253, 224, 71)) # 黄色
    
    # トップ3の描画
    y_offset = 450
    colors = [(251, 191, 36), (148, 163, 184), (180, 83, 9)] # 金、銀、銅
    
    for i in range(3):
        zodiac = daily_data[i]
        rank_str = f"第{i+1}位"
        
        # カード風の枠を描く
        draw.rounded_rectangle([60, y_offset, 1020, y_offset + 300], radius=20, fill=(255, 255, 255))
        
        # 順位と星座名
        draw.text((100, y_offset + 50), f"{rank_str}", font=font_rank, fill=colors[i])
        draw.text((400, y_offset + 50), f"{zodiac['name']}", font=font_rank, fill=(30, 58, 138))
        
        # ラッキーナンバーと運勢の星
        desc = f"ラッキーナンバー: {zodiac['lucky_num']}  /  金運: {zodiac['money'][:3]}"
        draw.text((100, y_offset + 200), desc, font=font_desc, fill=(71, 85, 105))
        
        y_offset += 350

    # 誘導テキスト
    promo_text = "4位以降のランキングと\nタロット宝くじ診断は\nプロフィールのリンクから！"
    draw.multiline_text((width/2, 1650), promo_text, font=font_title, fill=(253, 224, 71), align="center", anchor="ma")
    
    output_path = "story_horoscope.jpg"
    img.save(output_path, "JPEG", quality=95)
    print(f"✅ ストーリーズ画像 ({output_path}) の生成が完了しました！")
    return output_path

# =========================================================
# 画像アップロードとInstagram Storiesへの自動投稿
# =========================================================
def upload_image_to_server(image_path):
    url = "https://freeimage.host/api/1/upload"
    print("☁️ 画像をサーバーにアップロード中...")
    try:
        with open(image_path, "rb") as file:
            b64_image = base64.b64encode(file.read()).decode('utf-8')
            
        payload = {
            "key": "6d207e02198a847aa98d0a2a901485a5",
            "action": "upload",
            "source": b64_image,
            "format": "json"
        }
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            image_url = res.json()["image"]["url"]
            print(f"✅ 画像URL化成功: {image_url}")
            return image_url
    except Exception as e:
        print(f"❌ アップロードエラー: {e}")
    return None

def post_story_to_instagram(image_url):
    """Instagram Graph API を使ってストーリーズに直接投稿する"""
    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    
    if not ig_account_id or not access_token:
        print("⚠️ InstagramのAPIキーが設定されていないため、ストーリーズ投稿をスキップしました。")
        return

    # 【ステップ1】メディアコンテナの作成 (STORIES を指定)
    container_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
    payload = {
        'image_url': image_url,
        'media_type': 'STORIES', # ★ストーリーズ専用のパラメータ！
        'access_token': access_token
    }
    
    print("☁️ Instagram ストーリーズへのコンテナ作成をリクエスト中...")
    res = requests.post(container_url, data=payload)
    data = res.json()
    
    if 'id' not in data:
        print(f"❌ コンテナ作成エラー (Stories投稿非対応アカウントの可能性あり): {data}")
        # もしStories専用APIが弾かれた場合のフォールバック（通常のフィード投稿にする）
        print("⚠️ 通常のフィード投稿（画像）としてリトライします...")
        payload.pop('media_type')
        payload['caption'] = "本日の星座占いランキングトップ3！続きはプロフィールのリンクから！🔮✨"
        res = requests.post(container_url, data=payload)
        data = res.json()
        if 'id' not in data:
            print("❌ 通常投稿への切り替えも失敗しました。")
            return

    creation_id = data['id']
    
    # サーバーの処理を少し待つ
    time.sleep(10)
    
    # 【ステップ2】公開 (Publish)
    publish_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
    pub_payload = {
        'creation_id': creation_id,
        'access_token': access_token
    }
    print("☁️ ストーリーズを公開中...")
    pub_res = requests.post(publish_url, data=pub_payload)
    pub_data = pub_res.json()
    
    if 'id' in pub_data:
        print("🎉🎉🎉 Instagram ストーリーズへの自動投稿が完了しました！ 🎉🎉🎉")
    else:
        print(f"❌ ストーリーズ公開エラー: {pub_data}")

# =========================================================
# メイン処理
# =========================================================
if __name__ == "__main__":
    # 1. 占いの生成
    date_str, daily_data = generate_daily_horoscope()
    
    # 2. HTMLの出力
    build_html(date_str, daily_data)
    
    # 3. インスタストーリーズ用画像の生成
    image_path = create_story_image(date_str, daily_data)
    
    # 4. 画像をURL化してInstagramにストーリーズ投稿
    image_url = upload_image_to_server(image_path)
    if image_url:
        post_story_to_instagram(image_url)