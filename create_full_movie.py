import os
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip
import moviepy.video.fx.all as vfx

# ==========================================
# 🛠️ 共通ツール：テロップ画像生成職人
# （MoviePyの文字化けを防ぐため、Pillowで透明な文字画像を作ります）
# ==========================================
def create_text_image(text, filename, font_size=80, color="white"):
    # ※assetsフォルダに font.ttf を入れておいてください
    font_path = "assets/font.ttf"
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        # フォントがない場合はデフォルト（英語のみ）になるため注意
        font = ImageFont.load_default()
        print("⚠️ font.ttf が見つかりません！")

    # 文字のサイズを計算して、透明な画像キャンバスを作成
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    img_w, img_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    img = Image.new("RGBA", (img_w + 20, img_h + 20), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 黒いフチドリをつけて文字を目立たせる
    x, y = 10, 10
    outline_color = "black"
    for adj in range(-3, 4):
        draw.text((x+adj, y), text, font=font, fill=outline_color)
        draw.text((x, y+adj), text, font=font, fill=outline_color)
    # メインの文字
    draw.text((x, y), text, font=font, fill=color)
    
    img.save(filename)
    return filename

# ==========================================
# 🎬 本編：テレビ番組風 動画生成
# ==========================================
def generate_tv_show():
    print("🎬 本格的テレビ番組風の動画生成を開始します...")
    
    # 背景とBGMを準備（まずはテスト用に1分間だけ切り出す）
    TEST_DURATION = 60
    bg_clip = VideoFileClip("assets/bg.mp4").subclip(0, TEST_DURATION)
    bgm_clip = AudioFileClip("assets/bgm.mp3").subclip(0, TEST_DURATION).volumex(0.2)
    
    clips = [bg_clip]
    audios = [bgm_clip]

    # ------------------------------------------------
    # 📺 オープニング（0秒〜15秒）
    # ------------------------------------------------
    print("生成中: オープニング...")
    # タイトル文字を生成
    title_file = create_text_image("今週のAI宝くじ予想\n結果＆来週の激アツ数字まとめ", "temp_title.png", font_size=90, color="gold")
    date_file = create_text_image("第2095回〜 最新版", "temp_date.png", font_size=60, color="white")

    # タイトルをフェードインで中央に表示（1秒目〜10秒目）
    title_clip = ImageClip(title_file).set_position("center").set_start(1).set_duration(9).crossfadein(2).crossfadeout(1)
    # 日付は少し遅れて下の方に出現
    date_clip = ImageClip(date_file).set_position(("center", 700)).set_start(3).set_duration(7).crossfadein(1).crossfadeout(1)
    
    clips.extend([title_clip, date_clip])

    # ------------------------------------------------
    # 📺 ブロック1：結果発表（15秒〜）
    # ------------------------------------------------
    print("生成中: 結果発表ブロック...")
    # コーナータイトル
    header_file = create_text_image("【 今 週 の 結 果 発 表 】", "temp_head.png", font_size=100, color="cyan")
    header_clip = ImageClip(header_file).set_position(("center", 100)).set_start(12).set_duration(20).crossfadein(1)
    clips.append(header_clip)

    # 演出：ナンバーズの予想結果
    n4_text = create_text_image("ナンバーズ4 予想A", "temp_n4.png", font_size=70)
    n4_clip = ImageClip(n4_text).set_position(("center", 400)).set_start(15).set_duration(17)
    
    # 演出：ドラムロール音を15秒目から鳴らす（もしSEファイルがあれば）
    if os.path.exists("assets/se_drumroll.mp3"):
        drum = AudioFileClip("assets/se_drumroll.mp3").set_start(15).volumex(1.0)
        audios.append(drum)

    # もったいぶって、結果の文字を遅れて（18秒目から）表示
    hit_text = create_text_image("★ ボックス 的中！！ ★", "temp_hit.png", font_size=120, color="red")
    hit_clip = ImageClip(hit_text).set_position(("center", 600)).set_start(18).set_duration(14).crossfadein(0.5)
    
    # 結果表示と同時に「ジャジャーン！」音を鳴らす
    if os.path.exists("assets/se_tada.mp3"):
        tada = AudioFileClip("assets/se_tada.mp3").set_start(18).volumex(1.0)
        audios.append(tada)

    clips.extend([n4_clip, hit_clip])

    # ------------------------------------------------
    # 🎬 最終合成と書き出し
    # ------------------------------------------------
    final_video = CompositeVideoClip(clips)
    final_audio = CompositeAudioClip(audios)
    final_video = final_video.set_audio(final_audio)
    
    print("⏳ テスト版（1分）のエンコードを実行中...")
    final_video.write_videofile("tv_show_test.mp4", fps=30, codec="libx264", audio_codec="aac")
    print("🎉 テスト動画が完成しました！")

if __name__ == "__main__":
    generate_tv_show()