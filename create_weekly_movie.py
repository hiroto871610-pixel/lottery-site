import os
import math
import requests
import re
import datetime
import numpy as np
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips
from moviepy.audio.fx.all import audio_loop
from moviepy.video.fx.all import fadein, fadeout
from dotenv import load_dotenv
from collections import Counter
from gtts import gTTS

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

load_dotenv()

# ==========================================
# 📺 まとめ動画専用：YouTubeアップロード機能
# ==========================================
def upload_weekly_to_youtube(video_path, title, description, tags):
    print("🎥 YouTubeへまとめ動画をアップロード中...")
    token_str = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not token_str:
        print("❌ YOUTUBE_TOKEN_JSONが設定されていません。")
        return None
        
    try:
        import json
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        youtube = build('youtube', 'v3', credentials=creds)
        
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '24' # エンターテイメント
            },
            'status': {
                'privacyStatus': 'public', 
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )
        response = request.execute()
        video_id = response.get('id')
        print(f"🎉🎉🎉 YouTubeへのアップロードが完了しました！ URL: https://youtu.be/{video_id}")
        return video_id
    except Exception as e:
        print(f"❌ YouTubeアップロードエラー: {e}")
        return None

# ==========================================
# 📝 archive.html 自動更新機能
# ==========================================
def update_archive_html(video_id, title, date_str):
    print("🔄 archive.html を最新の動画で更新中...")
    file_path = "archive.html"
    
    if not os.path.exists(file_path):
        print(f"❌ {file_path} が見つからないため、更新をスキップします。")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    try:
        # 新しいブロックを作成 (loading="lazy" を追加してページの読み込みを高速化)
        new_block_html = f"""
            <div class="video-card">
                <div class="video-wrapper">
                    <iframe src="https://www.youtube.com/embed/{video_id}" title="YouTube video player" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
                </div>
                <div class="video-info">
                    <h3 class="video-title">{title}</h3>
                    <span class="video-date">{date_str}</span>
                </div>
            </div>"""

        # 目印となる <div class="video-grid"> を探す
        target_tag = '<div class="video-grid">'
        if target_tag in html:
            # ターゲットタグの直後に新しい動画ブロックを挿入
            new_html = html.replace(target_tag, target_tag + "\n" + new_block_html, 1)
            
            # 古い動画を削除（最新12個＝約3ヶ月分だけ残す設定）
            # <div class="video-card"> の数を数えて、13個目以降を消す簡単な処理を追加
            import re
            cards = re.findall(r'<div class="video-card">.*?</div>\s*</div>\s*</div>', new_html, re.DOTALL)
            MAX_VIDEOS = 12
            if len(cards) > MAX_VIDEOS:
                 # 古いカードのHTMLを特定して削除
                 for old_card in cards[MAX_VIDEOS:]:
                     new_html = new_html.replace(old_card, "")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_html)
            print(f"✅ archive.html を更新し、最新{MAX_VIDEOS}件に整理しました！")
        else:
            print("❌ archive.html 内に <div class=\"video-grid\"> が見つかりませんでした。")
            
    except Exception as e:
        print(f"❌ archive.htmlの更新中にエラーが発生しました: {e}")

# ==========================================
# 📸 Instagram 告知画像アップロード＆投稿機能
# ==========================================
def upload_image_to_server(image_path):
    url = "https://freeimage.host/api/1/upload"
    print("☁️ 画像をアップロードサーバー(Freeimage.host)に送信中...")
    try:
        import base64
        with open(image_path, "rb") as file:
            b64_image = base64.b64encode(file.read()).decode('utf-8')
            
        payload = {
            "key": "6d207e02198a847aa98d0a2a901485a5",
            "action": "upload",
            "source": b64_image,
            "format": "json"
        }
        response = requests.post(url, data=payload)
        result = response.json()
        
        if result.get("status_code") == 200:
            image_url = result["image"]["url"]
            print(f"✅ 画像のURL化成功: {image_url}")
            return image_url
        else:
            print(f"❌ サーバーエラー: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 画像アップロードエラー: {e}")
        return None

def post_to_instagram(image_url, caption_text):
    import time
    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    
    if not ig_account_id or not access_token:
        print("⚠️ IG_ACCOUNT_ID または IG_ACCESS_TOKEN が設定されていません。")
        return

    container_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
    container_payload = {
        'image_url': image_url,
        'caption': caption_text,
        'access_token': access_token
    }
    print("☁️ Instagramへ画像をリクエスト中...")
    container_response = requests.post(container_url, data=container_payload)
    container_data = container_response.json()
    
    if 'id' not in container_data:
        print(f"❌ コンテナ作成エラー: {container_data}")
        return
        
    creation_id = container_data['id']

    print("⏳ Instagram側の画像処理完了を15秒待ちます...")
    time.sleep(15) 
    
    publish_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
    publish_payload = {
        'creation_id': creation_id,
        'access_token': access_token
    }
    print("☁️ Instagramへ投稿を公開中...")
    publish_response = requests.post(publish_url, data=publish_payload)
    publish_data = publish_response.json()
    
    if 'id' in publish_data:
        print("🎉🎉🎉 Instagramへの告知画像投稿が完了しました！ 🎉🎉🎉")
    else:
        print(f"❌ 公開エラー: {publish_data}")
# ==========================================
# 🎵 背景動画とBGM・SEのパス
# ==========================================
BG_VIDEO_PATH = os.path.join("assets", "create_weekly.mp4")
BGM_PATH = os.path.join("assets", "create_weekly.mp3")
QR_CODE_PATH = os.path.join("assets", "qrcode.png")

bg_video = None
bgm_clip = None

FONT_PATH = "assets/font.ttf"
try:
    FONT_TITLE = ImageFont.truetype(FONT_PATH, 55)
    FONT_SUB = ImageFont.truetype(FONT_PATH, 45)
    FONT_NUM = ImageFont.truetype(FONT_PATH, 70)
    FONT_LIST = ImageFont.truetype(FONT_PATH, 50)
    FONT_HIT = ImageFont.truetype(FONT_PATH, 60)
except:
    FONT_TITLE = FONT_SUB = FONT_NUM = FONT_LIST = FONT_HIT = ImageFont.load_default()

def draw_text_with_shadow(draw, x, y, text, font, fill_color, shadow_color=(0,0,0,200)):
    draw.text((x+3, y+3), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill_color)

def draw_centered_text(draw, y, text, font, fill_color, screen_w=1920):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (screen_w - (bbox[2] - bbox[0])) / 2
    draw_text_with_shadow(draw, x, y, text, font, fill_color)

def draw_right_aligned_text(draw, right_x, y, text, font, fill_color):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw_text_with_shadow(draw, right_x - w, y, text, font, fill_color)

def draw_sphere_ball_with_bounce(draw, x, y, r, text, ball_color, t, appear_t):
    if t < appear_t: return
    progress = min(1.0, (t - appear_t) * 2.5)
    y_offset = 0
    shadow_alpha = 150
    shadow_r = r
    if progress < 1.0:
        y_offset = int(-180 * (1.0 - progress) * abs(math.cos(progress * math.pi * 2.5)))
        shadow_r = int(r * (0.6 + 0.4 * progress))
        shadow_alpha = int(150 * progress)
    draw.ellipse([x + 4, y + y_offset + 4, x + 2*shadow_r + 4, y + y_offset + 2*shadow_r + 4], fill=(0, 0, 0, shadow_alpha))
    draw.ellipse([x, y + y_offset, x + 2*r, y + y_offset + 2*r], fill=ball_color)
    inner_r, off = int(r * 0.85), int(r * 0.07)
    draw.ellipse([x + off, y + y_offset + off, x + off + 2*inner_r, y + y_offset + off + 2*inner_r], fill=tuple(min(255, c + 50) for c in ball_color))
    hl_r = int(r * 0.3)
    draw.ellipse([x + int(r*0.2), y + y_offset + int(r*0.2), x + int(r*0.2) + 2*hl_r, y + y_offset + int(r*0.2) + 2*hl_r], fill=(255, 255, 255, 200))
    bbox = draw.textbbox((0, 0), text, font=FONT_NUM)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw_text_with_shadow(draw, x + r - w / 2, y + y_offset + r - h / 2 - 10, text, FONT_NUM, (255, 255, 255))

def get_base_frame(t, tint_color=None):
    if bg_video:
        frame_t = t % bg_video.duration
        frame_img = Image.fromarray(bg_video.get_frame(frame_t)).convert('RGBA')
        frame_img = frame_img.resize((1920, 1080), PIL.Image.LANCZOS)
    else:
        frame_img = Image.new('RGBA', (1920, 1080), color=(15, 23, 42, 255))
    if tint_color:
        overlay = Image.new('RGBA', frame_img.size, tint_color)
        frame_img = Image.alpha_composite(frame_img, overlay)
    return frame_img

def apply_fade(clip, fade_duration=1.0):
    return fadeout(fadein(clip, fade_duration), fade_duration)

def cleanup_old_voice_files():
    assets_dir = "assets"
    if not os.path.exists(assets_dir): return
    print("🧹 過去のAI音声データを綺麗にお掃除しています...")
    for f in os.listdir(assets_dir):
        if f.endswith(".mp3") and (f.startswith("v_") or f.startswith("voice_")):
            try:
                os.remove(os.path.join(assets_dir, f))
            except Exception:
                pass

def get_voice_clip(text, filename, start_time):
    filepath = os.path.join("assets", filename)
    if os.path.exists(filepath):
        try: os.remove(filepath)
        except: pass
    try:
        print(f"🎙️ AI音声を生成中... ({text})")
        tts = gTTS(text=text, lang='ja')
        tts.save(filepath)
    except Exception as e:
        print(f"⚠️ 音声生成スキップ: {e}")
        return None
    if os.path.exists(filepath):
        return AudioFileClip(filepath).set_start(start_time)
    return None

def fetch_finished_history(bin_id, limit):
    api_key = os.environ.get("JSONBIN_API_KEY")
    if not bin_id or not api_key: return []
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}", headers={"X-Master-Key": api_key})
        if res.status_code == 200:
            records = []
            for r in res.json().get('record', []):
                is_loto = bool(r.get('actual_main') and r.get('actual_main') != "----")
                is_num = bool(r.get('actual_n4') and r.get('actual_n4') != "----")
                if r.get('status') == 'finished' or is_loto or is_num:
                    records.append(r)
            return records[:limit]
    except: pass
    return []

def fetch_video_db_safe(bin_id):
    api_key = os.environ.get("JSONBIN_API_KEY")
    if not bin_id or not api_key: return {}
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}", headers={"X-Master-Key": api_key})
        data = res.json().get('record', {})
        while isinstance(data, dict) and "record" in data:
            data = data["record"]
        if isinstance(data, list): return {}
        safe_db = {}
        for k, v in data.items():
            nums = re.findall(r'\d+', k)
            if nums: safe_db[str(int(nums[0]))] = v
        return safe_db
    except: return {}

def get_short_date(d_str):
    if not d_str or d_str == "----/--/--": return "----/--/--"
    m = re.search(r'\d{4}[/年]\s*(\d{1,2})[/月]\s*(\d{1,2})', d_str)
    if m: return f"{m.group(1)}月{m.group(2)}日"
    return d_str

def fetch_all_rakuten_hot_cold():
    targets = [
        ("LOTO6", "loto6", 43, 6),
        ("LOTO7", "loto7", 37, 7),
        ("NUMBERS4", "numbers4", 9, 4),
        ("NUMBERS3", "numbers3", 9, 3)
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    today = datetime.date.today()
    results = {}
    for t_name, t_url_part, max_num, pick_count in targets:
        all_nums = []
        urls = [f"https://takarakuji.rakuten.co.jp/backnumber/{t_url_part}/lastresults/"]
        for i in range(3):
            y, m = today.year, today.month - i
            if m <= 0: y, m = y - 1, m + 12
            urls.append(f"https://takarakuji.rakuten.co.jp/backnumber/{t_url_part}/{y}{m:02d}/")

        for url in urls:
            try:
                res = requests.get(url, headers=headers, timeout=5)
                if res.status_code != 200: continue
                res.encoding = 'euc-jp'
                soup = BeautifulSoup(res.content, 'html.parser')
                text = soup.get_text(separator=' ')
                for m in re.finditer(r'第\s*\d+\s*回', text):
                    chunk = text[m.end():m.end()+200]
                    date_m = re.search(r'\d{4}[/年]\d{1,2}[/月]\d{1,2}', chunk)
                    if not date_m: continue
                    num_chunk = chunk[date_m.end():]
                    digits = re.findall(r'\d+', num_chunk)
                    if "NUMBERS" in t_name:
                        for d in digits:
                            if len(d) == pick_count:
                                all_nums.extend(list(d))
                                break
                    else:
                        valid_nums = [n.zfill(2) for n in digits if 1 <= int(n) <= max_num]
                        if len(valid_nums) >= pick_count:
                            all_nums.extend(valid_nums[:pick_count])
            except: pass
        
        counts = Counter(all_nums)
        start_idx = 0 if "NUMBERS" in t_name else 1
        for i in range(start_idx, max_num + 1):
            n_str = str(i) if "NUMBERS" in t_name else str(i).zfill(2)
            if n_str not in counts: counts[n_str] = 0

        sorted_c = counts.most_common()
        results[t_name] = {"hot": sorted_c[:5], "cold": list(reversed(sorted_c))[:5]}
    return results

def create_opening_clip(start_date, end_date):
    duration = 15
    date_text = f"【 {start_date} 〜 {end_date} の予想結果 】" if start_date and end_date else "〜 今週の抽選結果とAI予想の答え合わせ 〜"
    
    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)
        alpha = int(255 * min(1.0, t / 2.0))
        
        if t > 1.0: draw_centered_text(draw, 350, "ロト＆ナンバーズ攻略局 完全無料のAI予想", FONT_TITLE, (250, 204, 21, alpha))
        if t > 3.0: draw_centered_text(draw, 500, date_text, FONT_NUM, (255, 255, 255, alpha))
        if t > 6.0: draw_centered_text(draw, 700, "ナンバーズ ＆ ロト 全データ一挙公開！", FONT_LIST, (52, 211, 153, alpha))
            
        return np.array(img.convert('RGB'))
        
    clip = VideoClip(make_frame, duration=duration)
    audio_clips = []
    if os.path.exists("assets/se_op_jingle.mp3"): audio_clips.append(AudioFileClip("assets/se_op_jingle.mp3").set_start(1.0))
    elif os.path.exists("assets/se_tada.mp3"): audio_clips.append(AudioFileClip("assets/se_tada.mp3").set_start(2.0))
        
    voice = get_voice_clip("ロトとナンバーズのAI予想、今週の結果まとめです！", "voice_op.mp3", 2.0)
    if voice: audio_clips.append(voice)
    if audio_clips: clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
    return apply_fade(clip)

def create_ending_clip():
    duration = 20
    qr_img = None
    if os.path.exists(QR_CODE_PATH):
        try:
            qr_img = Image.open(QR_CODE_PATH).convert("RGBA")
            qr_img = qr_img.resize((230, 230), PIL.Image.LANCZOS)
        except: pass

    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)
        alpha = int(255 * min(1.0, t / 2.0))
        if t > 1.0: draw_centered_text(draw, 200, "最後までご視聴ありがとうございました！", FONT_TITLE, (255, 255, 255, alpha))
        if t > 4.0:
            draw_centered_text(draw, 380, "高評価 ＆ チャンネル登録", FONT_NUM, (250, 204, 21, alpha))
            draw_centered_text(draw, 480, "よろしくお願いします！", FONT_TITLE, (250, 204, 21, alpha))
        if t > 7.0:
            draw_centered_text(draw, 680, "▼ 次回のAI予想は当サイトで完全無料公開中 ▼", FONT_LIST, (52, 211, 153, alpha))
            search_text = "🔍 ロトナンバーズ攻略局"
            draw_text_with_shadow(draw, 250, 800, search_text, FONT_NUM, (255, 255, 255, alpha))
            draw_text_with_shadow(draw, 450, 880, "で検索！", FONT_LIST, (250, 204, 21, alpha))
            
            if qr_img:
                qr_x, qr_y = 1350, 760
                img.paste(qr_img, (qr_x, qr_y), qr_img)
                text_str = "スマホでチェック！"
                bbox = draw.textbbox((0, 0), text_str, font=FONT_SUB)
                tw = bbox[2] - bbox[0]
                draw_text_with_shadow(draw, qr_x + 115 - tw / 2, 1000, text_str, FONT_SUB, (255, 255, 255, alpha))
                
        return np.array(img.convert('RGB'))
        
    clip = VideoClip(make_frame, duration=duration)
    voice = get_voice_clip("最後までご視聴ありがとうございました。チャンネル登録、よろしくお願いします！", "voice_ed.mp3", 2.0)
    if voice: clip = clip.set_audio(CompositeAudioClip([voice]).set_duration(duration))
    return apply_fade(clip)

def create_title_clip(records, title_name, main_color, voice_text, voice_file):
    duration = 10
    if not records: return None
    oldest, newest = records[-1], records[0]
    old_kai, new_kai = oldest.get('target_kai', ''), newest.get('target_kai', '')
    old_date = get_short_date(oldest.get('date', '----/--/--'))
    new_date = get_short_date(newest.get('date', '----/--/--'))

    tint_color = (0, 0, 0, 0)
    if "ロト6" in title_name: tint_color = (0, 100, 255, 40)
    elif "ロト7" in title_name: tint_color = (255, 150, 0, 40)
    elif "ナンバーズ" in title_name: tint_color = (0, 200, 100, 30)

    def make_frame(t):
        img = get_base_frame(t, tint_color)
        draw = ImageDraw.Draw(img, 'RGBA')
        box_height = 400
        box_top = (1080 - box_height) // 2
        box_width = min(1920, int(1920 * (t * 2))) 
        draw.rectangle([1920//2 - box_width//2, box_top, 1920//2 + box_width//2, box_top + box_height], fill=(0, 0, 0, 160))

        if t > 0.5:
            draw_centered_text(draw, box_top + 50, f"■ {title_name} 結果まとめ ■", FONT_TITLE, main_color)
            if old_kai == new_kai:
                draw_centered_text(draw, box_top + 180, f"{old_date} ({old_kai})", FONT_NUM, (255, 255, 255))
            else:
                draw_centered_text(draw, box_top + 150, f"{old_date} ({old_kai})", FONT_NUM, (255, 255, 255))
                draw_centered_text(draw, box_top + 240, "▼", FONT_LIST, (200, 200, 200))
                draw_centered_text(draw, box_top + 310, f"{new_date} ({new_kai})", FONT_NUM, (255, 255, 255))
        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    audio_clips = []
    if os.path.exists("assets/se_whoosh.mp3"): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(0.5))
    voice = get_voice_clip(voice_text, voice_file, 1.0)
    if voice: audio_clips.append(voice)
    if audio_clips: clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
    return apply_fade(clip)

def create_hot_cold_clip(title_name, hot, cold, main_color):
    duration = 20
    if not hot or not cold: return None
    tint_color = (255, 0, 50, 20)

    def make_frame(t):
        img = get_base_frame(t, tint_color)
        draw = ImageDraw.Draw(img)
        draw_centered_text(draw, 100, f"■ {title_name} 直近の傾向 (HOT & COLD) ■", FONT_TITLE, main_color)
        
        if t > 1.0:
            draw_centered_text(draw, 250, "【HOT】 よく出ている数字", FONT_SUB, (239, 68, 68))
            for i, (num, cnt) in enumerate(hot):
                appear_t = 1.5 + (i * 0.5)
                draw_sphere_ball_with_bounce(draw, 300 + (i * 260), 320, 65, num, (239, 68, 68), t, appear_t)
                if t > appear_t + 0.5:
                    text_str = f"{cnt}回"
                    bbox = draw.textbbox((0, 0), text_str, font=FONT_LIST)
                    tw = bbox[2] - bbox[0]
                    cx = 300 + (i * 260) + 65
                    draw_text_with_shadow(draw, cx - tw / 2, 470, text_str, FONT_LIST, (255, 255, 255))

        if t > 6.0:
            draw_centered_text(draw, 580, "【COLD】 全く出ていない数字", FONT_SUB, (14, 165, 233))
            for i, (num, cnt) in enumerate(cold):
                appear_t = 6.5 + (i * 0.5)
                draw_sphere_ball_with_bounce(draw, 300 + (i * 260), 650, 65, num, (14, 165, 233), t, appear_t)
                if t > appear_t + 0.5:
                    text_str = f"{cnt}回"
                    bbox = draw.textbbox((0, 0), text_str, font=FONT_LIST)
                    tw = bbox[2] - bbox[0]
                    cx = 300 + (i * 260) + 65
                    draw_text_with_shadow(draw, cx - tw / 2, 800, text_str, FONT_LIST, (255, 255, 255))

        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    audio_clips = []
    if os.path.exists("assets/se_don.mp3"):
        for i in range(5): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(1.5 + (i * 0.5)))
        for i in range(5): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(6.5 + (i * 0.5)))
    if audio_clips: clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
    return apply_fade(clip)

def create_trend_graph_clip(loto6_records):
    duration = 25
    targets = list(reversed(loto6_records[:10]))
    if len(targets) < 2: return None

    labels, sums = [], []
    for rec in targets:
        nums = re.findall(r'\d+', rec.get("target_kai", ""))
        labels.append(nums[0] if nums else "?")
        main_nums = [int(n) for n in rec.get("actual_main", "").split(",") if n.strip().isdigit()]
        sums.append(sum(main_nums) if main_nums else 0)

    plt.figure(figsize=(15, 7), facecolor='#0f172a')
    ax = plt.axes()
    ax.set_facecolor('#0f172a')
    bars = plt.bar(labels, sums, color='#38bdf8', edgecolor='white', linewidth=1)
    plt.title("LOTO6 Main Numbers Sum Trend", color='white', fontsize=26, pad=20)
    plt.xlabel("Round", color='#94a3b8', fontsize=18)
    ax.tick_params(colors='white', labelsize=14)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#334155')
    ax.spines['left'].set_color('#334155')
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, int(yval), ha='center', color='#facc15', fontweight='bold', fontsize=16)

    plt.tight_layout()
    graph_filename = "temp_graph.png"
    plt.savefig(graph_filename, dpi=150, transparent=True)
    plt.close()
    graph_pil = Image.open(graph_filename).convert("RGBA")

    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)
        draw_centered_text(draw, 50, "■ 直近10回 ロト6 本数字合計値トレンド ■", FONT_TITLE, (52, 211, 153))
        scale = 1.0 + 0.010 * t 
        new_w, new_h = int(graph_pil.width * scale), int(graph_pil.height * scale)
        resized_graph = graph_pil.resize((new_w, new_h), PIL.Image.LANCZOS)
        paste_x = int((1920 - new_w) / 2)
        paste_y = int((1080 - new_h) / 2) + 50
        img.paste(resized_graph, (paste_x, paste_y), resized_graph)
        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    if os.path.exists("assets/se_tada.mp3"): clip = clip.set_audio(AudioFileClip("assets/se_tada.mp3").set_start(0.5))
    return apply_fade(clip)

def create_loto_clip(record, loto_type="LOTO6"):
    duration = 50 
    main_color = (14, 165, 233) if loto_type == "LOTO6" else (245, 158, 11)
    tint_color = (0, 100, 255, 40) if loto_type == "LOTO6" else (255, 150, 0, 40)
    
    target_kai = record.get('target_kai', '')
    date_str = record.get('date', '----/--/--')
    actual_main = [n.strip() for n in record.get('actual_main', '').split(',') if n.strip() and n != "----"]
    actual_bonus = re.findall(r'\d+', record.get('actual_bonus', ''))
    prizes = record.get('prizes', [])
    carryover = record.get('carryover', '')
    preds = record.get('predictions', [])[:5]
    
    has_hit = any(len(set(p) & set(actual_main)) >= 3 for p in preds if isinstance(p, list))

    def make_frame(t):
        img = get_base_frame(t, tint_color)
        draw = ImageDraw.Draw(img)

        if t < 15.0:
            draw_centered_text(draw, 80, f"■ {loto_type} {target_kai} 結果発表 ■", FONT_TITLE, (56, 189, 248) if loto_type == "LOTO6" else (251, 191, 36))
            draw_centered_text(draw, 160, f"抽選日: {date_str}", FONT_LIST, (220, 220, 220))
            ball_r, gap = 75, 25
            total_balls = len(actual_main) + 1
            start_x = (1920 - (total_balls * (2 * ball_r) + (total_balls - 1) * gap + 40)) / 2
            
            for i, num in enumerate(actual_main):
                draw_sphere_ball_with_bounce(draw, start_x + (i * (2*ball_r + gap)), 450, ball_r, num, main_color, t, 1.0 + (i * 0.8))
            
            b_x = start_x + (len(actual_main) * (2*ball_r + gap)) + 40
            if t > 1.0 + (len(actual_main) * 0.8) + 0.5:
                draw_text_with_shadow(draw, b_x + 10, 390, "ボーナス", FONT_SUB, (239, 68, 68))
                for i, b_num in enumerate(actual_bonus):
                    draw_sphere_ball_with_bounce(draw, b_x + (i * (2*ball_r + gap)), 450, ball_r, b_num, (220, 38, 38), t, 1.0 + (len(actual_main) * 0.8) + 0.5)

        elif t < 32.0:
            draw_centered_text(draw, 100, f"【 {target_kai} 当せん金額 と 口数 】", FONT_TITLE, (52, 211, 153))
            if prizes:
                for i, p in enumerate(prizes[:6]):
                    if t > 16.0 + (i * 0.8):
                        y = 230 + (i * 100)
                        show_len = int(max(0, (t - (16.0 + i * 0.8)) * 15))
                        grade_text = p.get('grade','')[:show_len]
                        prize_text = p.get('prize','')[:show_len]
                        
                        draw_text_with_shadow(draw, 400, y, grade_text, FONT_LIST, (255, 255, 255))
                        if len(p.get('grade','')) <= show_len:
                            draw_right_aligned_text(draw, 1100, y, prize_text, FONT_NUM, (250, 204, 21))
                        draw_text_with_shadow(draw, 1150, y, p.get('winners',''), FONT_LIST, (156, 163, 175))
            else:
                if t > 16.5: draw_centered_text(draw, 450, "※賞金・口数データは現在集計中です...", FONT_LIST, (200, 200, 200))

            if t > 22.0 and carryover and carryover != "0円":
                blink = int(255 * (0.5 + 0.5 * math.sin(t * 10)))
                draw_centered_text(draw, 880, f"■ キャリーオーバー: {carryover}", FONT_LIST, (255, blink, 0))

        else:
            draw_centered_text(draw, 80, f"【 {loto_type} AI予想パターンA〜E 結果 】", FONT_TITLE, (250, 204, 21))
            draw_centered_text(draw, 160, f"本数字: {'  '.join(actual_main)}", FONT_LIST, (255, 255, 255))
            
            for i, p in enumerate(preds):
                appear_t = 33.0 + (i * 2.2)
                if t > appear_t:
                    y = 260 + (i * 130)
                    p_str = ", ".join(p) if isinstance(p, list) else p
                    show_len = int(max(0, (t - appear_t) * 15))
                    draw_text_with_shadow(draw, 300, y, f"予想{chr(65+i)} :  {p_str[:show_len]}", FONT_LIST, (200, 200, 200))
                    
                    hit_m = len(set(p) & set(actual_main)) if isinstance(p, list) else 0
                    hit_b = len(set(p) & set(actual_bonus)) if isinstance(p, list) else 0
                    hit_color = (52, 211, 153) if hit_m >= 3 else (156, 163, 175)
                    hit_text = f"当 {hit_m}個一致" + (f" + B" if hit_b > 0 else "") if hit_m > 0 else "ハズレ"
                    
                    if hit_m >= 4:
                        blink = int(255 * (0.5 + 0.5 * math.sin(t * 15)))
                        hit_color = (255, blink, 0)
                        
                    if len(p_str) <= show_len:
                        draw_right_aligned_text(draw, 1580, y, hit_text, FONT_HIT, hit_color)
            
            if has_hit and t > 45.0:
                blink = int(255 * (0.5 + 0.5 * math.sin(t * 20)))
                draw.rectangle([0, 930, 1920, 1080], fill=(220, 38, 38, 200))
                draw_centered_text(draw, 960, "見事AI予想が的中しました！おめでとうございます！", FONT_TITLE, (255, blink, 0))

        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    audio_clips = []
    
    v_res = get_voice_clip(f"{loto_type} {target_kai}、結果発表です！", f"v_{loto_type}_{target_kai}_res.mp3", 0.5)
    v_prz = get_voice_clip("続いて、当選金額と口数です。", f"v_{loto_type}_{target_kai}_prz.mp3", 16.0)
    v_ans = get_voice_clip("最後に、AI予想の答え合わせです！", f"v_{loto_type}_{target_kai}_ans.mp3", 33.0)
    if v_res: audio_clips.append(v_res)
    if v_prz: audio_clips.append(v_prz)
    if v_ans: audio_clips.append(v_ans)
    
    if os.path.exists("assets/se_don.mp3"):
        for i in range(len(actual_main) + len(actual_bonus)): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(1.0 + (i * 0.8)))
    if os.path.exists("assets/se_whoosh.mp3"):
        for i in range(len(prizes[:6]) if prizes else 1): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(16.0 + (i * 0.8)))
        for i in range(len(preds)): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(33.0 + (i * 2.2)))
    if os.path.exists("assets/se_drumroll.mp3"): audio_clips.append(AudioFileClip("assets/se_drumroll.mp3").set_start(30.0).set_duration(2.0))
    if os.path.exists("assets/se_tada.mp3"): audio_clips.append(AudioFileClip("assets/se_tada.mp3").set_start(33.0))
    if audio_clips: clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
    
    return apply_fade(clip), has_hit

def create_numbers_clip(record):
    duration = 45 
    tint_color = (0, 200, 100, 30)
    target_kai = record.get('target_kai', '')
    date_str = record.get('date', '----/--/--')
    actual_n4 = record.get('actual_n4', '----')
    n4_preds = record.get('n4_preds', [])[:5]
    n4_prizes = record.get('n4_prizes', [])
    actual_n3 = record.get('actual_n3', '---')
    n3_preds = record.get('n3_preds', [])[:5]
    n3_prizes = record.get('n3_prizes', [])

    has_hit = False
    for p in n4_preds + n3_preds:
        if p == actual_n4 or p == actual_n3 or (sorted(p) == sorted(actual_n4) and actual_n4 != "----") or (sorted(p) == sorted(actual_n3) and actual_n3 != "---"):
            has_hit = True

    def make_frame(t):
        img = get_base_frame(t, tint_color)
        draw = ImageDraw.Draw(img)

        if t < 15.0:
            draw_centered_text(draw, 80, f"■ ナンバーズ {target_kai} 結果発表 ■", FONT_TITLE, (52, 211, 153))
            draw_centered_text(draw, 160, f"抽選日: {date_str}", FONT_LIST, (220, 220, 220))
            ball_r, gap = 75, 15
            
            draw_text_with_shadow(draw, 250, 300, "【 ナンバーズ4 】", FONT_TITLE, (255, 255, 255))
            start_x4 = 450 - ((4 * (2*ball_r) + 3 * gap) / 2)
            for i, num in enumerate(list(actual_n4)):
                draw_sphere_ball_with_bounce(draw, start_x4 + i*(2*ball_r+gap), 420, ball_r, num, (22, 163, 74), t, 1.0 + (i * 0.5))

            draw_text_with_shadow(draw, 1150, 300, "【 ナンバーズ3 】", FONT_TITLE, (255, 255, 255))
            start_x3 = 1350 - ((3 * (2*ball_r) + 2 * gap) / 2)
            for i, num in enumerate(list(actual_n3)):
                draw_sphere_ball_with_bounce(draw, start_x3 + i*(2*ball_r+gap), 420, ball_r, num, (217, 119, 6), t, 3.5 + (i * 0.5))

        elif t < 30.0:
            draw_centered_text(draw, 80, "【 当せん金額 と 口数 】", FONT_TITLE, (52, 211, 153))
            
            draw_text_with_shadow(draw, 100, 180, "■ ナンバーズ4", FONT_LIST, (22, 163, 74))
            if n4_prizes:
                for i, p in enumerate(n4_prizes):
                    appear_t = 16.0 + (i * 0.5)
                    if t > appear_t:
                        y = 260 + (i * 140)
                        show_len = int(max(0, (t - appear_t) * 15))
                        draw_text_with_shadow(draw, 100, y, p.get('grade','')[:show_len], FONT_LIST, (255, 255, 255))
                        if len(p.get('grade','')) <= show_len:
                            draw_right_aligned_text(draw, 650, y + 55, p.get('prize',''), FONT_NUM, (250, 204, 21))
                        draw_text_with_shadow(draw, 680, y + 70, p.get('winners',''), FONT_SUB, (156, 163, 175))
            else:
                if t > 16.5: draw_text_with_shadow(draw, 150, 400, "※集計中...", FONT_LIST, (200, 200, 200))

            draw_text_with_shadow(draw, 1050, 180, "■ ナンバーズ3", FONT_LIST, (217, 119, 6))
            if n3_prizes:
                for i, p in enumerate(n3_prizes):
                    appear_t = 18.0 + (i * 0.5)
                    if t > appear_t:
                        y = 260 + (i * 140)
                        show_len = int(max(0, (t - appear_t) * 15))
                        draw_text_with_shadow(draw, 1050, y, p.get('grade','')[:show_len], FONT_LIST, (255, 255, 255))
                        if len(p.get('grade','')) <= show_len:
                            draw_right_aligned_text(draw, 1600, y + 55, p.get('prize',''), FONT_NUM, (250, 204, 21))
                        draw_text_with_shadow(draw, 1630, y + 70, p.get('winners',''), FONT_SUB, (156, 163, 175))
            else:
                if t > 18.5: draw_text_with_shadow(draw, 1100, 400, "※集計中...", FONT_LIST, (200, 200, 200))

        else:
            draw_centered_text(draw, 80, "【 AI予想パターン 答え合わせ 】", FONT_TITLE, (250, 204, 21))
            draw_text_with_shadow(draw, 100, 180, f"N4 本数字: {actual_n4}", FONT_LIST, (255, 255, 255))
            draw_text_with_shadow(draw, 1000, 180, f"N3 本数字: {actual_n3}", FONT_LIST, (255, 255, 255))

            for i in range(5):
                appear_t = 31.0 + (i * 1.0)
                if t > appear_t:
                    y = 280 + (i * 135) 
                    p4 = n4_preds[i] if i < len(n4_preds) else "----"
                    
                    show_len = int(max(0, (t - appear_t) * 15))
                    draw_text_with_shadow(draw, 80, y, f"予想{chr(65+i)}: {p4[:show_len]}", FONT_LIST, (200, 200, 200))
                    
                    if p4 == actual_n4: res, col = "当 ストレート", (255, 100, 100)
                    elif sorted(p4) == sorted(actual_n4) and actual_n4 != "----": res, col = "当 ボックス", (255, 150, 0)
                    else: res, col = "ハズレ", (150, 150, 150)
                    if len(p4) <= show_len:
                        draw_text_with_shadow(draw, 520, y, res, FONT_LIST, col)

                    p3 = n3_preds[i] if i < len(n3_preds) else "---"
                    draw_text_with_shadow(draw, 980, y, f"予想{chr(65+i)}: {p3[:show_len]}", FONT_LIST, (200, 200, 200))
                    
                    if p3 == actual_n3: res, col = "当 ストレート", (255, 100, 100)
                    elif sorted(p3) == sorted(actual_n3) and actual_n3 != "---": res, col = "当 ボックス", (255, 150, 0)
                    else: res, col = "ハズレ", (150, 150, 150)
                    if len(p3) <= show_len:
                        draw_text_with_shadow(draw, 1420, y, res, FONT_LIST, col)
            
            if has_hit and t > 40.0:
                blink = int(255 * (0.5 + 0.5 * math.sin(t * 20)))
                draw.rectangle([0, 930, 1920, 1080], fill=(22, 163, 74, 200))
                draw_centered_text(draw, 960, "見事AI予想が的中しました！おめでとうございます！", FONT_TITLE, (255, blink, 0))

        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    audio_clips = []
    
    v_res = get_voice_clip(f"ナンバーズ {target_kai}、結果発表です！", f"v_num_{target_kai}_res.mp3", 0.5)
    v_prz = get_voice_clip("続いて、当選金額と口数です。", f"v_num_{target_kai}_prz.mp3", 16.0)
    v_ans = get_voice_clip("最後に、AI予想の答え合わせです！", f"v_num_{target_kai}_ans.mp3", 31.0)
    if v_res: audio_clips.append(v_res)
    if v_prz: audio_clips.append(v_prz)
    if v_ans: audio_clips.append(v_ans)

    if os.path.exists("assets/se_don.mp3"):
        for i in range(4): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(1.0 + (i * 0.5)))
        for i in range(3): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(3.5 + (i * 0.5)))
    if os.path.exists("assets/se_whoosh.mp3"):
        for i in range(len(n4_prizes) if n4_prizes else 1): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(16.0 + (i * 0.5)))
        for i in range(len(n3_prizes) if n3_prizes else 1): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(18.0 + (i * 0.5)))
        for i in range(5): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(31.0 + (i * 1.0)))
    if os.path.exists("assets/se_tada.mp3"): audio_clips.append(AudioFileClip("assets/se_tada.mp3").set_start(31.0))
    if audio_clips: clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
    
    return apply_fade(clip), has_hit

def generate_weekly_video():
    global bg_video, bgm_clip
    print("\n🎬 超長尺・完全版(フラッシュバック＆タイプライター＆ダッキング搭載) 起動中！")
    
    cleanup_old_voice_files()
    
    try:
        if os.path.exists(BG_VIDEO_PATH): bg_video = VideoFileClip(BG_VIDEO_PATH)
    except: pass
    try:
        if os.path.exists(BGM_PATH): bgm_clip = AudioFileClip(BGM_PATH)
    except: pass

    all_clips = []
    highlight_clips = [] 
    
    n_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID_NUMBERS"), 5)
    l6_hist_all = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID"), 10)
    l7_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID_LOTO7"), 1)
    
    l6_hist = l6_hist_all[:2]

    v_db_n = fetch_video_db_safe(os.environ.get("JSONBIN_BIN_ID_VIDEO_NUMBERS"))
    v_db_l6 = fetch_video_db_safe(os.environ.get("JSONBIN_BIN_ID_VIDEO") or os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO6"))
    v_db_l7 = fetch_video_db_safe(os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO7"))

    for rec in n_hist:
        nums = re.findall(r'\d+', str(rec.get("target_kai", "")))
        if nums and str(int(nums[0])) in v_db_n:
            kai_key = str(int(nums[0]))
            rec["date"] = v_db_n[kai_key].get("date", "----/--/--")
            rec["n4_prizes"] = v_db_n[kai_key].get("n4_prizes", [])
            rec["n3_prizes"] = v_db_n[kai_key].get("n3_prizes", [])

    for rec in l6_hist:
        nums = re.findall(r'\d+', str(rec.get("target_kai", "")))
        if nums and str(int(nums[0])) in v_db_l6:
            kai_key = str(int(nums[0]))
            rec["date"] = v_db_l6[kai_key].get("date", "----/--/--")
            rec["prizes"] = v_db_l6[kai_key].get("prizes", [])
            rec["carryover"] = v_db_l6[kai_key].get("carryover", "0円")

    for rec in l7_hist:
        nums = re.findall(r'\d+', str(rec.get("target_kai", "")))
        if nums and str(int(nums[0])) in v_db_l7:
            kai_key = str(int(nums[0]))
            rec["date"] = v_db_l7[kai_key].get("date", "----/--/--")
            rec["prizes"] = v_db_l7[kai_key].get("prizes", [])
            rec["carryover"] = v_db_l7[kai_key].get("carryover", "0円")

    all_dates = []
    for rec in n_hist + l6_hist + l7_hist:
        d = rec.get("date", "----/--/--")
        if d != "----/--/--":
            all_dates.append(d)
    
    op_start_date, op_end_date = "", ""
    if all_dates:
        sorted_dates = sorted(all_dates)
        # ★ 修正：一番新しいデータの日付を基準に「その週の月曜日〜金曜日」を計算する
        latest_date_str = sorted_dates[-1]
        m = re.search(r'(\d{4})[/年]\s*(\d{1,2})[/月]\s*(\d{1,2})', latest_date_str)
        if m:
            y, mth, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            latest_dt = datetime.date(y, mth, d)
            monday = latest_dt - datetime.timedelta(days=latest_dt.weekday())
            friday = monday + datetime.timedelta(days=4)
            op_start_date = f"{monday.month}月{monday.day}日"
            op_end_date = f"{friday.month}月{friday.day}日"
        else:
            op_start_date = get_short_date(sorted_dates[0])
            op_end_date = get_short_date(sorted_dates[-1])

    if n_hist:
        title_clip = create_title_clip(n_hist, "ナンバーズ", (52, 211, 153), "続いて、ナンバーズの結果まとめです！", "voice_title_num.mp3")
        if title_clip: all_clips.append(title_clip)
        for rec in reversed(n_hist):
            clip, has_hit = create_numbers_clip(rec)
            all_clips.append(clip)
            if has_hit: highlight_clips.append(clip.subclip(40, 42.5))

    if l6_hist:
        title_clip = create_title_clip(l6_hist, "ロト6", (56, 189, 248), "続いて、ロトシックスの結果まとめです！", "voice_title_l6.mp3")
        if title_clip: all_clips.append(title_clip)
        for rec in reversed(l6_hist):
            clip, has_hit = create_loto_clip(rec, "LOTO6")
            all_clips.append(clip)
            if has_hit: highlight_clips.append(clip.subclip(45, 47.5))

    if l7_hist:
        title_clip = create_title_clip(l7_hist, "ロト7", (251, 191, 36), "続いて、ロトセブンの結果まとめです！", "voice_title_l7.mp3")
        if title_clip: all_clips.append(title_clip)
        for rec in reversed(l7_hist):
            clip, has_hit = create_loto_clip(rec, "LOTO7")
            all_clips.append(clip)
            if has_hit: highlight_clips.append(clip.subclip(45, 47.5))

    rakuten_hc_data = fetch_all_rakuten_hot_cold()
    if "NUMBERS4" in rakuten_hc_data:
        hc_clip = create_hot_cold_clip("ナンバーズ4", rakuten_hc_data["NUMBERS4"]["hot"], rakuten_hc_data["NUMBERS4"]["cold"], (22, 163, 74))
        if hc_clip: all_clips.append(hc_clip)
    if "NUMBERS3" in rakuten_hc_data:
        hc_clip = create_hot_cold_clip("ナンバーズ3", rakuten_hc_data["NUMBERS3"]["hot"], rakuten_hc_data["NUMBERS3"]["cold"], (217, 119, 6))
        if hc_clip: all_clips.append(hc_clip)
    if "LOTO6" in rakuten_hc_data:
        hc_clip = create_hot_cold_clip("ロト6", rakuten_hc_data["LOTO6"]["hot"], rakuten_hc_data["LOTO6"]["cold"], (56, 189, 248))
        if hc_clip: all_clips.append(hc_clip)
    if "LOTO7" in rakuten_hc_data:
        hc_clip = create_hot_cold_clip("ロト7", rakuten_hc_data["LOTO7"]["hot"], rakuten_hc_data["LOTO7"]["cold"], (251, 191, 36))
        if hc_clip: all_clips.append(hc_clip)

    ed_clip = create_ending_clip()
    if ed_clip: all_clips.append(ed_clip)

    final_clips = []
    
    if highlight_clips:
        print("🎉 的中データを発見しました！冒頭にハイライトを挿入します。")
        def make_hl_title(t):
            img = Image.new('RGBA', (1920, 1080), color=(15, 23, 42, 255))
            draw = ImageDraw.Draw(img)
            draw_centered_text(draw, 500, "＼ 今 週 の ハ イ ラ イ ト ／", FONT_TITLE, (250, 204, 21))
            return np.array(img.convert('RGB'))
        hl_title = VideoClip(make_hl_title, duration=1.0)
        final_clips.append(hl_title)
        final_clips.extend(highlight_clips) 

    op_clip = create_opening_clip(op_start_date, op_end_date)
    if op_clip: final_clips.append(op_clip)
    
    final_clips.extend(all_clips)

    if not final_clips:
        print("❌ 生成できるデータがありませんでした。")
        return

    print(f"\n🎞️ 全 {len(final_clips)} シーンを結合中... (レンダリングには数分かかります)")
    final_video = concatenate_videoclips(final_clips, method="compose")
    
    if bgm_clip:
        print("🎧 全体にBGMを合成し、音量バランスを最適化します...")
        looped_bgm = audio_loop(bgm_clip, duration=final_video.duration).volumex(0.15) 
        final_video = final_video.set_audio(CompositeAudioClip([looped_bgm, final_video.audio]))

    output_filename = "weekly_summary.mp4"
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="libmp3lame", threads=1)
    
    if os.path.exists("temp_graph.png"): os.remove("temp_graph.png")
    print(f"\n🎉🎉🎉 究極版 1週間まとめ動画が完成しました！ => {output_filename} 🎉🎉🎉")

    # ==========================================
    # 🚀 YouTubeへのアップロードとサイト自動更新の実行
    # ==========================================
    yt_title = f"【1週間まとめ】ロト＆ナンバーズ AI予想結果と最新トレンド ({op_end_date} 最新版)"
    yt_desc = "今週のロト6、ロト7、ナンバーズのAI予想と実際の抽選結果の答え合わせ動画です！\n\n🎯完全無料のAI予想サイトはこちら\n👉 https://loto-yosou-ai.com/"
    yt_tags = ["ロト6", "ロト7", "ナンバーズ", "宝くじ", "AI予想"]
    
    # YouTubeにアップロードして、動画のIDを取得
    video_id = upload_weekly_to_youtube(output_filename, yt_title, yt_desc, yt_tags)
    
    # アップロードに成功したら、archive.html を書き換え、Instagramにも投稿する
    if video_id:
        display_date = f"📅 {op_start_date} 〜 {op_end_date}"
        update_archive_html(video_id, yt_title, display_date)
        
        # --- ここから追加：Instagramへの告知画像投稿 ---
        try:
            thumbnail_path = "weekly_thumbnail.jpg"
            
            # 作成した動画の5秒目（タイトル画面）を切り取って画像として保存
            final_video.save_frame(thumbnail_path, t=5.0)
            
            ig_caption = f"📺 今週のまとめ動画をYouTubeに公開しました！\n\n🎯 {op_start_date} 〜 {op_end_date} のロト＆ナンバーズ AI予想結果と最新トレンドを一挙公開中！\n\nプロフィールのリンク（またはYouTubeで「ロトナンバーズ攻略局」と検索）からフル動画をチェックしてください✨\n\n#ロト6 #ロト7 #ナンバーズ #宝くじ #AI予想"
            
            print("\n📸 Instagramへの告知画像投稿を開始します...")
            image_url = upload_image_to_server(thumbnail_path)
            if image_url:
                post_to_instagram(image_url, ig_caption)
        except Exception as e:
            print(f"❌ Instagramへの告知投稿中にエラーが発生しました: {e}")
        # --- 追加ここまで ---

if __name__ == "__main__":
    generate_weekly_video()