import os
import math
import requests
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips, ImageClip
from moviepy.audio.fx.all import audio_loop
from dotenv import load_dotenv

# ▼ グラフ生成用のライブラリ（追加）
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg') # 画面に出力せず画像として保存するための設定

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
# 🔍 共通準備（フォント・描画ツール）
# ==========================================
FONT_PATH = "assets/font.ttf"
try:
    # ★ 画面に確実に収まるよう、全体的にフォントサイズを縮小調整しました
    FONT_TITLE = ImageFont.truetype(FONT_PATH, 60)
    FONT_NUM = ImageFont.truetype(FONT_PATH, 80)
    FONT_LIST = ImageFont.truetype(FONT_PATH, 50)
    FONT_HIT = ImageFont.truetype(FONT_PATH, 55)
except:
    FONT_TITLE = FONT_NUM = FONT_LIST = FONT_HIT = ImageFont.load_default()

def draw_text_with_shadow(draw, x, y, text, font, fill_color, shadow_color=(0,0,0,200)):
    draw.text((x+3, y+3), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill_color)

def draw_centered_text(draw, y, text, font, fill_color, screen_w=1920):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (screen_w - (bbox[2] - bbox[0])) / 2
    draw_text_with_shadow(draw, x, y, text, font, fill_color)

def draw_sphere_ball(draw, x, y, r, text, ball_color, font_color=(255, 255, 255)):
    draw.ellipse([x + 4, y + 4, x + 2*r + 4, y + 2*r + 4], fill=(0, 0, 0, 150))
    draw.ellipse([x, y, x + 2*r, y + 2*r], fill=ball_color)
    inner_r, off = int(r * 0.85), int(r * 0.07)
    draw.ellipse([x + off, y + off, x + off + 2*inner_r, y + off + 2*inner_r], fill=tuple(min(255, c + 50) for c in ball_color))
    hl_r = int(r * 0.3)
    draw.ellipse([x + int(r*0.2), y + int(r*0.2), x + int(r*0.2) + 2*hl_r, y + int(r*0.2) + 2*hl_r], fill=(255, 255, 255, 200))
    bbox = draw.textbbox((0, 0), text, font=FONT_NUM)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw_text_with_shadow(draw, x + r - w / 2, y + r - h / 2 - 15, text, FONT_NUM, font_color)

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

def fetch_video_db(bin_id):
    api_key = os.environ.get("JSONBIN_API_KEY")
    if not bin_id or not api_key: return {}
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}", headers={"X-Master-Key": api_key})
        data = res.json().get('record', {})
        if isinstance(data, list): return {}
        return data if res.status_code == 200 else {}
    except: return {}

# ==========================================
# 📊 【新機能】分析グラフ作成職人
# ==========================================
def create_trend_graph_clip(loto6_records):
    """ロト6の直近データから「合計値の推移グラフ」を生成する"""
    duration = 8
    
    # 直近10回分のデータを取り出し、古い順に並べる
    targets = list(reversed(loto6_records[:10]))
    if not targets: return None

    labels = []
    sums = []
    for rec in targets:
        kai = rec.get("target_kai", "").replace("第", "").replace("回", "")
        labels.append(kai)
        # 本数字を数値にして合計
        nums = [int(n) for n in rec.get("actual_main", "").split(",") if n.strip().isdigit()]
        sums.append(sum(nums) if nums else 0)

    # グラフの描画
    plt.figure(figsize=(10, 6), facecolor='#0f172a')
    ax = plt.axes()
    ax.set_facecolor('#0f172a')
    
    # 棒グラフの作成
    bars = plt.bar(labels, sums, color='#0ea5e9')
    plt.title("LOTO6 Recent Main Numbers Sum Trend", color='white', fontsize=18)
    plt.xlabel("Round", color='white')
    plt.ylabel("Sum", color='white')
    ax.tick_params(colors='white')
    
    # 棒の上に数値を表示
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, int(yval), ha='center', color='white', fontweight='bold')

    plt.tight_layout()
    graph_filename = "temp_graph.png"
    plt.savefig(graph_filename, dpi=150)
    plt.close()

    # 生成したグラフ画像を動画クリップにする
    def make_frame(t):
        img = get_base_frame(t)
        draw = ImageDraw.Draw(img)
        draw_centered_text(draw, 100, "■ 直近10回 ロト6 本数字合計値トレンド ■", FONT_TITLE, (52, 211, 153))
        
        # グラフ画像を中央に貼り付け
        graph_img = Image.open(graph_filename).convert("RGBA")
        gw, gh = graph_img.size
        paste_x = int((1920 - gw) / 2)
        paste_y = int((1080 - gh) / 2) + 50
        img.paste(graph_img, (paste_x, paste_y), graph_img)
        
        return np.array(img.convert('RGB'))

    clip = VideoClip(make_frame, duration=duration)
    if os.path.exists("assets/se_tada.mp3"):
        clip = clip.set_audio(AudioFileClip("assets/se_tada.mp3").set_start(0.5))
    return clip

# ==========================================
# 🎬 ロト動画職人 (3シーン構成・SE・ボール演出)
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

        # 📺 シーン1：ボール出現
        if t < 9.0:
            draw_centered_text(draw, 150, f"■ {loto_type} {target_kai} ({date_str}) 結果発表 ■", FONT_TITLE, (56, 189, 248) if loto_type == "LOTO6" else (251, 191, 36))
            ball_r = 80 # 少し縮小
            start_x = 180 if len(actual_main) >= 7 else 280 # 中央寄りに調整
            base_y = 420
            
            for i, num in enumerate(actual_main):
                appear_t = 1.0 + (i * 0.8)
                if t > appear_t:
                    progress = min(1.0, (t - appear_t) * 4.0)
                    y_offset = int(50 * (1.0 - progress))
                    draw_sphere_ball(draw, start_x + (i * 180), base_y + y_offset, ball_r, num, main_color)
            
            bonus_appear_t = 1.0 + (len(actual_main) * 0.8) + 0.5
            if t > bonus_appear_t:
                progress = min(1.0, (t - bonus_appear_t) * 4.0)
                y_offset = int(50 * (1.0 - progress))
                b_x = start_x + (len(actual_main) * 180) + 40
                draw_text_with_shadow(draw, b_x + 10, base_y - 70, "ボーナス", FONT_LIST, (239, 68, 68))
                for i, b_num in enumerate(actual_bonus):
                    draw_sphere_ball(draw, b_x + (i * 170), base_y + y_offset, ball_r, b_num, (220, 38, 38))

        # 📺 シーン2：賞金発表
        elif t < 18.0:
            draw_centered_text(draw, 100, f"【 {target_kai} 当せん金額 と 口数 】", FONT_TITLE, (52, 211, 153))
            if prizes:
                base_prize_y = 250
                for i, p in enumerate(prizes[:6]): # 最大6行までにしてはみ出し防止
                    if t > 9.5 + (i * 0.8):
                        y = base_prize_y + (i * 100)
                        # ★ X座標を内側に寄せて確実に見えるように調整
                        draw_text_with_shadow(draw, 350, y, p.get('grade',''), FONT_LIST, (255, 255, 255))
                        draw_text_with_shadow(draw, 700, y, p.get('prize',''), FONT_NUM, (250, 204, 21))
                        draw_text_with_shadow(draw, 1350, y, p.get('winners',''), FONT_LIST, (156, 163, 175))
            else:
                if t > 10.0: draw_centered_text(draw, 450, "※賞金・口数データは現在集計中です...", FONT_LIST, (200, 200, 200))

            if t > 14.0 and carryover and carryover != "0円":
                blink = int(255 * (0.5 + 0.5 * math.sin(t * 10)))
                draw_centered_text(draw, 900, f"💰 キャリーオーバー: {carryover}", FONT_LIST, (255, blink, 0))

        # 📺 シーン3：予想結果
        else:
            draw_centered_text(draw, 80, f"【 {loto_type} AI予想パターンA〜E 結果 】", FONT_TITLE, (250, 204, 21))
            draw_centered_text(draw, 180, f"本数字: {'  '.join(actual_main)}", FONT_LIST, (255, 255, 255))
            
            base_list_y = 280
            for i, p in enumerate(preds):
                if t > 19.0 + (i * 2.2):
                    y = base_list_y + (i * 130)
                    p_str = ", ".join(p) if isinstance(p, list) else p
                    # ★ 左に寄せて見切れ防止
                    draw_text_with_shadow(draw, 150, y, f"予想{chr(65+i)} :  {p_str}", FONT_LIST, (200, 200, 200))
                    
                    hit_m = len(set(p) & set(actual_main)) if isinstance(p, list) else 0
                    hit_b = len(set(p) & set(actual_bonus)) if isinstance(p, list) else 0
                    hit_color = (52, 211, 153) if hit_m >= 3 else (156, 163, 175)
                    hit_text = f"🎯 {hit_m}個一致" + (f" + B" if hit_b > 0 else "") if hit_m > 0 else "ハズレ"
                    
                    if hit_m >= 4:
                        blink = int(255 * (0.5 + 0.5 * math.sin(t * 15)))
                        hit_color = (255, blink, 0)
                    # ★ 右寄せ位置を1350から1200に内側へ移動
                    draw_text_with_shadow(draw, 1200, y, hit_text, FONT_HIT, hit_color)

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

        # 📺 シーン1：ボール出現
        if t < 8.0:
            draw_centered_text(draw, 100, f"■ ナンバーズ {target_kai} ({date_str}) 結果発表 ■", FONT_TITLE, (52, 211, 153))
            ball_r = 85
            
            draw_text_with_shadow(draw, 250, 300, "【 ナンバーズ4 】", FONT_TITLE, (255, 255, 255))
            for i, num in enumerate(list(actual_n4)):
                appear_t = 1.0 + (i * 0.5)
                if t > appear_t:
                    progress = min(1.0, (t - appear_t) * 4.0)
                    draw_sphere_ball(draw, 120 + (i * 180), 450 + int(50 * (1.0 - progress)), ball_r, num, (22, 163, 74))

            draw_text_with_shadow(draw, 1150, 300, "【 ナンバーズ3 】", FONT_TITLE, (255, 255, 255))
            for i, num in enumerate(list(actual_n3)):
                appear_t = 3.5 + (i * 0.5)
                if t > appear_t:
                    progress = min(1.0, (t - appear_t) * 4.0)
                    draw_sphere_ball(draw, 1150 + (i * 180), 450 + int(50 * (1.0 - progress)), ball_r, num, (217, 119, 6))

        # 📺 シーン2：賞金発表
        elif t < 16.0:
            draw_centered_text(draw, 80, "【 当せん金額 と 口数 】", FONT_TITLE, (52, 211, 153))
            
            draw_text_with_shadow(draw, 200, 200, "■ ナンバーズ4", FONT_LIST, (22, 163, 74))
            if n4_prizes:
                for i, p in enumerate(n4_prizes):
                    if t > 8.5 + (i * 0.5):
                        y = 300 + (i * 80)
                        # ★ 位置を内側に寄せる
                        draw_text_with_shadow(draw, 80, y, p.get('grade',''), FONT_LIST, (255, 255, 255))
                        draw_text_with_shadow(draw, 450, y, p.get('prize',''), FONT_LIST, (250, 204, 21))
            else:
                if t > 9.0: draw_text_with_shadow(draw, 200, 400, "※集計中...", FONT_LIST, (200, 200, 200))

            draw_text_with_shadow(draw, 1100, 200, "■ ナンバーズ3", FONT_LIST, (217, 119, 6))
            if n3_prizes:
                for i, p in enumerate(n3_prizes):
                    if t > 10.5 + (i * 0.5):
                        y = 300 + (i * 80)
                        # ★ 位置を内側に寄せる
                        draw_text_with_shadow(draw, 950, y, p.get('grade',''), FONT_LIST, (255, 255, 255))
                        draw_text_with_shadow(draw, 1300, y, p.get('prize',''), FONT_LIST, (250, 204, 21))
            else:
                if t > 11.0: draw_text_with_shadow(draw, 1100, 400, "※集計中...", FONT_LIST, (200, 200, 200))

        # 📺 シーン3：予想結果
        else:
            draw_centered_text(draw, 80, "【 AI予想パターン 答え合わせ 】", FONT_TITLE, (250, 204, 21))
            draw_text_with_shadow(draw, 150, 180, f"N4 本数字: {actual_n4}", FONT_LIST, (255, 255, 255))
            draw_text_with_shadow(draw, 1100, 180, f"N3 本数字: {actual_n3}", FONT_LIST, (255, 255, 255))

            for i in range(5):
                if t > 16.5 + (i * 1.0):
                    y = 300 + (i * 120)
                    p4 = n4_preds[i] if i < len(n4_preds) else "----"
                    # ★ N4のテキストを内側へ
                    draw_text_with_shadow(draw, 50, y, f"予想{chr(65+i)}: {p4}", FONT_LIST, (200, 200, 200))
                    if p4 == actual_n4: res, col = "🎯ストレート", (255, 100, 100)
                    elif sorted(p4) == sorted(actual_n4) and actual_n4 != "----": res, col = "🎯ボックス", (255, 150, 0)
                    else: res, col = "ハズレ", (150, 150, 150)
                    draw_text_with_shadow(draw, 480, y, res, FONT_LIST, col)

                    p3 = n3_preds[i] if i < len(n3_preds) else "---"
                    # ★ N3のテキストを内側へ
                    draw_text_with_shadow(draw, 950, y, f"予想{chr(65+i)}: {p3}", FONT_LIST, (200, 200, 200))
                    if p3 == actual_n3: res, col = "🎯ストレート", (255, 100, 100)
                    elif sorted(p3) == sorted(actual_n3) and actual_n3 != "---": res, col = "🎯ボックス", (255, 150, 0)
                    else: res, col = "ハズレ", (150, 150, 150)
                    draw_text_with_shadow(draw, 1350, y, res, FONT_LIST, col)

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
    
    # データ取得
    n_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID_NUMBERS"), 5)
    l6_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID"), 2)
    l7_hist = fetch_finished_history(os.environ.get("JSONBIN_BIN_ID_LOTO7"), 1)

    v_db_n = fetch_video_db(os.environ.get("JSONBIN_BIN_ID_VIDEO_NUMBERS"))
    v_db_l6 = fetch_video_db(os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO6"))
    v_db_l7 = fetch_video_db(os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO7"))

    # クリップ生成
    for rec in reversed(n_hist):
        kai = rec.get("target_kai")
        if kai in v_db_n:
            rec["date"] = v_db_n[kai].get("date", "----/--/--")
            rec["n4_prizes"] = v_db_n[kai].get("n4_prizes", [])
            rec["n3_prizes"] = v_db_n[kai].get("n3_prizes", [])
        all_clips.append(create_numbers_clip(rec))

    for rec in reversed(l6_hist):
        kai = rec.get("target_kai")
        if kai in v_db_l6:
            rec["date"] = v_db_l6[kai].get("date", "----/--/--")
            rec["prizes"] = v_db_l6[kai].get("prizes", [])
            rec["carryover"] = v_db_l6[kai].get("carryover", "0円")
        all_clips.append(create_loto_clip(rec, "LOTO6"))

    for rec in reversed(l7_hist):
        kai = rec.get("target_kai")
        if kai in v_db_l7:
            rec["date"] = v_db_l7[kai].get("date", "----/--/--")
            rec["prizes"] = v_db_l7[kai].get("prizes", [])
            rec["carryover"] = v_db_l7[kai].get("carryover", "0円")
        all_clips.append(create_loto_clip(rec, "LOTO7"))

    # ★【新機能】最後にトレンドグラフの動画シーンを追加する
    if l6_hist:
        print("📊 分析グラフ（ロト6合計値トレンド）のシーンを生成中...")
        graph_clip = create_trend_graph_clip(l6_hist) # 直近履歴を渡す
        if graph_clip:
            all_clips.append(graph_clip)

    if not all_clips:
        print("❌ 生成できるデータがありませんでした。")
        return

    print(f"\n🎞️ 全 {len(all_clips)} シーンを結合中... (レンダリングには数分かかります)")
    final_video = concatenate_videoclips(all_clips, method="compose")
    
    if bgm_clip:
        print("🎧 全体にBGMを合成します...")
        looped_bgm = audio_loop(bgm_clip, duration=final_video.duration).volumex(0.3)
        final_audio = CompositeAudioClip([looped_bgm, final_video.audio])
        final_video = final_video.set_audio(final_audio)

    output_filename = "weekly_summary.mp4"
    final_video.write_videofile(
        output_filename, fps=24, codec="libx264", audio_codec="libmp3lame", threads=4
    )
    
    # 終わったら一時的なグラフ画像を消しておく
    if os.path.exists("temp_graph.png"):
        os.remove("temp_graph.png")
        
    print(f"\n🎉🎉🎉 1週間まとめ動画が完成しました！ => {output_filename} 🎉🎉🎉")

if __name__ == "__main__":
    generate_weekly_video()