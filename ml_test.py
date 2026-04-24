import numpy as np
import pandas as pd
from collections import Counter
import itertools
from sklearn.ensemble import RandomForestClassifier
import requests
from bs4 import BeautifulSoup
import re
import datetime

# ==========================================
# 1. データ取得機能（AI学習用に強化版：過去3年分を取得）
# ==========================================
def fetch_real_history_data():
    print("☁️ 楽天宝くじから過去の履歴データを取得中（AI学習のため過去3年分）...")
    base_url = "https://takarakuji.rakuten.co.jp/backnumber/loto7/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    history_data = []
    
    today = datetime.date.today()
    target_urls = [f"{base_url}lastresults/"]
    
    # 過去36ヶ月（3年分）のURLを生成
    for i in range(1, 36):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        target_urls.append(f"{base_url}{y}{m:02d}/")
    
    for url in target_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200: continue
            res.encoding = 'euc-jp'
            soup = BeautifulSoup(res.content, 'html.parser')
            
            text = soup.get_text(separator=' ')
            
            for m in re.finditer(r'第\s*(\d+)\s*回', text):
                kai_num = m.group(1).zfill(4)
                kai_str = f"第{kai_num}回"
                
                chunk = text[m.end():m.end() + 300]
                next_kai_match = re.search(r'第\s*\d+\s*回', chunk)
                if next_kai_match:
                    chunk = chunk[:next_kai_match.start()]
                
                date_m = re.search(r'(\d{4})[/年]\s*(\d{1,2})\s*[/月]\s*(\d{1,2})', chunk)
                if not date_m: continue
                
                date_str = f"{date_m.group(1)}/{date_m.group(2).zfill(2)}/{date_m.group(3).zfill(2)}"
                num_chunk = chunk[date_m.end():]
                all_digits = re.findall(r'\d+', num_chunk)
                
                valid_nums = [n.zfill(2) for n in all_digits if 1 <= int(n) <= 37]
                
                if len(valid_nums) >= 9:
                    main_nums = valid_nums[:7]
                    bonus_nums = valid_nums[7:9]
                    
                    if not any(d['kai'] == kai_str for d in history_data):
                        history_data.append({
                            "kai": kai_str,
                            "date": date_str,
                            "main": main_nums,
                            "bonus": bonus_nums
                        })
        except Exception:
            pass # エラーはスキップ
            
    # 最新の回号が一番上に来るように並び替え
    history_data.sort(key=lambda x: int(re.search(r'\d+', x['kai']).group()), reverse=True)
    print(f"✅ 合計 {len(history_data)} 回分の過去データを取得しました！")
    return history_data

# ==========================================
# 2. ハイブリッドAI 予測アルゴリズム
# ==========================================
def generate_hybrid_predictions(history_data):
    print("🧠 AIが過去の傾向と数字の相性（共起性）を学習中...")
    if not history_data or len(history_data) < 20:
        return [] 

    main_draws = [list(map(int, d['main'])) for d in reversed(history_data)]
    
    # --- 1. 共起性行列（ペア相性）の作成 ---
    pair_counts = Counter()
    for draw in main_draws:
        for pair in itertools.combinations(sorted(draw), 2):
            pair_counts[pair] += 1

    # --- 2. 機械学習のためのデータセット作成 ---
    features = []
    labels = []
    window_size = 10 
    
    for i in range(window_size, len(main_draws) - 1):
        past_window = [num for draw in main_draws[i-window_size:i] for num in draw]
        past_counts = Counter(past_window)
        
        target_draw = main_draws[i] 
        for num in range(1, 38):
            feature = [past_counts.get(num, 0)]
            features.append(feature)
            labels.append(1 if num in target_draw else 0)

    X = np.array(features)
    y = np.array(labels)

    # --- 3. モデルの学習 (Random Forest) ---
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    model.fit(X, y)

    # --- 4. 次回の予測スコアを算出 ---
    latest_window = [num for draw in main_draws[-window_size:] for num in draw]
    latest_counts = Counter(latest_window)
    
    next_features = np.array([[latest_counts.get(num, 0)] for num in range(1, 38)])
    probabilities = model.predict_proba(next_features)[:, 1] 
    
    ml_scores = {num: prob for num, prob in enumerate(probabilities, start=1)}

    # --- 5. ハイブリッド選定（MLスコア × 共起性） ---
    predictions = []
    seen = set()
    import random
    numbers = list(range(1, 38))
    weights = [ml_scores[n] for n in numbers]

    candidates = []
    for _ in range(3000): # より精度の高い組み合わせを見つけるため3000パターン生成
        cand = []
        pool_nums = list(numbers)
        pool_weights = list(weights)
        for _ in range(7):
            if sum(pool_weights) > 0:
                choice = random.choices(pool_nums, weights=pool_weights)[0]
            else:
                choice = random.choice(pool_nums)
            cand.append(choice)
            idx = pool_nums.index(choice)
            pool_nums.pop(idx)
            pool_weights.pop(idx)
        cand.sort()
        candidates.append(cand)

    valid_candidates = []
    for cand in candidates:
        base_score = sum(ml_scores[n] for n in cand)
        
        pair_bonus = 0
        for pair in itertools.combinations(cand, 2):
            pair_bonus += pair_counts.get(pair, 0)
            
        final_score = base_score + (pair_bonus * 0.05)
        valid_candidates.append((final_score, cand))

    valid_candidates.sort(key=lambda x: x[0], reverse=True)
    for score, cand in valid_candidates:
        t_cand = tuple(cand)
        if t_cand not in seen:
            seen.add(t_cand)
            predictions.append([str(n).zfill(2) for n in cand])
        if len(predictions) == 5:
            break

    return predictions

# ==========================================
# 実行ブロック
# ==========================================
if __name__ == "__main__":
    print("--- 🚀 ロト7 ハイブリッドAIテスト開始 ---")
    # 1. 実データの取得
    real_history = fetch_real_history_data()
    
    if real_history:
        print(f"最新のデータ: {real_history[0]['kai']} ({real_history[0]['date']})")
        
        # 2. AIによる予測生成
        result = generate_hybrid_predictions(real_history)
        
        print("\n🎯 導き出された最新のAI予想:")
        for i, res in enumerate(result, 1):
            print(f"予想{i}: {res}")
    else:
        print("データの取得に失敗しました。")
    print("--- 🏁 テスト完了 ---")