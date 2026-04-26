import os
import time
import json
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 🎨 サムネイル自動生成職人
# ==========================================
def create_thumbnail():
    print("🎨 YouTube用のサムネイル画像を生成中...")
    width, height = 1280, 720
    thumbnail_path = "weekly_thumbnail.jpg"
    
    # 背景を紺色のグラデーション風に（1280x720のキャンバス）
    img = Image.new('RGB', (width, height), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    # フォントの準備
    font_path = "assets/font.ttf"
    try:
        font_huge = ImageFont.truetype(font_path, 110)
        font_large = ImageFont.truetype(font_path, 80)
        font_medium = ImageFont.truetype(font_path, 60)
    except:
        font_huge = font_large = font_medium = ImageFont.load_default()

    def draw_text_with_outline(d, x, y, text, font, fill_color, outline_color=(0,0,0), outline_width=5):
        for adj_x in range(-outline_width, outline_width+1):
            for adj_y in range(-outline_width, outline_width+1):
                d.text((x+adj_x, y+adj_y), text, font=font, fill=outline_color)
        d.text((x, y), text, font=font, fill=fill_color)

    def draw_centered(d, y, text, font, fill_color, outline_color=(0,0,0)):
        bbox = d.textbbox((0, 0), text, font=font)
        x = (width - (bbox[2] - bbox[0])) / 2
        draw_text_with_outline(d, x, y, text, font, fill_color, outline_color)

    # 今週の日付（月曜〜金曜）を計算してサムネイルに入れる
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    friday = monday + timedelta(days=4)
    date_str = f"{monday.month}月{monday.day}日 〜 {friday.month}月{friday.day}日"

    # テキストの描画
    draw_centered(draw, 80, "＼ 1週間データまとめ ／", font_large, (56, 189, 248))
    draw_centered(draw, 220, "ロト＆ナンバーズ", font_huge, (255, 255, 255))
    draw_centered(draw, 360, "AI予想 答え合わせ", font_huge, (250, 204, 21))
    draw_centered(draw, 520, f"【 {date_str} 】", font_medium, (52, 211, 153))
    
    # 派手な帯の装飾
    draw.rectangle([0, 640, width, 720], fill=(220, 38, 38))
    draw_centered(draw, 645, "HOT＆COLD分析グラフも完全公開中！", font_medium, (255, 255, 255))

    img.save(thumbnail_path, "JPEG", quality=95)
    print(f"✅ サムネイル作成完了: {thumbnail_path}")
    return thumbnail_path

# ==========================================
# 💬 固定コメント職人
# ==========================================
def add_pinned_comment(youtube, video_id, comment_text):
    print(f"💬 動画(ID:{video_id})に固定コメントを追加中...")
    try:
        # 1. コメントを投稿する
        comment_res = youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": comment_text}
                    }
                }
            }
        ).execute()
        
        # 2. そのコメントを一番上に「固定」する
        comment_id = comment_res['snippet']['topLevelComment']['id']
        youtube.comments().setModerationStatus(
            id=comment_id,
            moderationStatus="published",
            ban=False
        ).execute()
        print("✅ 固定コメントの設置が完了しました！")
    except Exception as e:
        print(f"⚠️ コメント固定エラー（動画処理が間に合っていない可能性があります）: {e}")

# ==========================================
# 🚀 YouTubeアップロード本処理
# ==========================================
def upload_long_video():
    video_path = "weekly_summary.mp4"
    if not os.path.exists(video_path):
        print(f"❌ 動画ファイルが見つかりません: {video_path}")
        return

    # サムネイルを自動生成
    thumbnail_path = create_thumbnail()

    print("🎥 YouTubeへ長尺動画のアップロードを開始します...")
    token_str = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not token_str:
        print("❌ YOUTUBE_TOKEN_JSONが設定されていません。")
        return
        
    try:
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        youtube = build('youtube', 'v3', credentials=creds)
        
        # 今週の日付（月曜〜金曜）を計算
        now = datetime.now()
        monday = now - timedelta(days=now.weekday())
        friday = monday + timedelta(days=4)
        title_date = f"{monday.month}月{monday.day}日〜{friday.month}月{friday.day}日"

        # メタデータ（タイトル・概要欄・タグ）
        title = f"【{title_date}】ロト6・ロト7・ナンバーズ AI予想と結果まとめ！HOT＆COLD分析"
        
        description = (
            f"今週（{title_date}）の宝くじ（ロト6・ロト7・ナンバーズ3・ナンバーズ4）の抽選結果と、"
            "当サイトの完全無料AI予想の答え合わせを一挙公開！\n\n"
            "🎯 次回の最新AI予想（完全無料）はこちらから！\n"
            "👉 https://loto-yosou-ai.com/\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔥 【厳選】おすすめサービス\n"
            f"💰 忙しい方に！宝くじの購入代行はこちら\n👉 {link_buy}\n"
            f"✨ 運気を味方に！最強の開運アイテムをチェック\n👉 {link_lucky}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📈 動画の後半では、直近データに基づいた【HOT＆COLD数字の分析】や"
            "【合計値トレンドグラフ】も特別公開しています。\n\n"
            "毎週土曜日に1週間のまとめ動画を配信中！\n"
            "最新情報を見逃さないよう、ぜひ【チャンネル登録】と【高評価】をお願いします✨\n\n"
            "#ロト6 #ロト7 #ナンバーズ4 #ナンバーズ3 #宝くじ #AI予想"
        )
        
        tags = ["ロト6", "ロト7", "ナンバーズ4", "ナンバーズ3", "宝くじ", "AI予想", "データ分析", "宝くじ 当たる"]

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '24' # 24 = エンターテイメント
            },
            'status': {
                'privacyStatus': 'public', # ★ public(公開)
                'selfDeclaredMadeForKids': False
            }
        }
        
        # ▼ 動画のアップロード（chunksizeを利用して大容量ファイルでも安全に送る）
        media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True, mimetype='video/mp4')
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"🔼 アップロード中... {int(status.progress() * 100)}%")

        video_id = response.get('id')
        print(f"🎉 動画のアップロード成功！ URL: https://youtu.be/{video_id}")

        # ▼ サムネイルのアップロード設定
        if thumbnail_path and os.path.exists(thumbnail_path):
            print("🖼️ サムネイル画像を動画に設定中...")
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype='image/jpeg')
            ).execute()
            print("✅ サムネイルの設定完了！")

        # YouTube側で動画の処理が始まるまで少し待機（固定コメントを弾かれないための安全マージン）
        print("⏳ YouTube側の処理を待つため、15秒待機します...")
        time.sleep(15)
        
        # ▼ 固定コメントの追加
        fixed_msg = (
            "🎯 サイトでは次回の『ロト＆ナンバーズ 最新AI予想』を完全無料で公開しています！\n"
            "スマホから今すぐチェック👇\n"
            "https://loto-yosou-ai.com/\n\n"
            "💰 宝くじの購入が面倒な方はこちら（購入代行）\n"
            f"👉 {link_buy}\n\n"
            "次回の動画も見逃さないよう、チャンネル登録をお願いします✨"
        )
        add_pinned_comment(youtube, video_id, fixed_msg)
        
        print("🚀🚀🚀 YouTubeへの全自動投稿フローが完璧に完了しました！ 🚀🚀🚀")
        
    except Exception as e:
        print(f"❌ YouTubeアップロード中にエラーが発生しました: {e}")

if __name__ == "__main__":
    upload_long_video()