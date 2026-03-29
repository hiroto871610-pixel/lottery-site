import random
import re

# 1. ロト7の予想番号（7個）を生成する関数
def generate_numbers():
    numbers = sorted(random.sample(range(1, 38), 7))
    # 数字を2桁の文字列にする（例: 3 -> "03"）
    return [str(n).zfill(2) for n in numbers]

# 2. 新しいHTMLのパーツを組み立てる
new_html_content = '<div class="prediction-box">\n'
labels = ['予想A', '予想B', '予想C', '予想D', '予想E']

for label in labels:
    nums = generate_numbers()
    balls_html = "".join([f'<span class="ball">{n}</span>' for n in nums])
    
    new_html_content += f'''
    <div class="numbers-row">
        <div class="row-label">{label}</div>
        <div class="ball-container">
            {balls_html}
        </div>
    </div>
    '''
new_html_content += '</div>'

# 3. loto7.html を読み込む
with open('loto7.html', 'r', encoding='utf-8') as file:
    html_data = file.read()

# 4. と の間を、新しいHTMLに差し替える
pattern = r'()(.*?)()'
updated_html = re.sub(pattern, rf'\1\n{new_html_content}\n\3', html_data, flags=re.DOTALL)

# 5. 上書き保存する
with open('loto7.html', 'w', encoding='utf-8') as file:
    file.write(updated_html)

print("ロト7の予想番号を自動更新しました！")