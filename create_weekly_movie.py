import os
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
import moviepy.video.fx.all as vfx
import moviepy.audio.fx.all as afx

def generate_weekly_video():
    print("🎬 週末まとめ動画（8分超え）の生成を開始します...")
    
    # 収益化の壁「8分（480秒）」を確実に超えるため、8分10秒（490秒）に設定
    TARGET_DURATION = 490 

    # ==========================================
    # 1. オシャレな背景とBGMを8分間ループさせる
    # ==========================================
    # 背景動画を読み込み、指定した時間までループ（繰り返し）させる
    bg_clip = VideoFileClip("assets/create_weekly.mp4")
    bg_clip = vfx.loop(bg_clip, duration=TARGET_DURATION)
    
    # BGMを読み込み、同じくループさせる
    bgm_clip = AudioFileClip("assets/create_weekly.mp3")
    bgm_clip = afx.audio_loop(bgm_clip, duration=TARGET_DURATION)
    
    # BGMの音量が大きすぎると視聴者が疲れるので、30%に下げる
    bgm_clip = bgm_clip.volumex(0.3)
    
    # 背景動画にBGMをセット
    bg_clip = bg_clip.set_audio(bgm_clip)

    # 合成用のリストを作成（まずは一番下に背景を置く）
    clips = [bg_clip]

    # ==========================================
    # 2. 【テスト】既存の画像を「スライド」として重ねる
    # ==========================================
    # もし手元にロト6の予想画像があれば、5秒目からふんわり登場させる
    if os.path.exists("loto6_result.jpg"):
        print("📸 予想画像をスライドとして追加します...")
        slide = ImageClip("loto6_result.jpg").set_duration(15) # 15秒間表示
        slide = slide.set_position("center").set_start(5)      # 5秒目から開始
        
        # オシャレ演出：2秒かけてフェードイン、2秒かけてフェードアウト
        slide = slide.crossfadein(2).crossfadeout(2)
        clips.append(slide)

    # ==========================================
    # 3. 最終書き出し（レンダリング）
    # ==========================================
    # すべてのパーツ（背景＋スライド）を合成
    final_video = CompositeVideoClip(clips)
    
    print("⏳ 動画の書き出し（エンコード）を実行中... ※数分〜数十分かかります")
    # YouTubeに最適な設定でMP4として保存
    final_video.write_videofile(
        "weekly_movie.mp4", 
        fps=30, 
        codec="libx264", 
        audio_codec="aac"
    )
    print("🎉🎉🎉 8分の長尺動画『weekly_movie.mp4』が完成しました！ 🎉🎉🎉")

if __name__ == "__main__":
    generate_weekly_video()