import random

# 1. ロト7の予想番号（7個）を生成する関数
def generate_numbers():
    numbers = sorted(random.sample(range(1, 38), 7))
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
                </div>'''
new_html_content += '\n            </div>'

# 3. loto7.html を読み込む
with open('loto7.html', 'r', encoding='utf-8') as file:
    html_data = file.read()

# 4. 超安全な書き換えロジック（ハサミで切って間に挟む方式）
start_marker = ""
end_marker = ""

if start_marker in html_data and end_marker in html_data:
    # 目印より「前」のHTMLと、「後」のHTMLを切り分ける
    before_html = html_data.split(start_marker)[0]
    after_html = html_data.split(end_marker)[1]
    
    # 前 + 目印 + 新しい予想 + 目印 + 後 で合体させる
    updated_html = before_html + start_marker + "\n            " + new_html_content + "\n            " + end_marker + after_html
    
    # 5. 上書き保存する
    with open('loto7.html', 'w', encoding='utf-8') as file:
        file.write(updated_html)
    print("大成功！デザインを保ったままロト7の予想番号を更新しました！")
else:
    print("エラー：loto7.html の中に目印が見つかりません。")