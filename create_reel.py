import os
import urllib.request
import math
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, AudioFileClip

# 光の粒子アニメーション準備
NUM_PARTICLES = 50
particles = [{'x': random.randint(0, 1080), 'y': random.randint(0, 1920), 'size': random.randint(5, 15), 'speed': random.uniform(0.5, 2.0)} for _ in range(NUM_PARTICLES)]

# 共通フォント準備
FONT_PATH = "NotoSansJP-Bold.ttf"
if not os.path.exists(FONT_PATH):
    font_url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/static/NotoSansJP-Bold.ttf"
    urllib.request.urlretrieve(font_url, FONT_PATH)

FONT_TITLE = ImageFont.truetype(FONT_PATH, 90)
FONT_NUM = ImageFont.truetype(FONT_PATH, 110)
FONT_SUB = ImageFont.truetype(FONT_PATH, 50)

# ==========================================
# 共通描画エンジン（最新Pillow対応版）
# ==========================================
def draw_sphere_ball(draw, x, y, r, text, ball_color, font_color=(255, 255, 255)):
    """立体的な当選ボールを描画"""
    draw.ellipse([x + 10, y + 10, x + 2*r + 10, y + 2*r + 10], fill=(0, 0, 0, 80))
    draw.ellipse([x, y, x + 2*r, y + 2*r], fill=ball_color)
    
    inner_r = int(r * 0.85)
    off = int(r * 0.07)
    bright_color = tuple(min(255, c + 50) for c in ball_color)
    draw.ellipse([x + off, y + off, x + off + 2*inner_r, y + off + 2*inner_r], fill=bright_color)

    hl_r = int(r * 0.3)
    draw.ellipse([x + int(r*0.2), y + int(r*0.2), x + int(r*0.2) + 2*hl_r, y + int(r*0.2) + 2*hl_r], fill=(255, 255, 255, 200))

    # 🎯 最新Pillowの文字サイズ取得
    bbox = draw.textbbox((0, 0), text, font=FONT_NUM)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    text_x = x + r - w / 2
    text_y = y + r - h / 2 - 15 
    draw.text((text_x, text_y), text, font=FONT_NUM, fill=font_color)

def draw_particles(img, t):
    """光の粒子アニメーション"""
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    for p in particles:
        current_y = (p['y'] - t * p['speed'] * 50) % 1920
        current_x = p['x'] + int(30 * math.sin(t * 2 + p['y']))
        alpha = int(100 + 50 * math.sin(t * 5 + p['x']))
        draw.ellipse([current_x, current_y, current_x + p['size'], current_y + p['size']], fill=(255, 255, 255, alpha))
    return Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

def create_stylish_video(make_frame_func, output_path, bgm_path="bgm.mp3", duration=15):
    """動画生成エンジン"""
    def make_frame_with_particles(t):
        frame_img_array = make_frame_func(t)
        frame_img = Image.fromarray(frame_img_array)
        final_img = draw_particles(frame_img, t)
        return np.array(final_img)

    clip = VideoClip(make_frame_with_particles, duration=duration)
    clip = clip.fadein(0.5)

    if os.path.exists(bgm_path):
        print(f"🎵 BGM({bgm_path})を合成します...")
        try:
            audio = AudioFileClip(bgm_path)
            audio = audio.subclip(0, min(duration, audio.duration)).audio_fadeout(2.0)
            clip = clip.set_audio(audio)
        except Exception as e: print(f"❌ BGMエラー: {e}")

    print(f"🎞️ アニメーションレンダリング中... {output_path}")
    clip.write_videofile(output_path, fps=30, codec="libx264", audio_codec="libmp3lame")
    print(f"✅ 完成: {output_path}")

# ==========================================
# 1. ナンバーズ動画
# ==========================================
def generate_numbers_reel(n4_yosou, n3_yosou, bg_image="bg_numbers.jpg"):
    print(f"🎬 ナンバーズの動画を作成中... (N4:{n4_yosou} N3:{n3_yosou})")
    bg_base = Image.open(bg_image).resize((1080, 1920)).convert('RGBA') if os.path.exists(bg_image) else Image.new('RGBA', (1080, 1920), color=(30, 41, 59, 255))
    ball_r = 90 

    def make_frame(t):
        img = bg_base.copy()
        draw = ImageDraw.Draw(img)

        # ★修正：絵文字（🎯）を消し、上下に揺れるアニメーションの基準位置を少し上げる
        float_y = 250 + int(15 * math.sin(t * 3))
        draw.text((120, float_y), "明日のナンバーズ\n激アツ予想【A】", font=FONT_TITLE, fill=(255, 255, 255))
        
        # ★追加：タイトルの下に回号と日付を表示
        draw.text((120, float_y + 180), f"{target_kai} ({target_date})", font=FONT_SUB, fill=(220, 220, 220))

        draw.text((120, 700), "■ ナンバーズ4", font=FONT_SUB, fill=(52, 211, 153))
        for i, num in enumerate(list(n4_yosou)):
            appear_t = 1.0 + i * 0.2
            if t > appear_t:
                progress = min(1.0, (t - appear_t) * 3.3)
                y_off = int(50 * (1.0 - progress))
                draw_sphere_ball(draw, 120 + i * 210, 780 + y_off, ball_r, num, (22, 163, 74))

        if t > 3.0:
            draw.text((120, 1150), "■ ナンバーズ3", font=FONT_SUB, fill=(251, 146, 60))
            for i, num in enumerate(list(n3_yosou)):
                appear_t = 3.5 + i * 0.2
                if t > appear_t:
                    progress = min(1.0, (t - appear_t) * 3.3)
                    y_off = int(50 * (1.0 - progress))
                    draw_sphere_ball(draw, 200 + i * 210, 1230 + y_off, ball_r, num, (217, 119, 6))

        return np.array(img.convert('RGB'))

    create_stylish_video(make_frame, "reel_numbers.mp4")

# ==========================================
# 2. ロト6動画
# ==========================================
def generate_loto6_reel(numbers, carryover="0円", has_carryover=False, bg_image="bg_loto6.jpg"):
    print(f"🎬 ロト6の動画を作成中... (予想:{numbers} キャリーオーバー:{has_carryover})")
    bg_base = Image.open(bg_image).resize((1080, 1920)).convert('RGBA') if os.path.exists(bg_image) else Image.new('RGBA', (1080, 1920), color=(14, 165, 233, 255))
    ball_r = 75 
        
    def make_frame(t):
        img = bg_base.copy()
        draw = ImageDraw.Draw(img)

        float_y = 280 + int(15 * math.sin(t * 3))
        draw.text((120, float_y), "次回 ロト6\nAI予想【A】", font=FONT_TITLE, fill=(255, 255, 255))

        # ★追加：タイトルの下に回号と日付を表示
        draw.text((120, float_y + 180), f"{target_kai} ({target_date})", font=FONT_SUB, fill=(220, 220, 220))
        
        if has_carryover:
            blink = int(127 * (1 + math.sin(t * 8)))
            # ★修正：二重になっていた原因を直し、絵文字を消して改行する
            # 元のテキスト自体に「キャリーオーバー発生中！」が入っているのでそのまま使う
            clean_carryover = carryover.replace("💰 ", "").replace("！(", "！\n　 ")
            draw.text((120, float_y + 260), clean_carryover, font=FONT_SUB, fill=(255, 255, blink))
        
        for i, num in enumerate(numbers):
            appear_t = 1.0 + i * 0.2
            if t > appear_t:
                progress = min(1.0, (t - appear_t) * 3.3)
                y_off = int(50 * (1.0 - progress))
                row = i // 3
                col = i % 3
                base_y = 900 if has_carryover else 750
                draw_sphere_ball(draw, 150 + col * 260, base_y + row * 230 + y_off, ball_r, num, (14, 165, 233))

        return np.array(img.convert('RGB'))

    create_stylish_video(make_frame, "reel_loto6.mp4")

# ==========================================
# 3. ロト7動画
# ==========================================
def generate_loto7_reel(numbers, carryover="0円", has_carryover=False, bg_image="bg_loto7.jpg"):
    print(f"🎬 ロト7の動画を作成中... (予想:{numbers} キャリーオーバー:{has_carryover})")
    bg_base = Image.open(bg_image).resize((1080, 1920)).convert('RGBA') if os.path.exists(bg_image) else Image.new('RGBA', (1080, 1920), color=(245, 158, 11, 255))
    ball_r = 65 
        
    def make_frame(t):
        img = bg_base.copy()
        draw = ImageDraw.Draw(img)

        # ★修正：絵文字（🟧）を削除し、位置を少し上にズラす
        float_y = 280 + int(15 * math.sin(t * 3))
        draw.text((120, float_y), "次回 ロト7\nAI予想【A】", font=FONT_TITLE, fill=(255, 255, 255))

        # ★追加：タイトルの下に回号と日付を表示
        draw.text((120, float_y + 180), f"{target_kai} ({target_date})", font=FONT_SUB, fill=(220, 220, 220))
        
        if has_carryover:
            blink = int(127 * (1 + math.sin(t * 8)))
            # ★修正：二重になっていた原因を直し、絵文字を消して改行する
            clean_carryover = carryover.replace("💰 ", "").replace("！(", "！\n　 ")
            draw.text((120, float_y + 260), clean_carryover, font=FONT_SUB, fill=(255, 255, blink))
        
        for i, num in enumerate(numbers):
            appear_t = 1.0 + i * 0.15 
            if t > appear_t:
                progress = min(1.0, (t - appear_t) * 3.3)
                y_off = int(50 * (1.0 - progress))
                base_y = 850 if has_carryover else 700
                if i < 4:
                    draw_sphere_ball(draw, 100 + i * 220, base_y + y_off, ball_r, num, (217, 119, 6))
                else:
                    draw_sphere_ball(draw, 210 + (i-4) * 220, base_y + 200 + y_off, ball_r, num, (217, 119, 6))

        return np.array(img.convert('RGB'))

    create_stylish_video(make_frame, "reel_loto7.mp4")

# ==========================================
# テスト用・強制実行ブロック（これが消えていました！）
# ==========================================
if __name__ == "__main__":
    print("\n🔄 テスト実行を開始します...")
    # テストの待ち時間を減らすため、まずはナンバーズだけ生成します。
    # N4とN3のダミーデータを渡して実行！
    generate_numbers_reel("5821", "670")