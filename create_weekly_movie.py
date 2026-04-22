import os
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
import moviepy.video.fx.all as vfx
import moviepy.audio.fx.all as afx

def generate_weekly_video():
    print("🎬 週末まとめ動画の生成を開始します...")
    
    TARGET_DURATION = 490  # 8分10秒（収益化条件）

    # ==========================================
    # 1. 音声の準備（バグ修正：一番最後に合成します）
    # ==========================================
    bgm_clip = AudioFileClip("assets/create_weekly.mp3")
    bgm_clip = afx.audio_loop(bgm_clip, duration=TARGET_DURATION).volumex(0.3)
    
    # ==========================================
    # 2. 背景動画の準備（横長の空間を作る）
    # ==========================================
    bg_clip = VideoFileClip("assets/create_weekly.mp4")
    bg_clip = vfx.loop(bg_clip, duration=TARGET_DURATION)
    clips = [bg_clip]
    
    # ==========================================
    # 3. 静止画ではなく「本物の動画」をオシャレに配置する
    # ==========================================
    # すでに自動生成されているショート動画をリスト化
    video_files = ["reel_loto6.mp4", "reel_loto7.mp4", "reel_numbers.mp4"]
    
    current_time = 5  # 最初の5秒は背景とBGMだけで「タメ」を作る
    
    for v_file in video_files:
        if os.path.exists(v_file):
            print(f"🎥 {v_file} を映像ソースとして組み込みます...")
            vid = VideoFileClip(v_file)
            
            # 【オシャレ演出1】縦型動画を少し縮小して、画面中央に配置
            # （これにより、後ろの背景動画がフチのように見えてプロっぽくなります）
            vid = vid.resize(height=900) 
            
            # 【オシャレ演出2】パッと切り替わらず、1秒かけてフワッと現れ、消える
            vid = vid.crossfadein(1).crossfadeout(1)
            
            # 出現タイミングと位置をセット
            vid = vid.set_position("center").set_start(current_time)
            clips.append(vid)
            
            # 次の動画は、今の動画が終わった「2秒後」からスタートさせる
            current_time += vid.duration + 2

    # ==========================================
    # 4. 最終合成（音声を確実にくっつける！）
    # ==========================================
    final_video = CompositeVideoClip(clips)
    
    # ここが最重要！合成が終わった「最後の最後」に音声をセットすることで音消えバグを防ぐ
    final_video = final_video.set_audio(bgm_clip)
    
    print("⏳ レンダリング（動画書き出し）を実行中...しばらくお待ちください！")
    final_video.write_videofile(
        "weekly_movie_v2.mp4", 
        fps=30, 
        codec="libx264", 
        audio_codec="aac"
    )
    print("🎉🎉🎉 オシャレな長尺動画『weekly_movie_v2.mp4』が完成しました！ 🎉🎉🎉")

if __name__ == "__main__":
    generate_weekly_video()