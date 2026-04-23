import os
import math
import requests
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips
from moviepy.audio.fx.all import audio_loop
from dotenv import load_dotenv
from collections import Counter

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

load_dotenv()

# ==========================================
# 🎵 背景動画とBGMのパス
# ==========================================
BG_VIDEO_PATH = os.path.join("assets", "create_weekly.mp4")
BGM_PATH = os.path.join("assets", "create_weekly.mp3")

bg_video = None
bgm_clip = None

# ==========================================
# 🔍 共通準備（フォント・自動配置ツール）
# ==========================================
FONT_PATH = "assets/font.ttf"
try:
    FONT_TITLE = ImageFont.truetype(FONT_PATH, 45)
    FONT_SUB = ImageFont.truetype(FONT_PATH, 35)
    FONT_NUM = ImageFont.truetype(FONT_PATH, 55)
    FONT_LIST = ImageFont.truetype(FONT_PATH, 40)
    FONT_HIT = ImageFont.truetype(FONT_PATH, 45)
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

# ★ 根本的解決：エラーの元だった無駄な1行を削除し、強制リサイズを有効化！
def get_base_frame(t):
    if bg_video:
        frame_t = t % bg_video.duration
        frame_img = Image.fromarray(bg_video.get_frame(frame_t)).convert('RGBA')
        return frame_img.resize((1920, 1080), PIL.Image.LANCZOS)
    return Image.new('RGBA', (1920, 1080), color=(15, 23, 42, 255))

# ==========================================
# ☁️ データ取得・照合
# ==========================================
def fetch_finished_history(bin_id, limit):
    api_key = os.environ.get("JSONBIN_API_KEY")
    if not bin_id or not api_key: return []
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}", headers={"X-Master-Key": api_key})
        if res.status_code == 200:
            records = []
            for r in res.json().get('record', []):
                if r.get('status') == 'finished' or (r.get('actual_main') and r.get('actual_main') != "----"):
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
        if isinstance(data, list): return {}
        safe_db = {}
        for k, v in data.items():
            nums = re.findall(r'\d+', k)
            if nums: safe_db[str(int(nums[0]))] = v
        return safe_db
    except: return {}

def get_short_date(d_str):
    """日付を「●月●日」の形式に綺麗にフォーマットする"""
    if not d_str or d_str == "----/--/--": return "----/--/--"
    m = re.search(r'\d{4}[/年]\s*(\d{1,2})[/月]\s*(\d{1,2})', d_str)
    if m: return f"{m.group(1)}月{m.group(2)}日"
    return d_str

# ==========================================
# 📺 【新機能】タイトルコール職人
# ==========================================
def create_title_clip(records, title_name, main_color):
    """各宝くじの最初に流れる「●月●日～●月●日 結果まとめ」のシーン"""
    duration = 4
    if not records: return None
    
    # リストの中で0番目が最新、最後が最古のデータ
    oldest = records[-1]
    newest = records[0]
    
    old_kai = oldest.get('target_kai', '')
    new_kai = newest.get('target_kai', '')
    old_date = get_short_date(oldest.get('date', '----/--/--'))
    new_date = get_short_date(newest.get('date', '----/--/--'))

    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)
        
        draw_centered_text(draw, 350, f"■ {title_name} 結果まとめ ■", FONT_TITLE, main_color)
        
        if old_kai == new_kai:
            # 1回分しかない場合
            draw_centered_text(draw, 500, f"{old_date} ({old_kai})", FONT_NUM, (255, 255, 255))
        else:
            # 複数回分ある場合
            draw_centered_text(draw, 460, f"{old_date} ({old_kai})", FONT_NUM, (255, 255, 255))
            draw_centered_text(draw, 580, "▼", FONT_LIST, (200, 200, 200))
            draw_centered_text(draw, 660, f"{new_date} ({new_kai})", FONT_NUM, (255, 255, 255))

        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    if os.path.exists("assets/se_whoosh.mp3"):
        clip = clip.set_audio(AudioFileClip("assets/se_whoosh.mp3").set_start(0.5))
    return clip

# ==========================================
# 🔥 HOT & COLD 紹介シーン職人
# ==========================================
def create_hot_cold_clip(loto6_records):
    duration = 10
    all_nums = []
    for rec in loto6_records:
        nums = [n.strip() for n in rec.get("actual_main", "").split(",") if n.strip().isdigit()]
        all_nums.extend(nums)

    counts = Counter(all_nums)
    for i in range(1, 44):
        n_str = str(i).zfill(2)
        if n_str not in counts: counts[n_str] = 0

    hot = counts.most_common(5)
    cold = list(reversed(counts.most_common()))[:5]

    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)

        draw_centered_text(draw, 100, "■ 直近データ分析 ( HOT & COLD ) ■", FONT_TITLE, (250, 204, 21))
        
        if t > 1.0:
            draw_centered_text(draw, 250, "🔥 よく出ている数字 (HOT)", FONT_SUB, (239, 68, 68))
            for i, (num, cnt) in enumerate(hot):
                appear_t = 1.5 + (i * 0.3)
                draw_sphere_ball_with_bounce(draw, 350 + (i * 250), 320, 60, num, (239, 68, 68), t, appear_t)
                if t > appear_t + 0.5:
                    draw_centered_text(draw, 460, f"{cnt}回", FONT_LIST, (255, 255, 255), screen_w=(350 + (i * 250) * 2 + 120))

        if t > 4.0:
            draw_centered_text(draw, 580, "❄️ 全く出ていない数字 (COLD)", FONT_SUB, (14, 165, 233))
            for i, (num, cnt) in enumerate(cold):
                appear_t = 4.5 + (i * 0.3)
                draw_sphere_ball_with_bounce(draw, 350 + (i * 250), 650, 60, num, (14, 165, 233), t, appear_t)
                if t > appear_t + 0.5:
                    draw_centered_text(draw, 790, f"{cnt}回", FONT_LIST, (255, 255, 255), screen_w=(350 + (i * 250) * 2 + 120))

        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    audio_clips = []
    if os.path.exists("assets/se_don.mp3"):
        for i in range(5): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(1.5 + (i * 0.3)))
        for i in range(5): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(4.5 + (i * 0.3)))
    if audio_clips: clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
    return clip

# ==========================================
# 📊 分析グラフ作成職人
# ==========================================
def create_trend_graph_clip(loto6_records):
    duration = 10
    targets = list(reversed(loto6_records[:10]))
    
    if len(targets) < 2:
        def make_frame_empty(t):
            img = get_base_frame(t)
            draw = ImageDraw.Draw(img)
            draw_centered_text(draw, 100, "■ 直近10回 ロト6 本数字合計値トレンド ■", FONT_TITLE, (52, 211, 153))
            draw_centered_text(draw, 450, "⚠️ データを収集中です...", FONT_TITLE, (200, 200, 200))
            draw_centered_text(draw, 550, "※過去データが蓄積されると、次回以降ここにグラフが表示されます", FONT_SUB, (150, 150, 150))
            return np.array(img.convert('RGB'))
        return VideoClip(make_frame_empty, duration=duration)

    labels, sums = [], []
    for rec in targets:
        nums = re.findall(r'\d+', rec.get("target_kai", ""))
        labels.append(nums[0] if nums else "?")
        main_nums = [int(n) for n in rec.get("actual_main", "").split(",") if n.strip().isdigit()]
        sums.append(sum(main_nums) if main_nums else 0)

    plt.figure(figsize=(14, 6), facecolor='#0f172a')
    ax = plt.axes()
    ax.set_facecolor('#0f172a')
    
    bars = plt.bar(labels, sums, color='#38bdf8', edgecolor='white', linewidth=1)
    plt.title("LOTO6 Main Numbers Sum Trend", color='white', fontsize=22, pad=20)
    plt.xlabel("Round", color='#94a3b8', fontsize=16)
    ax.tick_params(colors='white', labelsize=12)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#334155')
    ax.spines['left'].set_color('#334155')
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, int(yval), ha='center', color='#facc15', fontweight='bold', fontsize=14)

    plt.tight_layout()
    graph_filename = "temp_graph.png"
    plt.savefig(graph_filename, dpi=150, transparent=True)
    plt.close()

    graph_pil = Image.open(graph_filename).convert("RGBA")

    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)
        draw_centered_text(draw, 50, "■ 直近10回 ロト6 本数字合計値トレンド ■", FONT_TITLE, (52, 211, 153))
        
        scale = 1.0 + 0.015 * t
        new_w, new_h = int(graph_pil.width * scale), int(graph_pil.height * scale)
        resized_graph = graph_pil.resize((new_w, new_h), PIL.Image.LANCZOS)
        
        paste_x = int((1920 - new_w) / 2)
        paste_y = int((1080 - new_h) / 2) + 50
        img.paste(resized_graph, (paste_x, paste_y), resized_graph)
        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    if os.path.exists("assets/se_tada.mp3"):
        clip = clip.set_audio(AudioFileClip("assets/se_tada.mp3").set_start(0.5))
    return clip

# ==========================================
# 🎬 ロト動画職人
# ==========================================
def create_loto_clip(record, loto_type="LOTO6"):
    duration = 32
    main_color = (14, 165, 233) if loto_type == "LOTO6" else (245, 158, 11)
    
    target_kai = record.get('target_kai', '')
    date_str = record.get('date', '----/--/--')
    actual_main = [n.strip() for n in record.get('actual_main', '').split(',') if n.strip() and n != "----"]
    actual_bonus = re.findall(r'\d+', record.get('actual_bonus', ''))
    
    prizes = record.get('prizes', [])
    carryover = record.get('carryover', '')
    preds = record.get('predictions', [])[:5]

    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)

        # 📺 シーン1：ボール
        if t < 9.0:
            draw_centered_text(draw, 80, f"■ {loto_type} {target_kai} 結果発表 ■", FONT_TITLE, (56, 189, 248) if loto_type == "LOTO6" else (251, 191, 36))
            draw_centered_text(draw, 150, f"抽選日: {date_str}", FONT_LIST, (220, 220, 220))
            
            ball_r = 65
            gap = 20
            total_balls = len(actual_main) + 1
            total_w = total_balls * (2 * ball_r) + (total_balls - 1) * gap + 40
            start_x = (1920 - total_w) / 2
            base_y = 450
            
            for i, num in enumerate(actual_main):
                appear_t = 1.0 + (i * 0.8)
                draw_sphere_ball_with_bounce(draw, start_x + (i * (2*ball_r + gap)), base_y, ball_r, num, main_color, t, appear_t)
            
            bonus_appear_t = 1.0 + (len(actual_main) * 0.8) + 0.5
            b_x = start_x + (len(actual_main) * (2*ball_r + gap)) + 40
            if t > bonus_appear_t:
                draw_text_with_shadow(draw, b_x + 5, base_y - 60, "ボーナス", FONT_SUB, (239, 68, 68))
                for i, b_num in enumerate(actual_bonus):
                    draw_sphere_ball_with_bounce(draw, b_x + (i * (2*ball_r + gap)), base_y, ball_r, b_num, (220, 38, 38), t, bonus_appear_t)

        # 📺 シーン2：賞金
        elif t < 18.0:
            draw_centered_text(draw, 100, f"【 {target_kai} 当せん金額 と 口数 】", FONT_TITLE, (52, 211, 153))
            if prizes:
                base_prize_y = 230
                for i, p in enumerate(prizes[:6]):
                    if t > 9.5 + (i * 0.8):
                        y = base_prize_y + (i * 90)
                        draw_text_with_shadow(draw, 400, y, p.get('grade',''), FONT_LIST, (255, 255, 255))
                        draw_right_aligned_text(draw, 1050, y, p.get('prize',''), FONT_NUM, (250, 204, 21))
                        draw_text_with_shadow(draw, 1150, y, p.get('winners',''), FONT_LIST, (156, 163, 175))
            else:
                if t > 10.0: draw_centered_text(draw, 450, "※賞金・口数データは現在集計中です...", FONT_LIST, (200, 200, 200))

            if t > 14.0 and carryover and carryover != "0円":
                blink = int(255 * (0.5 + 0.5 * math.sin(t * 10)))
                draw_centered_text(draw, 850, f"💰 キャリーオーバー: {carryover}", FONT_LIST, (255, blink, 0))

        # 📺 シーン3：予想
        else:
            draw_centered_text(draw, 80, f"【 {loto_type} AI予想パターンA〜E 結果 】", FONT_TITLE, (250, 204, 21))
            draw_centered_text(draw, 150, f"本数字: {'  '.join(actual_main)}", FONT_LIST, (255, 255, 255))
            
            base_list_y = 250
            for i, p in enumerate(preds):
                if t > 19.0 + (i * 2.2):
                    y = base_list_y + (i * 120)
                    p_str = ", ".join(p) if isinstance(p, list) else p
                    draw_text_with_shadow(draw, 350, y, f"予想{chr(65+i)} :  {p_str}", FONT_LIST, (200, 200, 200))
                    
                    hit_m = len(set(p) & set(actual_main)) if isinstance(p, list) else 0
                    hit_b = len(set(p) & set(actual_bonus)) if isinstance(p, list) else 0
                    hit_color = (52, 211, 153) if hit_m >= 3 else (156, 163, 175)
                    hit_text = f"🎯 {hit_m}個一致" + (f" + B" if hit_b > 0 else "") if hit_m > 0 else "ハズレ"
                    
                    if hit_m >= 4:
                        blink = int(255 * (0.5 + 0.5 * math.sin(t * 15)))
                        hit_color = (255, blink, 0)
                    draw_right_aligned_text(draw, 1550, y, hit_text, FONT_HIT, hit_color)

        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    audio_clips = []
    if os.path.exists("assets/se_don.mp3"):
        for i in range(len(actual_main) + len(actual_bonus)): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(1.0 + (i * 0.8)))
    if os.path.exists("assets/se_whoosh.mp3"):
        for i in range(len(prizes[:6]) if prizes else 1): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(9.5 + (i * 0.8)))
        for i in range(len(preds)): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(19.0 + (i * 2.2)))
    if os.path.exists("assets/se_drumroll.mp3"): audio_clips.append(AudioFileClip("assets/se_drumroll.mp3").set_start(17.0).set_duration(2.0))
    if os.path.exists("assets/se_tada.mp3"): audio_clips.append(AudioFileClip("assets/se_tada.mp3").set_start(19.0))
    if audio_clips: clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
    return clip

# ==========================================
# 🎬 ナンバーズ動画職人
# ==========================================
def create_numbers_clip(record):
    duration = 24
    target_kai = record.get('target_kai', '')
    date_str = record.get('date', '----/--/--')
    
    actual_n4 = record.get('actual_n4', '----')
    n4_preds = record.get('n4_preds', [])[:5]
    n4_prizes = record.get('n4_prizes', [])
    
    actual_n3 = record.get('actual_n3', '---')
    n3_preds = record.get('n3_preds', [])[:5]
    n3_prizes = record.get('n3_prizes', [])

    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)

        # 📺 シーン1：ボール
        if t < 8.0:
            draw_centered_text(draw, 80, f"■ ナンバーズ {target_kai} 結果発表 ■", FONT_TITLE, (52, 211, 153))
            draw_centered_text(draw, 150, f"抽選日: {date_str}", FONT_LIST, (220, 220, 220))
            ball_r = 70
            gap = 15
            
            draw_text_with_shadow(draw, 250, 300, "【 ナンバーズ4 】", FONT_TITLE, (255, 255, 255))
            w4 = 4 * (2*ball_r) + 3 * gap
            start_x4 = 450 - (w4 / 2)
            for i, num in enumerate(list(actual_n4)):
                appear_t = 1.0 + (i * 0.5)
                draw_sphere_ball_with_bounce(draw, start_x4 + i*(2*ball_r+gap), 420, ball_r, num, (22, 163, 74), t, appear_t)

            draw_text_with_shadow(draw, 1150, 300, "【 ナンバーズ3 】", FONT_TITLE, (255, 255, 255))
            w3 = 3 * (2*ball_r) + 2 * gap
            start_x3 = 1350 - (w3 / 2)
            for i, num in enumerate(list(actual_n3)):
                appear_t = 3.5 + (i * 0.5)
                draw_sphere_ball_with_bounce(draw, start_x3 + i*(2*ball_r+gap), 420, ball_r, num, (217, 119, 6), t, appear_t)

        # 📺 シーン2：賞金
        elif t < 16.0:
            draw_centered_text(draw, 80, "【 当せん金額 と 口数 】", FONT_TITLE, (52, 211, 153))
            
            draw_text_with_shadow(draw, 150, 200, "■ ナンバーズ4", FONT_LIST, (22, 163, 74))
            if n4_prizes:
                for i, p in enumerate(n4_prizes):
                    if t > 8.5 + (i * 0.5):
                        y = 280 + (i * 85)
                        draw_text_with_shadow(draw, 100, y, p.get('grade',''), FONT_LIST, (255, 255, 255))
                        draw_right_aligned_text(draw, 650, y, p.get('prize',''), FONT_NUM, (250, 204, 21))
                        draw_text_with_shadow(draw, 680, y, p.get('winners',''), FONT_SUB, (156, 163, 175))
            else:
                if t > 9.0: draw_text_with_shadow(draw, 200, 400, "※集計中...", FONT_LIST, (200, 200, 200))

            draw_text_with_shadow(draw, 1100, 200, "■ ナンバーズ3", FONT_LIST, (217, 119, 6))
            if n3_prizes:
                for i, p in enumerate(n3_prizes):
                    if t > 10.5 + (i * 0.5):
                        y = 280 + (i * 85)
                        draw_text_with_shadow(draw, 1050, y, p.get('grade',''), FONT_LIST, (255, 255, 255))
                        draw_right_aligned_text(draw, 1600, y, p.get('prize',''), FONT_NUM, (250, 204, 21))
                        draw_text_with_shadow(draw, 1630, y, p.get('winners',''), FONT_SUB, (156, 163, 175))
            else:
                if t > 11.0: draw_text_with_shadow(draw, 1100, 400, "※集計中...", FONT_LIST, (200, 200, 200))

        # 📺 シーン3：予想結果
        else:
            draw_centered_text(draw, 80, "【 AI予想パターン 答え合わせ 】", FONT_TITLE, (250, 204, 21))
            draw_text_with_shadow(draw, 150, 180, f"N4 本数字: {actual_n4}", FONT_LIST, (255, 255, 255))
            draw_text_with_shadow(draw, 1050, 180, f"N3 本数字: {actual_n3}", FONT_LIST, (255, 255, 255))

            for i in range(5):
                if t > 16.5 + (i * 1.0):
                    y = 280 + (i * 125)
                    # ★ N4
                    p4 = n4_preds[i] if i < len(n4_preds) else "----"
                    draw_text_with_shadow(draw, 100, y, f"予想{chr(65+i)}: {p4}", FONT_LIST, (200, 200, 200))
                    if p4 == actual_n4: res, col = "🎯ストレート", (255, 100, 100)
                    elif sorted(p4) == sorted(actual_n4) and actual_n4 != "----": res, col = "🎯ボックス", (255, 150, 0)
                    else: res, col = "ハズレ", (150, 150, 150)
                    draw_text_with_shadow(draw, 500, y, res, FONT_LIST, col)

                    # ★ N3
                    p3 = n3_preds[i] if i < len(n3_preds) else "---"
                    draw_text_with_shadow(draw, 1000, y, f"予想{chr(65+i)}: {p3}", FONT_LIST, (200, 200, 200))
                    if p3 == actual_n3: res, col = "🎯ストレート", (255, 100, 100)
                    elif sorted(p3) == sorted(actual_n3) and actual_n3 != "---": res, col = "🎯ボックス", (255, 150, 0)
                    else: res, col = "ハズレ", (150, 150, 150)
                    draw_text_with_shadow(draw, 1400, y, res, FONT_LIST, col)

        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    audio_clips = []
    if os.path.exists("assets/se_don.mp3"):
        for i in range(4): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(1.0 + (i * 0.5)))
        for i in range(3): audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(3.5 + (i * 0.5)))
    if os.path.exists("assets/se_whoosh.mp3"):
        for i in range(len(n4_prizes) if n4_prizes else 1): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(8.5 + (i * 0.5)))
        for i in range(len(n3_prizes) if n3_prizes else 1): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(10.5 + (i * 0.5)))
        for i in range(5): audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(16.5 + (i * 1.0)))
    if os.path.exists("assets/se_tada.mp3"): audio_clips.append(AudioFileClip("assets/se_tada.mp3").set_start(16.5))
    if audio_clips: clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
    return clip

# ==========================================
# 🚀 司令塔（メイン処理）
# ==========================================
def generate_weekly_video():
    global bg_video, bgm_clip
    print("\n🎬 1週間まとめ動画のプログラムを起動しました！")
    
    try:
        if os.path.exists(BG_VIDEO_PATH): bg_video = VideoFileClip(BG_VIDEO_PATH)
    except: pass
    try:
        if os.path.exists(BGM_PATH): bgm_clip = AudioFileClip(BGM_PATH)
    except: pass

    all_clips = []
    
    # データの取得（過去10回分まで深く取得する）
    n_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID_NUMBERS"), 5)
    l6_hist_all = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID"), 10)
    l7_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID_LOTO7"), 1)
    
    # 動画用は直近2回分を使用
    l6_hist = l6_hist_all[:2]

    v_db_n = fetch_video_db_safe(os.environ.get("JSONBIN_BIN_ID_VIDEO_NUMBERS"))
    v_db_l6 = fetch_video_db_safe(os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO6"))
    v_db_l7 = fetch_video_db_safe(os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO7"))

    # ★ データと日付を「動画を作る前」に先にすべて結合しておく
    for rec in n_hist:
        nums = re.findall(r'\d+', rec.get("target_kai", ""))
        if nums and str(int(nums[0])) in v_db_n:
            kai_key = str(int(nums[0]))
            rec["date"] = v_db_n[kai_key].get("date", "----/--/--")
            rec["n4_prizes"] = v_db_n[kai_key].get("n4_prizes", [])
            rec["n3_prizes"] = v_db_n[kai_key].get("n3_prizes", [])

    for rec in l6_hist:
        nums = re.findall(r'\d+', rec.get("target_kai", ""))
        if nums and str(int(nums[0])) in v_db_l6:
            kai_key = str(int(nums[0]))
            rec["date"] = v_db_l6[kai_key].get("date", "----/--/--")
            rec["prizes"] = v_db_l6[kai_key].get("prizes", [])
            rec["carryover"] = v_db_l6[kai_key].get("carryover", "0円")

    for rec in l7_hist:
        nums = re.findall(r'\d+', rec.get("target_kai", ""))
        if nums and str(int(nums[0])) in v_db_l7:
            kai_key = str(int(nums[0]))
            rec["date"] = v_db_l7[kai_key].get("date", "----/--/--")
            rec["prizes"] = v_db_l7[kai_key].get("prizes", [])
            rec["carryover"] = v_db_l7[kai_key].get("carryover", "0円")

    # =========================================================
    # ★ 新機能：タイトルコールを各宝くじの直前に挿入！
    # =========================================================
    if n_hist:
        print("📺 ナンバーズのタイトルシーンを生成中...")
        title_clip = create_title_clip(n_hist, "ナンバーズ", (52, 211, 153))
        if title_clip: all_clips.append(title_clip)
        for rec in reversed(n_hist):
            all_clips.append(create_numbers_clip(rec))

    if l6_hist:
        print("📺 ロト6のタイトルシーンを生成中...")
        title_clip = create_title_clip(l6_hist, "ロト6", (56, 189, 248))
        if title_clip: all_clips.append(title_clip)
        for rec in reversed(l6_hist):
            all_clips.append(create_loto_clip(rec, "LOTO6"))

    if l7_hist:
        print("📺 ロト7のタイトルシーンを生成中...")
        title_clip = create_title_clip(l7_hist, "ロト7", (251, 191, 36))
        if title_clip: all_clips.append(title_clip)
        for rec in reversed(l7_hist):
            all_clips.append(create_loto_clip(rec, "LOTO7"))
    # =========================================================

    if l6_hist_all:
        print("🔥 HOT & COLD 分析のシーンを生成中...")
        hc_clip = create_hot_cold_clip(l6_hist_all)
        if hc_clip: all_clips.append(hc_clip)

    print("📊 分析グラフのシーンを生成中...")
    graph_clip = create_trend_graph_clip(l6_hist_all) 
    if graph_clip: all_clips.append(graph_clip)

    if not all_clips:
        print("❌ 生成できるデータがありませんでした。")
        return

    print(f"\n🎞️ 全 {len(all_clips)} シーンを結合中... (レンダリングには数分かかります)")
    final_video = concatenate_videoclips(all_clips, method="compose")
    
    if bgm_clip:
        print("🎧 全体にBGMを合成します...")
        looped_bgm = audio_loop(bgm_clip, duration=final_video.duration).volumex(0.3)
        final_video = final_video.set_audio(CompositeAudioClip([looped_bgm, final_video.audio]))

    output_filename = "weekly_summary.mp4"
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="libmp3lame", threads=4)
    
    if os.path.exists("temp_graph.png"): os.remove("temp_graph.png")
    print(f"\n🎉🎉🎉 1週間まとめ動画が完成しました！ => {output_filename} 🎉🎉🎉")

if __name__ == "__main__":
    generate_weekly_video()