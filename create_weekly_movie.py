import os
import math
import requests
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips
from moviepy.audio.fx.all import audio_loop
from dotenv import load_dotenv

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

load_dotenv()

# ==========================================
# 🎵 背景動画とBGMのパス設定（安全なパス指定方式に変更）
# ==========================================
BG_VIDEO_PATH = os.path.join("assets", "create_weekly.mp4")
BGM_PATH = os.path.join("assets", "create_weekly.mp3")

# グローバル変数として用意（読み込みは後で行います）
bg_video = None
bgm_clip = None

# ==========================================
# 🔍 共通準備（フォント・描画ツール）
# ==========================================
FONT_PATH = "assets/font.ttf"
try:
    FONT_TITLE = ImageFont.truetype(FONT_PATH, 70)
    FONT_NUM = ImageFont.truetype(FONT_PATH, 100)
    FONT_LIST = ImageFont.truetype(FONT_PATH, 65)
    FONT_HIT = ImageFont.truetype(FONT_PATH, 70)
except:
    FONT_TITLE = FONT_NUM = FONT_LIST = FONT_HIT = ImageFont.load_default()

def draw_text_with_shadow(draw, x, y, text, font, fill_color, shadow_color=(0,0,0,200)):
    draw.text((x+4, y+4), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill_color)

def draw_centered_text(draw, y, text, font, fill_color, screen_w=1920):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (screen_w - (bbox[2] - bbox[0])) / 2
    draw_text_with_shadow(draw, x, y, text, font, fill_color)

def draw_sphere_ball(draw, x, y, r, text, ball_color, font_color=(255, 255, 255)):
    draw.ellipse([x + 5, y + 5, x + 2*r + 5, y + 2*r + 5], fill=(0, 0, 0, 150))
    draw.ellipse([x, y, x + 2*r, y + 2*r], fill=ball_color)
    inner_r, off = int(r * 0.85), int(r * 0.07)
    draw.ellipse([x + off, y + off, x + off + 2*inner_r, y + off + 2*inner_r], fill=tuple(min(255, c + 50) for c in ball_color))
    hl_r = int(r * 0.3)
    draw.ellipse([x + int(r*0.2), y + int(r*0.2), x + int(r*0.2) + 2*hl_r, y + int(r*0.2) + 2*hl_r], fill=(255, 255, 255, 200))
    bbox = draw.textbbox((0, 0), text, font=FONT_NUM)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw_text_with_shadow(draw, x + r - w / 2, y + r - h / 2 - 20, text, FONT_NUM, font_color)

def get_base_frame(t):
    if bg_video:
        frame_t = t % bg_video.duration
        return Image.fromarray(bg_video.get_frame(frame_t)).convert('RGBA')
    return Image.new('RGBA', (1920, 1080), color=(15, 23, 42, 255))

# ==========================================
# ☁️ データ取得
# ==========================================
def fetch_finished_history(bin_id, limit):
    api_key = os.environ.get("JSONBIN_API_KEY")
    if not bin_id or not api_key: return []
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}", headers={"X-Master-Key": api_key})
        if res.status_code == 200:
            records = res.json().get('record', [])
            return [r for r in records if r.get('status') == 'finished'][:limit]
    except: pass
    return []

# ==========================================
# 🎬 ロト動画職人
# ==========================================
def create_loto_clip(record, loto_type="LOTO6"):
    duration = 32
    main_color = (14, 165, 233) if loto_type == "LOTO6" else (245, 158, 11)
    
    target_kai = record.get('target_kai', '')
    date_str = record.get('date', '----/--/--')
    actual_main = [n.strip() for n in record.get('actual_main', '').split(',') if n.strip() and n != "----"]
    
    bonus_str = record.get('actual_bonus', '')
    actual_bonus = re.findall(r'\d+', bonus_str)
    
    prizes = record.get('prizes', [])
    carryover = record.get('carryover', '')
    preds = record.get('predictions', [])[:5]

    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)

        # 📺 シーン1：本数字＆ボーナス数字発表（0〜9秒）
        if t < 9.0:
            draw_centered_text(draw, 150, f"■ {loto_type} {target_kai} ({date_str}) 結果発表 ■", FONT_TITLE, (56, 189, 248) if loto_type == "LOTO6" else (251, 191, 36))
            
            ball_r = 85
            start_x = 120 if len(actual_main) >= 7 else 220
            base_y = 420
            
            for i, num in enumerate(actual_main):
                appear_t = 1.0 + (i * 0.8)
                if t > appear_t:
                    progress = min(1.0, (t - appear_t) * 4.0)
                    y_offset = int(50 * (1.0 - progress))
                    draw_sphere_ball(draw, start_x + (i * 200), base_y + y_offset, ball_r, num, main_color)
            
            bonus_appear_t = 1.0 + (len(actual_main) * 0.8) + 0.5
            if t > bonus_appear_t:
                progress = min(1.0, (t - bonus_appear_t) * 4.0)
                y_offset = int(50 * (1.0 - progress))
                b_x = start_x + (len(actual_main) * 200) + 40
                draw_text_with_shadow(draw, b_x + (20 if len(actual_bonus)==1 else 60), base_y - 70, "ボーナス", FONT_LIST, (239, 68, 68))
                for i, b_num in enumerate(actual_bonus):
                    draw_sphere_ball(draw, b_x + (i * 180), base_y + y_offset, ball_r, b_num, (220, 38, 38))

        # 📺 シーン2：賞金発表（9〜18秒）
        elif t < 18.0:
            draw_centered_text(draw, 100, f"【 {target_kai} 当せん金額 と 口数 】", FONT_TITLE, (52, 211, 153))
            
            if prizes:
                base_prize_y = 250
                for i, p in enumerate(prizes):
                    if t > 9.5 + (i * 0.8):
                        y = base_prize_y + (i * 120)
                        draw_text_with_shadow(draw, 350, y, p.get('grade',''), FONT_LIST, (255, 255, 255))
                        draw_text_with_shadow(draw, 700, y, p.get('prize',''), FONT_NUM, (250, 204, 21))
                        draw_text_with_shadow(draw, 1400, y, p.get('winners',''), FONT_LIST, (156, 163, 175))
            else:
                if t > 10.0:
                    draw_centered_text(draw, 450, "※賞金・口数データは現在集計中です...", FONT_LIST, (200, 200, 200))

            if t > 14.0 and carryover and carryover != "0円":
                blink = int(255 * (0.5 + 0.5 * math.sin(t * 10)))
                draw_centered_text(draw, 880, f"💰 キャリーオーバー: {carryover}", FONT_LIST, (255, blink, 0))

        # 📺 シーン3：予想答え合わせ（18〜32秒）
        else:
            draw_centered_text(draw, 80, f"【 {loto_type} AI予想パターンA〜E 結果 】", FONT_TITLE, (250, 204, 21))
            draw_centered_text(draw, 180, f"本数字: {'  '.join(actual_main)}", FONT_LIST, (255, 255, 255))
            
            base_list_y = 300
            for i, p in enumerate(preds):
                if t > 19.0 + (i * 2.2):
                    y = base_list_y + (i * 120)
                    p_str = ", ".join(p) if isinstance(p, list) else p
                    draw_text_with_shadow(draw, 180, y, f"予想{chr(65+i)} :  {p_str}", FONT_LIST, (200, 200, 200))
                    
                    hit_m = len(set(p) & set(actual_main)) if isinstance(p, list) else 0
                    hit_b = len(set(p) & set(actual_bonus)) if isinstance(p, list) else 0
                    
                    hit_color = (52, 211, 153) if hit_m >= 3 else (156, 163, 175)
                    hit_text = f"🎯 {hit_m}個一致" + (f" + B" if hit_b > 0 else "") if hit_m > 0 else "ハズレ"
                    
                    if hit_m >= 4:
                        blink = int(255 * (0.5 + 0.5 * math.sin(t * 15)))
                        hit_color = (255, blink, 0)
                    draw_text_with_shadow(draw, 1350, y, hit_text, FONT_HIT, hit_color)

        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    
    # 🎵 SE
    audio_clips = []
    if os.path.exists("assets/se_don.mp3"):
        for i in range(len(actual_main) + len(actual_bonus)):
            audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(1.0 + (i * 0.8)))
    if os.path.exists("assets/se_whoosh.mp3"):
        for i in range(len(prizes) if prizes else 1):
            audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(9.5 + (i * 0.8)))
        for i in range(len(preds)):
            audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(19.0 + (i * 2.2)))
    if os.path.exists("assets/se_drumroll.mp3"):
        audio_clips.append(AudioFileClip("assets/se_drumroll.mp3").set_start(17.0).set_duration(2.0))
    if os.path.exists("assets/se_tada.mp3"):
        audio_clips.append(AudioFileClip("assets/se_tada.mp3").set_start(19.0))

    if audio_clips:
        clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
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

        # 📺 シーン1：ボール出現（0〜8秒）
        if t < 8.0:
            draw_centered_text(draw, 100, f"■ ナンバーズ {target_kai} ({date_str}) 結果発表 ■", FONT_TITLE, (52, 211, 153))
            ball_r = 90
            
            # ナンバーズ4
            draw_text_with_shadow(draw, 300, 300, "【 ナンバーズ4 】", FONT_TITLE, (255, 255, 255))
            for i, num in enumerate(list(actual_n4)):
                appear_t = 1.0 + (i * 0.5)
                if t > appear_t:
                    progress = min(1.0, (t - appear_t) * 4.0)
                    y_offset = int(50 * (1.0 - progress))
                    draw_sphere_ball(draw, 150 + (i * 190), 450 + y_offset, ball_r, num, (22, 163, 74))

            # ナンバーズ3
            draw_text_with_shadow(draw, 1250, 300, "【 ナンバーズ3 】", FONT_TITLE, (255, 255, 255))
            for i, num in enumerate(list(actual_n3)):
                appear_t = 3.5 + (i * 0.5)
                if t > appear_t:
                    progress = min(1.0, (t - appear_t) * 4.0)
                    y_offset = int(50 * (1.0 - progress))
                    draw_sphere_ball(draw, 1150 + (i * 190), 450 + y_offset, ball_r, num, (217, 119, 6))

        # 📺 シーン2：賞金発表（8〜16秒）
        elif t < 16.0:
            draw_centered_text(draw, 80, "【 当せん金額 と 口数 】", FONT_TITLE, (52, 211, 153))
            
            draw_text_with_shadow(draw, 250, 200, "■ ナンバーズ4", FONT_LIST, (22, 163, 74))
            if n4_prizes:
                for i, p in enumerate(n4_prizes):
                    if t > 8.5 + (i * 0.5):
                        y = 300 + (i * 80)
                        draw_text_with_shadow(draw, 100, y, p.get('grade',''), FONT_LIST, (255, 255, 255))
                        draw_text_with_shadow(draw, 450, y, p.get('prize',''), FONT_LIST, (250, 204, 21))
            else:
                if t > 9.0: draw_text_with_shadow(draw, 200, 400, "※集計中...", FONT_LIST, (200, 200, 200))

            draw_text_with_shadow(draw, 1150, 200, "■ ナンバーズ3", FONT_LIST, (217, 119, 6))
            if n3_prizes:
                for i, p in enumerate(n3_prizes):
                    if t > 10.5 + (i * 0.5):
                        y = 300 + (i * 80)
                        draw_text_with_shadow(draw, 1000, y, p.get('grade',''), FONT_LIST, (255, 255, 255))
                        draw_text_with_shadow(draw, 1350, y, p.get('prize',''), FONT_LIST, (250, 204, 21))
            else:
                if t > 11.0: draw_text_with_shadow(draw, 1100, 400, "※集計中...", FONT_LIST, (200, 200, 200))

        # 📺 シーン3：予想結果（16〜24秒）
        else:
            draw_centered_text(draw, 80, "【 AI予想パターン 答え合わせ 】", FONT_TITLE, (250, 204, 21))
            draw_text_with_shadow(draw, 200, 180, f"N4 本数字: {actual_n4}", FONT_LIST, (255, 255, 255))
            draw_text_with_shadow(draw, 1150, 180, f"N3 本数字: {actual_n3}", FONT_LIST, (255, 255, 255))

            for i in range(5):
                if t > 16.5 + (i * 1.0):
                    y = 320 + (i * 120)
                    p4 = n4_preds[i] if i < len(n4_preds) else "----"
                    draw_text_with_shadow(draw, 100, y, f"予想{chr(65+i)}: {p4}", FONT_LIST, (200, 200, 200))
                    if p4 == actual_n4: res, col = "🎯ストレート", (255, 100, 100)
                    elif sorted(p4) == sorted(actual_n4) and actual_n4 != "----": res, col = "🎯ボックス", (255, 150, 0)
                    else: res, col = "ハズレ", (150, 150, 150)
                    draw_text_with_shadow(draw, 500, y, res, FONT_LIST, col)

                    p3 = n3_preds[i] if i < len(n3_preds) else "---"
                    draw_text_with_shadow(draw, 1050, y, f"予想{chr(65+i)}: {p3}", FONT_LIST, (200, 200, 200))
                    if p3 == actual_n3: res, col = "🎯ストレート", (255, 100, 100)
                    elif sorted(p3) == sorted(actual_n3) and actual_n3 != "---": res, col = "🎯ボックス", (255, 150, 0)
                    else: res, col = "ハズレ", (150, 150, 150)
                    draw_text_with_shadow(draw, 1450, y, res, FONT_LIST, col)

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
    if os.path.exists("assets/se_tada.mp3"):
        audio_clips.append(AudioFileClip("assets/se_tada.mp3").set_start(16.5))

    if audio_clips:
        clip = clip.set_audio(CompositeAudioClip(audio_clips).set_duration(duration))
    return clip

# ==========================================
# 🚀 司令塔（メイン処理）
# ==========================================
def fetch_video_db(bin_id):
    """動画専用のDB(辞書)を取得する"""
    api_key = os.environ.get("JSONBIN_API_KEY")
    if not bin_id or not api_key: return {}
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}", headers={"X-Master-Key": api_key})
        return res.json().get('record', {}) if res.status_code == 200 else {}
    except: return {}

def generate_weekly_video():
    global bg_video, bgm_clip
    print("\n🎬 1週間まとめ動画のプログラムを起動しました！")
    print("🔄 背景動画(mp4)とBGM(mp3)を読み込んでいます...")
    
    # 背景とBGMの読み込み（変更なし）
    try:
        if os.path.exists(BG_VIDEO_PATH): bg_video = VideoFileClip(BG_VIDEO_PATH)
    except: pass
    try:
        if os.path.exists(BGM_PATH): bgm_clip = AudioFileClip(BGM_PATH)
    except: pass

    print("\n☁️ クラウドから【予想・結果】と【賞金・日付(動画用)】の両方を取得中...")
    all_clips = []

    # ① 心臓部のDB（予想・結果など）
    n_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID_NUMBERS"), 5)
    l6_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID"), 2)
    l7_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID_LOTO7"), 1)

    # ② 動画専用のDB（日付・賞金など）
    v_db_n = fetch_video_db(os.environ.get("JSONBIN_BIN_ID_VIDEO_NUMBERS"))
    v_db_l6 = fetch_video_db(os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO6"))
    v_db_l7 = fetch_video_db(os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO7"))

    # ★ ここで2つのデータを合体(マージ)させて職人に渡す！
    print(f"📊 ナンバーズ {len(n_hist)}回分を生成中...")
    for rec in reversed(n_hist):
        kai = rec.get("target_kai")
        if kai in v_db_n: # 動画用DBにデータがあれば合体
            rec["date"] = v_db_n[kai].get("date", "----/--/--")
            rec["n4_prizes"] = v_db_n[kai].get("n4_prizes", [])
            rec["n3_prizes"] = v_db_n[kai].get("n3_prizes", [])
        all_clips.append(create_numbers_clip(rec))

    print(f"📊 ロト6 {len(l6_hist)}回分を生成中...")
    for rec in reversed(l6_hist):
        kai = rec.get("target_kai")
        if kai in v_db_l6:
            rec["date"] = v_db_l6[kai].get("date", "----/--/--")
            rec["prizes"] = v_db_l6[kai].get("prizes", [])
            rec["carryover"] = v_db_l6[kai].get("carryover", "0円")
        all_clips.append(create_loto_clip(rec, "LOTO6"))

    print(f"📊 ロト7 {len(l7_hist)}回分を生成中...")
    for rec in reversed(l7_hist):
        kai = rec.get("target_kai")
        if kai in v_db_l7:
            rec["date"] = v_db_l7[kai].get("date", "----/--/--")
            rec["prizes"] = v_db_l7[kai].get("prizes", [])
            rec["carryover"] = v_db_l7[kai].get("carryover", "0円")
        all_clips.append(create_loto_clip(rec, "LOTO7"))

    if not all_clips:
        print("❌ 生成できる確定データがありませんでした。")
        return

    print(f"\n🎞️ 全 {len(all_clips)} シーンを結合中... (レンダリングには数分かかります)")
    final_video = concatenate_videoclips(all_clips, method="compose")
    
    if bgm_clip:
        print("🎧 全体にBGMを合成します...")
        from moviepy.audio.fx.all import audio_loop
        looped_bgm = audio_loop(bgm_clip, duration=final_video.duration).volumex(0.3)
        final_audio = CompositeAudioClip([looped_bgm, final_video.audio])
        final_video = final_video.set_audio(final_audio)

    output_filename = "weekly_summary.mp4"
    final_video.write_videofile(
        output_filename, fps=24, codec="libx264", audio_codec="libmp3lame", threads=4
    )
    print(f"\n🎉🎉🎉 1週間まとめ動画が完成しました！ => {output_filename} 🎉🎉🎉")

if __name__ == "__main__":
    generate_weekly_video()