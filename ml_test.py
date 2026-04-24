import numpy as np
import pandas as pd
from collections import Counter
import itertools
from sklearn.ensemble import RandomForestClassifier

def generate_hybrid_predictions(history_data):
    """
    機械学習(個別の確率) × 共起性分析(ペア相性) のハイブリッド予想
    """
    if not history_data or len(history_data) < 20:
        return [] # データが少なすぎる場合はスキップ

    # 過去データから本数字のみを古い順(時系列)に並び替え
    main_draws = [list(map(int, d['main'])) for d in reversed(history_data)]
    
    # ==========================================
    # 1. 共起性行列（ペア相性）の作成
    # ==========================================
    pair_counts = Counter()
    for draw in main_draws:
        # 1回の抽選結果(7個)から作られるすべての2個の組み合わせをカウント
        for pair in itertools.combinations(sorted(draw), 2):
            pair_counts[pair] += 1

    # ==========================================
    # 2. 機械学習のためのデータセット作成
    # ==========================================
    # AIに学習させる「過去の傾向（特徴量）」を作ります
    features = []
    labels = []
    
    # 過去10回分のデータを見て、次の回を予測するモデル
    window_size = 10 
    
    for i in range(window_size, len(main_draws) - 1):
        # 過去10回分の抽選データを1つの配列に平坦化
        past_window = [num for draw in main_draws[i-window_size:i] for num in draw]
        past_counts = Counter(past_window)
        
        # 1〜37の各数字について、特徴量と正解ラベルを作成
        target_draw = main_draws[i] # 予測したい「次の回」の結果
        for num in range(1, 38):
            # 特徴量: 過去10回で何回出たか
            feature = [past_counts.get(num, 0)]
            features.append(feature)
            # ラベル: 実際に出たか(1)、出なかったか(0)
            labels.append(1 if num in target_draw else 0)

    X = np.array(features)
    y = np.array(labels)

    # ==========================================
    # 3. モデルの学習 (Random Forest)
    # ==========================================
    # AIモデルの初期化と学習の実行
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    model.fit(X, y)

    # ==========================================
    # 4. 次回（最新）の予測スコアを算出
    # ==========================================
    latest_window = [num for draw in main_draws[-window_size:] for num in draw]
    latest_counts = Counter(latest_window)
    
    next_features = np.array([[latest_counts.get(num, 0)] for num in range(1, 38)])
    # 各数字が次に出る確率(0.0〜1.0)を予測
    probabilities = model.predict_proba(next_features)[:, 1] 
    
    # 数字と確率を紐付け ( {1: 0.85, 2: 0.12, ...} )
    ml_scores = {num: prob for num, prob in enumerate(probabilities, start=1)}

    # ==========================================
    # 5. ハイブリッド選定（MLスコア × 共起性）
    # ==========================================
    predictions = []
    seen = set()
    
    import random
    numbers = list(range(1, 38))
    # MLスコアを重みとして使う
    weights = [ml_scores[n] for n in numbers]

    candidates = []
    # 候補を多めに(2000個)生成
    for _ in range(2000):
        cand = []
        pool_nums = list(numbers)
        pool_weights = list(weights)
        for _ in range(7):
            # 確率の合計が0より大きい場合のみ重み付き抽出
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
        # MLのベーススコア
        base_score = sum(ml_scores[n] for n in cand)
        
        # ★共起性(ペア)ボーナスの加算
        pair_bonus = 0
        for pair in itertools.combinations(cand, 2):
            pair_bonus += pair_counts.get(pair, 0)
            
        # ボーナスの影響度を調整（例: 共起回数1回につき0.05ポイント加算など）
        final_score = base_score + (pair_bonus * 0.05)
        valid_candidates.append((final_score, cand))

    # 最終スコア順にソートして上位5つを獲得
    valid_candidates.sort(key=lambda x: x[0], reverse=True)
    for score, cand in valid_candidates:
        t_cand = tuple(cand)
        if t_cand not in seen:
            seen.add(t_cand)
            predictions.append([str(n).zfill(2) for n in cand])
        if len(predictions) == 5:
            break

    return predictions

# --- テスト実行用 ---
if __name__ == "__main__":
    # テスト用のダミーデータ（過去の配列）
    # ※実際はJSONBinから取得したデータを使用します
    dummy_history = [
        {"main": ["01", "05", "12", "15", "22", "30", "35"]},
        {"main": ["02", "05", "13", "18", "25", "31", "36"]},
        # ... 本来はここに数十〜数百の履歴が入る
    ] * 20 # ダミーで水増し
    
    print("🤖 ハイブリッドAIで予測を生成中...")
    result = generate_hybrid_predictions(dummy_history)
    for i, res in enumerate(result, 1):
        print(f"予想{i}: {res}")