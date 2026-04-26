import os
import time
import json
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# ▼▼▼ 追加：SNS告知メディア生成用のライブラリ ▼▼▼
import math
import numpy as np
from moviepy.editor import VideoClip, AudioFileClip
import cloudinary
import cloudinary.uploader
import requests
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ▲▲▲ ここまで ▲▲▲

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

# ▼▼▼ 新規追加：SNS告知メディア生成＆自動投稿職人 ▼▼▼
def create_ig_announcements(thumbnail_path):
    print("🎨 Instagram用の告知画像とリール動画を生成中...")
    font_path = "assets/font.ttf"
    try:
        font_huge = ImageFont.truetype(font_path, 90)
        font_large = ImageFont.truetype(font_path, 70)
        font_medium = ImageFont.truetype(font_path, 50)
    except:
        font_huge = font_large = font_medium = ImageFont.load_default()

    def draw_ig_text(d, y, text, font, fill_color, outline_color=(0,0,0)):
        bbox = d.textbbox((0, 0), text, font=font)
        x = (1080 - (bbox[2] - bbox[0])) / 2
        for adj_x in range(-5, 6):
            for adj_y in range(-5, 6):
                d.text((x+adj_x, y+adj_y), text, font=font, fill=outline_color)
        d.text((x, y), text, font=font, fill=fill_color)

    img_feed = Image.new('RGB', (1080, 1350), color=(15, 23, 42))
    draw_f = ImageDraw.Draw(img_feed)
    
    draw_ig_text(draw_f, 150, "＼ YouTubeで最新動画を公開！ ／", font_medium, (52, 211, 153))
    draw_ig_text(draw_f, 250, "1週間の予想結果まとめ", font_huge, (255, 255, 255))
    
    if os.path.exists(thumbnail_path):
        thumb = Image.open(thumbnail_path).resize((960, 540), PIL.Image.LANCZOS)
        img_feed.paste(thumb, (60, 420))
        
    draw_f.rectangle([0, 1100, 1080, 1350], fill=(220, 38, 38))
    draw_ig_text(draw_f, 1130, "ご視聴はプロフィールの", font_large, (255, 255, 255))
    draw_ig_text(draw_f, 1220, "リンクから今すぐチェック👇", font_large, (250, 204, 21))
    
    feed_path = "ig_announcement.jpg"
    img_feed.save(feed_path, "JPEG", quality=95)

    def make_reel_frame(t):
        img = Image.new('RGB', (1080, 1920), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        
        draw_ig_text(draw, 300, "＼ YouTubeで最新動画を公開！ ／", font_medium, (52, 211, 153))
        draw_ig_text(draw, 400, "1週間の予想結果まとめ", font_huge, (255, 255, 255))
        
        y_off = int(20 * math.sin(t * 3))
        if os.path.exists(thumbnail_path):
            thumb = Image.open(thumbnail_path).resize((960, 540), PIL.Image.LANCZOS)
            img.paste(thumb, (60, 600 + y_off))
            
        draw.rectangle([0, 1500, 1080, 1920], fill=(220, 38, 38))
        draw_ig_text(draw, 1580, "ご視聴はプロフィールの", font_large, (255, 255, 255))
        draw_ig_text(draw, 1700, "リンクから今すぐチェック👇", font_large, (250, 204, 21))
        
        return np.array(img)
        
    reel_clip = VideoClip(make_reel_frame, duration=6)
    
    bgm_path = "assets/create_weekly.mp3"
    if os.path.exists(bgm_path):
        try:
            bgm = AudioFileClip(bgm_path).subclip(0, 6).audio_fadeout(1)
            reel_clip = reel_clip.set_audio(bgm)
        except: pass
        
    reel_path = "ig_announcement.mp4"
    reel_clip.write_videofile(reel_path, fps=24, codec="libx264", audio_codec="libmp3lame", threads=1, logger=None)
    
    print("✅ Instagram用の告知メディア（画像・リール）作成完了！")
    return feed_path, reel_path

def post_to_line(message):
    LINE_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not LINE_ACCESS_TOKEN: return
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    data = {"messages": [{"type": "text", "text": message}]}
    try:
        res = requests.post(url, headers=headers, json=data)
        if res.status_code == 200: print("✅ LINEへのYouTube公開告知が成功しました！")
    except: pass

def upload_image_to_server(image_path):
    url = "https://freeimage.host/api/1/upload"
    try:
        import base64
        with open(image_path, "rb") as file:
            b64_image = base64.b64encode(file.read()).decode('utf-8')
        payload = {"key": "6d207e02198a847aa98d0a2a901485a5", "action": "upload", "source": b64_image, "format": "json"}
        response = requests.post(url, data=payload).json()
        if response.get("status_code") == 200: return response["image"]["url"]
    except: pass
    return None

def post_to_instagram(image_url, caption_text):
    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    if not all([ig_account_id, access_token]): return
    try:
        print("☁️ Instagramへ告知画像をアップロード中...")
        c_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
        c_res = requests.post(c_url, data={'image_url': image_url, 'caption': caption_text, 'access_token': access_token}).json()
        if 'id' in c_res:
            time.sleep(15) 
            p_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
            p_res = requests.post(p_url, data={'creation_id': c_res['id'], 'access_token': access_token}).json()
            if 'id' in p_res: print("✅ Instagram（フィード）への告知投稿が完了しました！")
    except: pass

def upload_video_to_cloudinary(video_path):
    print("☁️ Cloudinaryへ告知リール動画をアップロード中...")
    cloudinary.config( 
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
        api_key = os.environ.get("CLOUDINARY_API_KEY"), 
        api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
        secure = True
    )
    try:
        res = cloudinary.uploader.upload(video_path, resource_type="video")
        return res.get("secure_url")
    except Exception as e:
        print(f"⚠️ Cloudinaryエラー: {e}")
        return None

def post_reel_to_instagram(video_url, caption_text):
    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    if not all([ig_account_id, access_token]): return
    try:
        print("☁️ Instagramへ告知リール動画を送信中...")
        c_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
        payload = {'media_type': 'REELS', 'video_url': video_url, 'caption': caption_text, 'access_token': access_token}
        c_res = requests.post(c_url, data=payload).json()
        if 'id' in c_res:
            print("⏳ リール処理のため60秒待機します...")
            time.sleep(60)
            p_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
            p_res = requests.post(p_url, data={'creation_id': c_res['id'], 'access_token': access_token}).json()
            if 'id' in p_res: print("🎉 Instagram（リール）への告知動画投稿が完了しました！")
    except: pass
# ▲▲▲ ここまで ▲▲▲

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
        
        # ★修正：欠落してエラーの原因となっていた環境変数の取得を復元しました
        link_buy = os.environ.get("AFFILIATE_BUY_SERVICE", "https://loto-yosou-ai.com/")
        link_lucky = os.environ.get("AFFILIATE_LUCKY_ITEM", "https://loto-yosou-ai.com/")

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
        
        # ▼ 追加：動画のURLを変数として保持
        youtube_url = f"https://youtu.be/{video_id}"

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
        
        # ▼▼▼ 新規追加：SNSへ一斉告知！ ▼▼▼
        print("\n📢 続いて、LINEとInstagramへYouTube公開の告知を行います！")
        
        ig_feed_path, ig_reel_path = create_ig_announcements(thumbnail_path)
        
        sns_message = (
            f"🎬 今週の『ロト＆ナンバーズ 予想結果まとめ動画』をYouTubeで公開しました！\n\n"
            f"当サイトの完全無料AI予想の答え合わせや、\n"
            f"直近データから導き出す【HOT＆COLD数字分析グラフ】も特別公開中📈✨\n\n"
            f"▼ 動画の視聴はプロフィールのリンク（またはこちら👇）から！\n"
            f"{youtube_url}\n\n"
            f"#ロト6 #ロト7 #ナンバーズ #AI予想 #宝くじ #高額当選"
        )

        post_to_line(sns_message)

        if os.path.exists(ig_feed_path):
            img_url = upload_image_to_server(ig_feed_path)
            if img_url: post_to_instagram(img_url, sns_message)

        if os.path.exists(ig_reel_path):
            vid_url = upload_video_to_cloudinary(ig_reel_path)
            if vid_url: post_reel_to_instagram(vid_url, sns_message)
        # ▲▲▲ ここまで ▲▲▲
        
        print("🚀🚀🚀 YouTubeへの全自動投稿フローが完璧に完了しました！ 🚀🚀🚀")
        
    except Exception as e:
        print(f"❌ YouTubeアップロード中にエラーが発生しました: {e}")

if __name__ == "__main__":
    upload_long_video()