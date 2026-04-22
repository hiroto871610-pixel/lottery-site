import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, AudioFileClip, CompositeAudioClip
# ▼▼▼ ココを追加！ (Pillow 10.0以降のANTIALIASエラー対策) ▼▼▼
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ▲▲▲ ここまで ▲▲▲

# ==========================================
# 🔍 準備
# ==========================================
FONT_PATH = "assets/font.ttf"
try:
    FONT_TITLE = ImageFont.truetype(FONT_PATH, 70)
    FONT_NUM = ImageFont.truetype(FONT_PATH, 100) # ★数字をさらに大きく！(80→100)
    FONT_LIST = ImageFont.truetype(FONT_PATH, 65)
    FONT_HIT = ImageFont.truetype(FONT_PATH, 70)
except:
    FONT_TITLE = FONT_NUM = FONT_LIST = FONT_HIT = ImageFont.load_default()

def draw_centered_text(draw, y, text, font, fill_color, screen_w=1920):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (screen_w - text_w) / 2
    draw.text((x, y), text, font=font, fill=fill_color)

def draw_sphere_ball(draw, x, y, r, text, ball_color, font_color=(255, 255, 255)):
    draw.ellipse([x + 5, y + 5, x + 2*r + 5, y + 2*r + 5], fill=(0, 0, 0, 100))
    draw.ellipse([x, y, x + 2*r, y + 2*r], fill=ball_color)
    inner_r, off = int(r * 0.85), int(r * 0.07)
    draw.ellipse([x + off, y + off, x + off + 2*inner_r, y + off + 2*inner_r], fill=tuple(min(255, c + 50) for c in ball_color))
    hl_r = int(r * 0.3)
    draw.ellipse([x + int(r*0.2), y + int(r*0.2), x + int(r*0.2) + 2*hl_r, y + int(r*0.2) + 2*hl_r], fill=(255, 255, 255, 200))
    bbox = draw.textbbox((0, 0), text, font=FONT_NUM)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x + r - w / 2, y + r - h / 2 - 20), text, font=FONT_NUM, fill=font_color)

# ==========================================
# 🎬 本編：動画生成
# ==========================================
def generate_result_scene(data):
    print("🎬 3シーン構成：結果発表シーン（32秒）を生成中...")
    
    width, height = 1920, 1080
    duration = 32 # 3つのシーンを収めるために32秒に延長
    
    def make_frame(t):
        img = Image.new('RGBA', (width, height), color=(15, 23, 42, 255))
        draw = ImageDraw.Draw(img)

        # ------------------------------------------------
        # 📺 シーン1：本数字＆ボーナス数字発表（0〜9秒）
        # ------------------------------------------------
        if t < 9.0:
            # ★ご要望：回号と日付を復活
            title_text = f"■ {data['round']} ({data['date']}) ロト6 結果発表 ■"
            draw_centered_text(draw, 150, title_text, FONT_TITLE, (56, 189, 248))
            
            # ★ご要望：ボールを大きく (半径70→85)
            ball_r = 85
            start_x = 220
            base_y = 420
            
            # 本数字6個
            for i, num in enumerate(data['main_nums']):
                appear_t = 1.0 + (i * 0.8)
                if t > appear_t:
                    progress = min(1.0, (t - appear_t) * 4.0)
                    y_offset = int(50 * (1.0 - progress)) 
                    draw_sphere_ball(draw, start_x + (i * 210), base_y + y_offset, ball_r, num, (14, 165, 233))
            
            # ★ご要望：ボーナス数字を追加 (色は赤系)
            bonus_appear_t = 1.0 + (6 * 0.8) + 0.5
            if t > bonus_appear_t:
                progress = min(1.0, (t - bonus_appear_t) * 4.0)
                y_offset = int(50 * (1.0 - progress))
                b_x = start_x + (6 * 210) + 50 # 少し間を開ける
                
                draw.text((b_x + 30, base_y - 70), "ボーナス", font=FONT_LIST, fill=(239, 68, 68))
                draw_sphere_ball(draw, b_x, base_y + y_offset, ball_r, data['bonus'], (220, 38, 38))

        # ------------------------------------------------
        # 📺 シーン2：★新規★ 等級ごとの賞金発表（9〜18秒）
        # ------------------------------------------------
        elif t < 18.0:
            draw_centered_text(draw, 100, "【 当せん金額 と 口数 】", FONT_TITLE, (52, 211, 153))
            
            base_prize_y = 250
            for i, prize_info in enumerate(data['prizes']):
                row_t = 9.5 + (i * 0.8)
                if t > row_t:
                    y = base_prize_y + (i * 120)
                    # 等級
                    draw.text((350, y), prize_info['grade'], font=FONT_LIST, fill=(255, 255, 255))
                    # 当せん金
                    draw.text((700, y), prize_info['prize'], font=FONT_NUM, fill=(250, 204, 21))
                    # 口数
                    draw.text((1400, y), prize_info['winners'], font=FONT_LIST, fill=(156, 163, 175))

            if t > 14.0 and data.get('carryover') and data['carryover'] != "0円":
                blink = int(255 * (0.5 + 0.5 * math.sin(t * 10)))
                draw_centered_text(draw, 880, f"💰 キャリーオーバー: {data['carryover']} 発生中！", FONT_LIST, (255, blink, 0))

        # ------------------------------------------------
        # 📺 シーン3：予想答え合わせ（18〜32秒）
        # ------------------------------------------------
        else:
            draw_centered_text(draw, 80, "【 当サイト AI予想パターンA〜E 結果 】", FONT_TITLE, (250, 204, 21))
            draw_centered_text(draw, 180, f"本数字: {'  '.join(data['main_nums'])}", FONT_LIST, (255, 255, 255))
            
            base_list_y = 300
            for i, pred in enumerate(data['predictions']):
                row_appear_t = 19.0 + (i * 2.2) 
                if t > row_appear_t:
                    y = base_list_y + (i * 120)
                    draw.text((250, y), f"{pred['name']} :  {pred['nums']}", font=FONT_LIST, fill=(200, 200, 200))
                    
                    hit_color = (52, 211, 153) if pred['hit'] >= 3 else (156, 163, 175)
                    hit_text = f"🎯 {pred['hit']} 個的中！" if pred['hit'] > 0 else "ハズレ"
                    
                    if pred['hit'] >= 4:
                        blink = int(255 * (0.5 + 0.5 * math.sin(t * 15)))
                        hit_color = (255, blink, 0)
                    draw.text((1200, y), hit_text, font=FONT_HIT, fill=hit_color)

        return np.array(img.convert('RGB'))

    video_clip = VideoClip(make_frame, duration=duration)
    
    # 🎵 音声処理
    audio_clips = []
    
    if os.path.exists("assets/se_don.mp3"):
        # 本数字6個 + ボーナス1個 = 7回鳴らす
        for i in range(7):
            audio_clips.append(AudioFileClip("assets/se_don.mp3").set_start(1.0 + (i * 0.8)))

    if os.path.exists("assets/se_whoosh.mp3"):
        # 賞金の行数分シュワッ！
        for i in range(len(data['prizes'])):
            audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(9.5 + (i * 0.8)))
        # 予想の行数分シュワッ！
        for i in range(len(data['predictions'])):
            audio_clips.append(AudioFileClip("assets/se_whoosh.mp3").set_start(19.0 + (i * 2.2)))

    if os.path.exists("assets/se_drumroll.mp3"):
        audio_clips.append(AudioFileClip("assets/se_drumroll.mp3").set_start(17.0).set_duration(2.0))

    if os.path.exists("assets/se_tada.mp3"):
        audio_clips.append(AudioFileClip("assets/se_tada.mp3").set_start(19.0))

    if audio_clips:
        final_audio = CompositeAudioClip(audio_clips).set_duration(duration)
        video_clip = video_clip.set_audio(final_audio)

    output_path = "test_result_scene.mp4"
    video_clip.write_videofile(
        output_path, fps=30, codec="libx264", audio_codec="libmp3lame", 
        temp_audiofile="temp-audio.mp3", remove_temp=True
    )
    print("🎉 結果発表シーンが完成しました！")

if __name__ == "__main__":
    # ★ここに「本番のデータ構造」と同じ形のダミーデータを用意しました！
    test_data = {
        "round": "第2095回",
        "date": "2026/04/20",
        "main_nums": ["05", "12", "18", "24", "31", "42"],
        "bonus": "15",
        "carryover": "125,400,000円",
        "prizes": [
            {"grade": "1等", "winners": "該当なし", "prize": "0円"},
            {"grade": "2等", "winners": "12口", "prize": "10,500,000円"},
            {"grade": "3等", "winners": "180口", "prize": "350,000円"},
            {"grade": "4等", "winners": "8,500口", "prize": "7,200円"},
            {"grade": "5等", "winners": "150,000口", "prize": "1,000円"}
        ],
        "predictions": [
            {"name": "予想A", "nums": "05, 12, 19, 24, 31, 41", "hit": 4},
            {"name": "予想B", "nums": "03, 11, 18, 22, 33, 42", "hit": 2},
            {"name": "予想C", "nums": "05, 12, 18, 24, 31, 42", "hit": 6},
            {"name": "予想D", "nums": "01, 10, 15, 20, 30, 40", "hit": 0},
            {"name": "予想E", "nums": "12, 18, 24, 35, 38, 43", "hit": 3},
        ]
    }
    
    generate_result_scene(test_data)