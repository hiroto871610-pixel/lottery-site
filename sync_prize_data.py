import os
import requests
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("JSONBIN_API_KEY")

# ★ 動画専用のBIN IDを指定
BINS_VIDEO = {
    "LOTO6": os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO6"),
    "LOTO7": os.environ.get("JSONBIN_BIN_ID_VIDEO_LOTO7"),
    "NUMBERS": os.environ.get("JSONBIN_BIN_ID_VIDEO_NUMBERS")
}

def get_video_db(bin_id):
    """動画専用DB(辞書型)を取得"""
    if not bin_id or not API_KEY: return {}
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}", headers={"X-Master-Key": API_KEY})
        return res.json().get('record', {}) if res.status_code == 200 else {}
    except: return {}

def save_video_db(bin_id, data):
    """動画専用DBへ保存"""
    if not bin_id or not API_KEY: return
    try:
        requests.put(f"https://api.jsonbin.io/v3/b/{bin_id}", json={"record": data}, headers={"Content-Type": "application/json", "X-Master-Key": API_KEY})
    except Exception as e: print(f"保存エラー: {e}")

def fetch_loto_details(loto_type):
    url = f"https://takarakuji.rakuten.co.jp/backnumber/{loto_type}/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    result = {"round": "", "date": "", "prizes": [], "carryover": "0円"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'euc-jp'
        soup = BeautifulSoup(res.content, 'html.parser')

        target_table = None
        for table in soup.find_all('table'):
            if '本数字' in table.get_text() and '1等' in table.get_text():
                target_table = table
                break
        
        if not target_table: return result

        for tr in target_table.find_all('tr'):
            header_text = tr.get_text(strip=True)
            for i in range(1, 8):
                if f'{i}等' in header_text:
                    tds = tr.find_all('td')
                    if len(tds) >= 2:
                        result["prizes"].append({"grade": f"{i}等", "winners": tds[-2].get_text(strip=True), "prize": tds[-1].get_text(strip=True)})
            if 'キャリーオーバー' in header_text:
                tds = tr.find_all('td')
                if tds: result["carryover"] = tds[-1].get_text(strip=True)

        text = target_table.get_text(separator=' ', strip=True)
        m_round = re.search(r'第\s*\d+\s*回', text)
        m_date = re.search(r'\d{4}[年/]\d{1,2}[月/]\d{1,2}日?', text)
        if m_round: result["round"] = m_round.group().replace(' ', '')
        if m_date: result["date"] = m_date.group()

        return result
    except: return result

def fetch_numbers_details():
    headers = {'User-Agent': 'Mozilla/5.0'}
    result = {"round": "", "date": "", "n4_prizes": [], "n3_prizes": []}
    try:
        res4 = requests.get("https://takarakuji.rakuten.co.jp/backnumber/numbers4/", headers=headers)
        res4.encoding = 'euc-jp'
        soup4 = BeautifulSoup(res4.content, 'html.parser')
        
        for heading in soup4.find_all(['h1', 'h2', 'h3', 'div', 'p']):
            h_text = heading.get_text(separator=' ', strip=True)
            if '第' in h_text and '回' in h_text and 'ナンバーズ4' in h_text:
                m_round = re.search(r'第\s*\d+\s*回', h_text)
                m_date = re.search(r'\d{4}[年/]\d{1,2}[月/]\d{1,2}日?', h_text)
                if m_round: result["round"] = m_round.group().replace(' ', '')
                if m_date: result["date"] = m_date.group()
                break

        for table in soup4.find_all('table'):
            if 'ストレート' in table.get_text() and 'ボックス' in table.get_text():
                for tr in table.find_all('tr'):
                    header = tr.get_text(strip=True).replace(' ', '').replace('　', '')
                    grade = None
                    if 'セット' in header and 'ストレート' in header: grade = 'セット(ストレート)'
                    elif 'セット' in header and 'ボックス' in header: grade = 'セット(ボックス)'
                    elif 'ストレート' in header: grade = 'ストレート'
                    elif 'ボックス' in header: grade = 'ボックス'
                    if grade:
                        tds = tr.find_all('td')
                        if len(tds) >= 2: result["n4_prizes"].append({"grade": grade, "winners": tds[-2].get_text(strip=True), "prize": tds[-1].get_text(strip=True)})
                break

        res3 = requests.get("https://takarakuji.rakuten.co.jp/backnumber/numbers3/", headers=headers)
        res3.encoding = 'euc-jp'
        soup3 = BeautifulSoup(res3.content, 'html.parser')
        for table in soup3.find_all('table'):
            if 'ストレート' in table.get_text() and 'ミニ' in table.get_text():
                for tr in table.find_all('tr'):
                    header = tr.get_text(strip=True).replace(' ', '').replace('　', '')
                    grade = None
                    if 'セット' in header and 'ストレート' in header: grade = 'セット(ストレート)'
                    elif 'セット' in header and 'ボックス' in header: grade = 'セット(ボックス)'
                    elif 'ストレート' in header: grade = 'ストレート'
                    elif 'ボックス' in header: grade = 'ボックス'
                    elif 'ミニ' in header: grade = 'ミニ'
                    if grade:
                        tds = tr.find_all('td')
                        if len(tds) >= 2: result["n3_prizes"].append({"grade": grade, "winners": tds[-2].get_text(strip=True), "prize": tds[-1].get_text(strip=True)})
                break
        return result
    except: return result

def update_video_db():
    print("🔄 動画専用BINへのデータ収集を開始します...")
    
    # ロト6
    l6 = fetch_loto_details("loto6")
    if l6["round"]:
        db = get_video_db(BINS_VIDEO["LOTO6"])
        db[l6["round"]] = l6 # 回号をキーにして保存
        save_video_db(BINS_VIDEO["LOTO6"], db)
        print(f"✅ ロト6 ({l6['round']}) を動画用DBに保存しました！")

    # ロト7
    l7 = fetch_loto_details("loto7")
    if l7["round"]:
        db = get_video_db(BINS_VIDEO["LOTO7"])
        db[l7["round"]] = l7
        save_video_db(BINS_VIDEO["LOTO7"], db)
        print(f"✅ ロト7 ({l7['round']}) を動画用DBに保存しました！")

    # ナンバーズ
    num = fetch_numbers_details()
    if num["round"]:
        db = get_video_db(BINS_VIDEO["NUMBERS"])
        db[num["round"]] = num
        save_video_db(BINS_VIDEO["NUMBERS"], db)
        print(f"✅ ナンバーズ ({num['round']}) を動画用DBに保存しました！")

if __name__ == "__main__":
    update_video_db()