import os
import datetime
import random
import requests
import urllib.request
import base64
from PIL import Image, ImageDraw, ImageFont
import time
import json
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# =========================================================
# 星座と占いテキストのデータ定義（★大増量版★）
# =========================================================
ZODIACS = [
    {"name": "牡羊座", "date": "3/21〜4/19", "emoji": "♈"},
    {"name": "牡牛座", "date": "4/20〜5/20", "emoji": "♉"},
    {"name": "双子座", "date": "5/21〜6/21", "emoji": "♊"},
    {"name": "蟹座",   "date": "6/22〜7/22", "emoji": "♋"},
    {"name": "獅子座", "date": "7/23〜8/22", "emoji": "♌"},
    {"name": "乙女座", "date": "8/23〜9/22", "emoji": "♍"},
    {"name": "天秤座", "date": "9/23〜10/23", "emoji": "♎"},
    {"name": "蠍座",   "date": "10/24〜11/22", "emoji": "♏"},
    {"name": "射手座", "date": "11/23〜12/21", "emoji": "♐"},
    {"name": "山羊座", "date": "12/22〜1/19", "emoji": "♑"},
    {"name": "水瓶座", "date": "1/20〜2/18", "emoji": "♒"},
    {"name": "魚座",   "date": "2/19〜3/20", "emoji": "♓"}
]

FORTUNE_TEXTS = {
    "excellent": [ # 1位〜3位用 (絶好調)
        "これまでの努力が実を結び、素晴らしい成果を手にする一日です。自信を持って進んでください！",
        "直感が恐ろしいほど冴え渡っています。迷っていた決断を下すのに最高のタイミングです。",
        "新しいことに挑戦すると大きな運気を引き寄せます。宝くじの購入や投資にも強い追い風が！",
        "周囲からの評価が急上昇する暗示。あなたのアイデアが多くの人を救うきっかけになります。",
        "予想外の臨時収入や、探していたものが見つかる嬉しいハプニングの予感。金運絶好調です！",
        "エネルギーに満ち溢れ、どんな壁も乗り越えられる無敵の1日。大きな勝負に出るなら今日です。",
        "あなたの魅力が最大限に引き出される日。対人関係も良好で、強力な味方が現れるでしょう。",
        "停滞していた物事が一気に動き出します。長年の夢を叶えるための第一歩を踏み出しましょう。",
        "偶然立ち寄った場所に幸運の鍵が落ちています。直感で選んだ数字が大当たりを引くかも！？",
        "心身ともにバランスが整い、最高のパフォーマンスを発揮できます。勝利の女神はあなたに微笑んでいます。"
    ],
    "good": [ # 4位〜8位用 (安定・小吉)
        "穏やかで落ち着いた一日になるでしょう。自分のペースを守ることが今日の鍵です。",
        "周囲との何気ないコミュニケーションの中に、今後の人生を豊かにする思わぬヒントが隠されています。",
        "小さなラッキーが重なる予感。いつもより少しだけ直感を信じて行動してみましょう。",
        "コツコツと積み上げてきたことが評価され始めます。焦らずに今のやり方を貫いてください。",
        "今日は「整理整頓」が運気アップの秘訣。身の回りやお金の管理を見直すと金運が上向きます。",
        "過去の経験があなたを助けてくれます。似たような状況に直面したら、以前の成功パターンを思い出して。",
        "気になっていたことに少しだけ手を出してみるのに良い日。少額での運試しも吉と出そうです。",
        "誰かのサポート役に回ることで、巡り巡ってあなた自身に大きな幸運が舞い込んでくる暗示です。",
        "ルーティンワークの中に新しい発見があります。いつもの道を少し変えてみるのも運気アップに。",
        "迷ったときは「ワクワクする方」を選んで正解。直感があなたを正しい道へと導いてくれます。"
    ],
    "caution": [ # 9位〜12位用 (注意・アドバイス)
        "少し疲れが出やすいかもしれません。無理をせず、今日は自分のための休息を最優先してください。",
        "思い込みでの行動は避けて。何事も慎重な確認を心がけることで、未然にトラブルを防げます。",
        "焦りは禁物です。今日は大きく動くよりも、リラックスして次のチャンスに備える充電期間にしましょう。",
        "予期せぬ出費や見落としに注意が必要な日。大きなお金を使う決断は明日以降に持ち越すのが無難です。",
        "人間関係で少しすれ違いが起きやすい星回り。言葉選びを慎重にし、相手の意見に耳を傾けましょう。",
        "感情の波が激しくなりがち。深呼吸をして、客観的な視点を持つことで運気は回復に向かいます。",
        "「うまい話」には裏があるかもしれません。今日は堅実に、手堅い選択をすることが最大の防御になります。",
        "予定通りに進まなくてもイライラしないこと。回り道をした先に、思わぬ幸運の種が落ちていることも。",
        "判断力が少し鈍っているかも。宝くじを買うなら「AI予想」や「クイックピック」に身を委ねるのが吉です。",
        "過去の失敗を思い出してネガティブになりやすい日。おいしいものを食べて、早めに寝るのが一番の開運法です。"
    ]
}

# =========================================================
# タロットカード大アルカナ（全22枚）の本格データ定義
# =========================================================
TAROT_DECK = [
    {
        "id": 0, "name": "愚者 (The Fool)", "img": "https://upload.wikimedia.org/wikipedia/commons/9/90/RWS_Tarot_00_Fool.jpg",
        "upright": { "meaning": "自由・型破り・無邪気・純粋", "money": "直感的な閃きが大当たりを引き寄せます。少額でいつもと違う買い方（クイックピックなど）を試すのが大吉。", "advice": "常識や過去のデータに囚われず、あなたの心の赴くままに行動してください。" },
        "reversed": { "meaning": "軽率・無計画・わがまま・焦り", "money": "無計画な出費やギャンブルは禁物。直感ではなく、冷静なデータ分析（AI予想）に従うべき時です。", "advice": "「なんとかなる」という甘い考えを捨て、地に足をつける必要があります。" }
    },
    {
        "id": 1, "name": "魔術師 (The Magician)", "img": "https://upload.wikimedia.org/wikipedia/commons/d/de/RWS_Tarot_01_Magician.jpg",
        "upright": { "meaning": "創造・自信・スタート・才能", "money": "新しい手法を取り入れるのに最高のタイミング。自ら分析した数字や、AIのデータを活用すると結果が出やすいです。", "advice": "あなたには既に必要なツールがすべて揃っています。あとは実行するだけです。" },
        "reversed": { "meaning": "混迷・スランプ・消極的・裏切り", "money": "情報に振り回されてしまいそう。「絶対に当たる」といった怪しい情報には注意し、堅実な買い方を。", "advice": "自信を失いかけています。まずは小さな成功体験を積み重ねて感覚を取り戻しましょう。" }
    },
    {
        "id": 2, "name": "女教皇 (The High Priestess)", "img": "https://upload.wikimedia.org/wikipedia/commons/8/88/RWS_Tarot_02_High_Priestess.jpg",
        "upright": { "meaning": "直感・知性・冷静・洞察力", "money": "冷静な分析力が冴えています。過去のデータや傾向をじっくり読み解くことで、隠された法則が見えてくるかも。", "advice": "心の奥底からの声（潜在意識）に耳を傾けてください。静かな環境で考えるのが吉です。" },
        "reversed": { "meaning": "神経質・批判的・冷酷・閉鎖的", "money": "考えすぎてチャンスを逃す暗示。「絶対にこれだ」と固執しすぎると大局を見失います。", "advice": "知識や理屈だけで物事を判断していませんか？少し肩の力を抜いて柔軟になりましょう。" }
    },
    {
        "id": 3, "name": "女帝 (The Empress)", "img": "https://upload.wikimedia.org/wikipedia/commons/d/d2/RWS_Tarot_03_Empress.jpg",
        "upright": { "meaning": "豊穣・繁栄・愛情・包容力", "money": "金運は絶好調。豊かな実りを手にする暗示です。楽しむ気持ちで宝くじを買うと、幸運の女神が微笑みます。", "advice": "心にゆとりを持つことが成功の鍵。周囲への感謝を忘れずに過ごしてください。" },
        "reversed": { "meaning": "浪費・嫉妬・怠惰・虚栄心", "money": "見栄を張ってのお金の使い方や、過度な浪費に注意。予算をしっかり決めて楽しむことが重要です。", "advice": "「もっと欲しい」という強欲さが運気を下げています。今あるものに目を向けてください。" }
    },
    {
        "id": 4, "name": "皇帝 (The Emperor)", "img": "https://upload.wikimedia.org/wikipedia/commons/c/c3/RWS_Tarot_04_Emperor.jpg",
        "upright": { "meaning": "支配・安定・成就・責任感", "money": "計画的で確実なアプローチが功を奏します。予算を決めた継続的な購入（セット買い等）が結果を生むでしょう。", "advice": "感情に流されず、強い意志を持って自分のルールを貫き通してください。" },
        "reversed": { "meaning": "傲慢・頑固・身勝手・過労", "money": "「自分だけは当たる」という過信が命取りに。意地になってつぎ込むのは絶対にやめましょう。", "advice": "人の意見（AIの客観的なデータなど）を聞き入れる柔軟さが必要です。" }
    },
    {
        "id": 5, "name": "法王 (The Hierophant)", "img": "https://upload.wikimedia.org/wikipedia/commons/8/8d/RWS_Tarot_05_Hierophant.jpg",
        "upright": { "meaning": "慈悲・連帯・伝統・信頼", "money": "奇をてらわない、王道の買い方（ジャンボの連番など）や、専門家（AI）のアドバイスに従うのが吉。", "advice": "ルールや規律を守ることで守られます。信頼できる人の助言を大切にしてください。" },
        "reversed": { "meaning": "束縛・孤立・おせっかい・盲信", "money": "古いやり方に縛られて損をするかも。たまには普段買わない宝くじ（ビンゴ5など）に挑戦するのもアリです。", "advice": "常識の枠から少しはみ出してみることで、現状を打開できる暗示です。" }
    },
    {
        "id": 6, "name": "恋人 (The Lovers)", "img": "https://upload.wikimedia.org/wikipedia/commons/3/3a/RWS_Tarot_06_Lovers.jpg",
        "upright": { "meaning": "選択・調和・情熱・絆", "money": "直感による「究極の二択」が大正解を生む暗示。迷った数字があれば、最初にピンときた方を選んでください。", "advice": "頭で考えるよりも、心が「楽しい」「心地よい」と感じる選択をしましょう。" },
        "reversed": { "meaning": "誘惑・不道徳・空回り・失恋", "money": "優柔不断になってしまい、買いそびれたり選び間違えたりする暗示。今日は無理に勝負しない方が良いでしょう。", "advice": "その場しのぎの決断は後悔を生みます。一度冷静になって状況を見つめ直して。" }
    },
    {
        "id": 7, "name": "戦車 (The Chariot)", "img": "https://upload.wikimedia.org/wikipedia/commons/9/9b/RWS_Tarot_07_Chariot.jpg",
        "upright": { "meaning": "勝利・前進・行動力・克服", "money": "迷わず突き進むことで勝利（高額当選）を掴み取ります！思い立ったら吉日、すぐに行動に移してください。", "advice": "あなたの持つエネルギーを一つの目標に集中させることで、どんな壁も突破できます。" },
        "reversed": { "meaning": "暴走・挫折・好戦的・敗北", "money": "熱くなりすぎて予算をオーバーしてしまう危険があります。引き際を見極める冷静さが必要です。", "advice": "コントロールを失っています。一度立ち止まり、手綱を握り直す時間を作りましょう。" }
    },
    {
        "id": 8, "name": "力 (Strength)", "img": "https://upload.wikimedia.org/wikipedia/commons/f/f5/RWS_Tarot_08_Strength.jpg",
        "upright": { "meaning": "忍耐・不屈・理性・自制心", "money": "一発逆転を狙うより、コツコツと継続して買い続ける忍耐力が最終的な大きな利益に繋がります。", "advice": "恐れや不安といった「自分の内なる獣」を、優しさと理性で手懐けてください。" },
        "reversed": { "meaning": "甘え・無気力・自信喪失・妥協", "money": "「どうせ当たらない」というネガティブな思い込みが運気を下げています。今日は買うのをお休みしても良いかも。", "advice": "困難から逃げ出さず、自分の弱さと真正面から向き合う勇気が必要です。" }
    },
    {
        "id": 9, "name": "隠者 (The Hermit)", "img": "https://upload.wikimedia.org/wikipedia/commons/4/4d/RWS_Tarot_09_Hermit.jpg",
        "upright": { "meaning": "探求・内観・孤独・悟り", "money": "周囲のノイズを遮断し、自分一人で過去のデータを深く分析することで、誰も気づかない法則を発見できそうです。", "advice": "答えは外ではなく、あなた自身の心（潜在意識）の中にすでに存在しています。" },
        "reversed": { "meaning": "閉鎖的・陰湿・現実逃避・偏屈", "money": "自分の分析やオカルトに固執しすぎて失敗する暗示。AIの予想など、第三者の客観的なデータも取り入れて。", "advice": "殻に閉じこもらず、外の光（新しい情報や人の意見）を取り入れる時期です。" }
    },
    {
        "id": 10, "name": "運命の輪 (Wheel of Fortune)", "img": "https://upload.wikimedia.org/wikipedia/commons/3/3c/RWS_Tarot_10_Wheel_of_Fortune.jpg",
        "upright": { "meaning": "転機・好転・チャンス・運命的", "money": "まさに「運命の転換点」。突然の閃きや、たまたま買った1枚が人生を変える高額当選を呼び込む最強の運気です！", "advice": "流れが来ています。ためらわずに、その波に乗って思い切り行動してください。" },
        "reversed": { "meaning": "すれ違い・悪化・タイミングのズレ", "money": "運気が下降気味。買い忘れや、マークシートの塗り間違いなどケアレスミスに注意してください。", "advice": "今は無理に抗わず、次の良い波が来るのを静かに待つのが賢明です。" }
    },
    {
        "id": 11, "name": "正義 (Justice)", "img": "https://upload.wikimedia.org/wikipedia/commons/e/e0/RWS_Tarot_11_Justice.jpg",
        "upright": { "meaning": "公平・均衡・誠意・正当な評価", "money": "過去に積み上げた努力やデータ分析が「正当な結果」として現れます。理詰めの買い方（ロトなど）が吉。", "advice": "感情を排除し、事実とデータに基づいた公平な判断を下してください。" },
        "reversed": { "meaning": "不公平・偏見・不正・不釣り合い", "money": "「これだけ買ったのに当たらない」と不満が溜まりやすい日。予算のバランスが崩れている警告サインです。", "advice": "物事の一面だけを見ていませんか？視点を変えて全体を見渡す必要があります。" }
    },
    {
        "id": 12, "name": "吊るされた男 (The Hanged Man)", "img": "https://upload.wikimedia.org/wikipedia/commons/2/2b/RWS_Tarot_12_Hanged_Man.jpg",
        "upright": { "meaning": "修行・試練・自己犠牲・視点の転換", "money": "今は当たらない時期かもしれませんが、この試練が次の直感を磨きます。視点を変えた新しい買い方を試すと吉。", "advice": "一見身動きが取れないように見えても、視点を変えれば大きな気づきが得られます。" },
        "reversed": { "meaning": "無駄な犠牲・徒労・もがき・焦り", "money": "負けを取り戻そうとしてさらに泥沼にハマる暗示。今日は絶対に投資や宝くじに手を出さないでください。", "advice": "執着を捨てる時です。諦める勇気が、あなたを次なるステージへ解放します。" }
    },
    {
        "id": 13, "name": "死神 (Death)", "img": "https://upload.wikimedia.org/wikipedia/commons/d/d7/RWS_Tarot_13_Death.jpg",
        "upright": { "meaning": "終焉・リセット・再生・転生", "money": "これまでの予想方法やジンクスを「完全にリセット」する時。全く新しいアプローチを取り入れると金運が復活します。", "advice": "終わらせることを恐れないでください。古いものを手放さなければ、新しい運気は入りません。" },
        "reversed": { "meaning": "未練・停滞・ズルズル・変化への恐れ", "money": "当たらないと分かっている同じ買い方に執着してしまっています。思い切ってロジックを変える必要があります。", "advice": "過去の栄光や失敗にしがみついています。現状を打破するには変化を受け入れるしかありません。" }
    },
    {
        "id": 14, "name": "節制 (Temperance)", "img": "https://upload.wikimedia.org/wikipedia/commons/f/f5/RWS_Tarot_14_Temperance.jpg",
        "upright": { "meaning": "調和・自制・中庸・自然体", "money": "予算をしっかり守り、無理のない範囲で楽しむことで金運が安定します。AI予想と自分の直感の「ブレンド」が大吉。", "advice": "極端な行動は避け、心身のバランスを保つよう自然体で過ごしてください。" },
        "reversed": { "meaning": "不均衡・浪費・悪習慣・ルーズ", "money": "感情に任せた無駄遣いや、予算オーバーの購入に要注意。資金管理が甘くなっている警告です。", "advice": "生活リズムや感情のコントロールが乱れています。一度リセットして生活を整えましょう。" }
    },
    {
        "id": 15, "name": "悪魔 (The Devil)", "img": "https://upload.wikimedia.org/wikipedia/commons/5/55/RWS_Tarot_15_Devil.jpg",
        "upright": { "meaning": "欲望・誘惑・執着・堕落", "money": "ギャンブル依存や「絶対当たる」という甘い誘惑に要注意。冷静な判断ができず、大きく損をする可能性があります。", "advice": "欲望に溺れ、大切なものを見失っています。強い意志で誘惑を断ち切ってください。" },
        "reversed": { "meaning": "解放・回復・悪縁を断つ・覚醒", "money": "負の連鎖から抜け出せる兆し。ダメだった予想方法を見切り、健全な予算管理ができるようになります。", "advice": "あなたを縛り付けていた鎖はすでに解けています。あとは自らの足で歩き出すだけです。" }
    },
    {
        "id": 16, "name": "塔 (The Tower)", "img": "https://upload.wikimedia.org/wikipedia/commons/5/53/RWS_Tarot_16_Tower.jpg",
        "upright": { "meaning": "崩壊・破滅・予期せぬトラブル・衝撃", "money": "想定外の事態が起こる暗示。金運は大荒れなので、今日は手堅く資金を守り、一切の勝負事を避けるのが最善です。", "advice": "積み上げてきた価値観が崩れるような出来事があるかもしれませんが、それは必要な破壊（浄化）です。" },
        "reversed": { "meaning": "緊迫・じわじわとした崩壊・トラウマ", "money": "小さな損（ハズレ）が積み重なって大きなダメージになる警告。見直すべきは今です。", "advice": "問題から目を背けても解決しません。崩れゆく現実を受け止め、基礎から作り直す覚悟を持ちましょう。" }
    },
    {
        "id": 17, "name": "星 (The Star)", "img": "https://upload.wikimedia.org/wikipedia/commons/d/db/RWS_Tarot_17_Star.jpg",
        "upright": { "meaning": "希望・ひらめき・願いが叶う・吉兆", "money": "直感やインスピレーションが光り輝く日！ふと思いついた数字が、大いなる希望（高額当選）を運んでくるかもしれません。", "advice": "明るい未来を信じてください。あなたの純粋な願いは宇宙に届き、現実になろうとしています。" },
        "reversed": { "meaning": "悲観・高望み・失望・見失う", "money": "現実離れした過度な期待（いきなり数億円など）が失望を生みます。まずは小さな当たりを狙う堅実さを持って。", "advice": "理想が高すぎて現実とのギャップに苦しんでいます。手の届く目標に切り替えましょう。" }
    },
    {
        "id": 18, "name": "月 (The Moon)", "img": "https://upload.wikimedia.org/wikipedia/commons/7/7f/RWS_Tarot_18_Moon.jpg",
        "upright": { "meaning": "不安・迷い・幻滅・隠れた危険", "money": "先が見えない不安な時期。何を買っても当たらない気がしてしまう日は、AIのデータなど明確な「光」に頼りましょう。", "advice": "潜在意識にある見えない恐怖があなたを縛っています。夜明け前が一番暗いことを思い出して。" },
        "reversed": { "meaning": "不安からの解放・好転・トラウマの払拭", "money": "スランプを抜け出し、自分なりの必勝法や直感が戻ってくる兆し。迷いが晴れてクリアな判断ができます。", "advice": "霧が晴れ、進むべき道がはっきりと見えてきました。過去の不安はもう捨ててください。" }
    },
    {
        "id": 19, "name": "太陽 (The Sun)", "img": "https://upload.wikimedia.org/wikipedia/commons/1/17/RWS_Tarot_19_Sun.jpg",
        "upright": { "meaning": "成功・幸福・繁栄・生命力", "money": "文句なしの最強運気！明るく前向きな気持ちで宝くじを買うことで、とびきりの結果（高額当選）を引き寄せます！", "advice": "何も心配はいりません。今のあなたは太陽のように輝き、すべてをポジティブな方向へ導く力があります。" },
        "reversed": { "meaning": "不調・延期・エネルギー不足・見栄", "money": "運気は悪くないものの、あと一歩及ばず（ニアピンなど）悔しい思いをするかも。次回への布石と考えましょう。", "advice": "少しだけ元気が足りていません。日光を浴びたり、楽しいことをしてエネルギーをチャージして。" }
    },
    {
        "id": 20, "name": "審判 (Judgement)", "img": "https://upload.wikimedia.org/wikipedia/commons/d/dd/RWS_Tarot_20_Judgment.jpg",
        "upright": { "meaning": "復活・覚醒・奇跡・報われる", "money": "一度諦めていた過去の予想数字（マイラッキーナンバーなど）が、ここで奇跡の復活当選を果たす大チャンス！", "advice": "過去の努力が報われる時が来ました。あなたの潜在意識が「今だ」と告げるサインを見逃さないで。" },
        "reversed": { "meaning": "挫折・再起不能・未練・悔恨", "money": "「あの時買っておけば」という後悔を引きずりそう。終わったことは潔く諦め、次の抽選に目を向けましょう。", "advice": "過去の失敗をいつまでも責めるのはやめましょう。自分を許すことが次の一歩に繋がります。" }
    },
    {
        "id": 21, "name": "世界 (The World)", "img": "https://upload.wikimedia.org/wikipedia/commons/f/ff/RWS_Tarot_21_World.jpg",
        "upright": { "meaning": "完成・完全・最高・ハッピーエンド", "money": "全てが完璧に噛み合い、長年追い求めていた結果（理想の当選）を手にする最高のカード！迷わず勝負に出てください。", "advice": "あなたの目標は一つの「完成」を迎えようとしています。自信を持ってゴールテープを切ってください。" },
        "reversed": { "meaning": "未完成・スランプ・中途半端・マンネリ", "money": "あと少しのところで結果が届かないもどかしい時期。予想に新しいスパイス（AI予想を取り入れる等）が必要です。", "advice": "今の現状に満足して成長を止めていませんか？完成まであと少し、最後のひと踏ん張りを。" }
    }
]

LOTTERY_TYPES = ["ロト7", "ロト6", "ナンバーズ4", "ナンバーズ3", "ビンゴ5"]

# =========================================================
# 日替わりの占いデータを生成する関数
# =========================================================
def generate_daily_horoscope():
    today = datetime.date.today()
    date_str = f"{today.year}年{today.month}月{today.day}日"
    
    seed = today.toordinal()
    random.seed(seed)
    
    ranking = list(ZODIACS)
    random.shuffle(ranking)
    
    daily_data = []
    for i, zodiac in enumerate(ranking):
        rank = i + 1
        
        if rank <= 3:
            status_type = "excellent"
            money, work, love = random.choice([5, 4]), random.choice([5, 4]), random.choice([5, 4])
        elif rank <= 8:
            status_type = "good"
            money, work, love = random.choice([4, 3, 2]), random.choice([4, 3, 2]), random.choice([4, 3, 2])
        else:
            status_type = "caution"
            money, work, love = random.choice([3, 2, 1]), random.choice([3, 2, 1]), random.choice([3, 2, 1])
            
        text = random.choice(FORTUNE_TEXTS[status_type])
        lucky_num = random.randint(0, 9)
        
        # 総合評価（★の数）を計算
        total_score = money + work + love
        if total_score >= 13: total_star = "★★★★★"
        elif total_score >= 10: total_star = "★★★★☆"
        elif total_score >= 7: total_star = "★★★☆☆"
        else: total_star = "★★☆☆☆"

        daily_data.append({
            "rank": rank,
            "name": zodiac["name"],
            "date": zodiac["date"],
            "emoji": zodiac["emoji"],
            "text": text,
            "lucky_num": lucky_num,
            "stars": total_star,
            "money": "★" * money + "☆" * (5 - money),
            "work": "★" * work + "☆" * (5 - work),
            "love": "★" * love + "☆" * (5 - love)
        })
        
    return date_str, daily_data

# =========================================================
# HTML生成関数
# =========================================================
def build_html(date_str, daily_data):
    print("🔄 星座占い＆タロットページの生成を開始...")
    
    # タロットデータをJSに渡すためにJSON文字列に変換
    tarot_json = json.dumps(TAROT_DECK, ensure_ascii=False)
    
    # --- ランキング部分のHTMLを構築 ---
    ranking_html = ""
    for item in daily_data:
        if item['rank'] == 1:
            crown, border_color, bg_color = "🥇", "#fbbf24", "#fefce8"
        elif item['rank'] == 2:
            crown, border_color, bg_color = "🥈", "#94a3b8", "#f8fafc"
        elif item['rank'] == 3:
            crown, border_color, bg_color = "🥉", "#b45309", "#fffbeb"
        else:
            crown, border_color, bg_color = f"{item['rank']}位", "#e2e8f0", "#ffffff"

        ranking_html += f"""
        <div class="ranking-card" style="border-left: 6px solid {border_color}; background-color: {bg_color};">
            <div class="rank-header">
                <div class="rank-title">{crown} {item['emoji']} {item['name']}</div>
                <div class="lucky-number">ラッキー数字: <span>{item['lucky_num']}</span></div>
            </div>
            <p class="fortune-text">{item['text']}</p>
            <div class="fortune-stats">
                <div class="stat-item" style="width: 100%; border-bottom: 1px dashed #cbd5e1; padding-bottom: 5px; margin-bottom: 5px;">👑 総合評価: <span style="color: #fbbf24;">{item['stars']}</span></div>
                <div class="stat-item">💰 金運: <span style="color: #ea580c;">{item['money']}</span></div>
                <div class="stat-item">💼 仕事運: <span style="color: #2563eb;">{item['work']}</span></div>
                <div class="stat-item">💖 恋愛運: <span style="color: #e11d48;">{item['love']}</span></div>
            </div>
        </div>
        """

    # --- HTML全体 ---
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>【毎日更新】本格タロット＆12星座占い×宝くじ | ロト＆ナンバーズ攻略局</title>
    <meta name="description" content="本日の12星座占いランキングと、本格的な大アルカナタロット診断で今日のラッキーナンバー・おすすめ宝くじを完全無料で鑑定します。">
    <style>
        body {{ font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; margin: 0; padding: 0; background-color: #f0f4f8; color: #333; }}
        header {{ background-color: #1e3a8a; padding: 15px 0; text-align: center; }}
        nav {{ display: flex; justify-content: center; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: sticky; top: 0; flex-wrap: wrap; z-index: 10; }}
        nav a {{ 
    color: #1e3a8a; 
    padding: 12px 12px; /* 👈 上下の余白を12px、左右の余白を12pxに縮小 */
    font-size: 14px;    /* 👈 文字サイズを少し小さく指定（元は未指定＝16px相当） */
    text-decoration: none; 
    font-weight: bold; 
    border-bottom: 3px solid transparent; 
    transition: all 0.3s; 
}}
        nav a.active {{ border-bottom: 3px solid #8b5cf6; color: #8b5cf6; background-color: #f5f3ff; }}
        nav a:hover {{ background-color: #f0f4f8; }}

        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .section-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .section-header {{ color: #4c1d95; border-bottom: 2px solid #ede9fe; padding-bottom: 10px; margin-bottom: 20px; font-size: 22px; display: flex; align-items: center; }}

        /* ▼▼▼ 本格タロット占い演出用CSS ▼▼▼ */
        .tarot-area {{ text-align: center; background: linear-gradient(135deg, #0f172a, #312e81); color: white; padding: 40px 20px; border-radius: 12px; box-shadow: inset 0 0 30px rgba(0,0,0,0.8); position: relative; overflow: hidden; }}
        .tarot-area::before {{ content: '✨'; position: absolute; font-size: 150px; opacity: 0.05; top: -30px; left: -20px; }}
        .tarot-area::after {{ content: '🔮'; position: absolute; font-size: 150px; opacity: 0.05; bottom: -30px; right: -20px; }}
        
        .input-group {{ margin-bottom: 20px; position: relative; z-index: 2; }}
        input[type="date"] {{ padding: 12px 20px; font-size: 18px; border-radius: 30px; border: 2px solid #6366f1; outline: none; background: rgba(255,255,255,0.9); font-weight: bold; }}
        .btn-divination {{ background: linear-gradient(135deg, #fbbf24, #d97706); color: white; border: none; padding: 15px 40px; font-size: 18px; border-radius: 30px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 15px rgba(217, 119, 6, 0.5); transition: all 0.3s; margin-top: 20px; }}
        .btn-divination:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(217, 119, 6, 0.7); }}
        
        /* カードのアニメーション設定 */
        .card-scene {{ perspective: 1000px; width: 100%; max-width: 600px; margin: 20px auto; display: none; }}
        .card-inner {{ width: 100%; display: flex; flex-direction: column; align-items: center; transition: opacity 1s; }}
        .card-3d-wrapper {{ width: 200px; height: 340px; position: relative; transform-style: preserve-3d; transition: transform 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); margin-bottom: 20px; }}
        .card-3d-wrapper.is-flipped {{ transform: rotateY(180deg); }}
        .card-3d-wrapper.is-shaking {{ animation: shake 0.4s infinite; }}
        @keyframes shake {{ 0% {{transform: translate(1px, 1px) rotate(0deg);}} 50% {{transform: translate(-2px, 2px) rotate(-2deg);}} 100% {{transform: translate(1px, -1px) rotate(1deg);}} }}
        
        .card-face {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 2px solid #fbbf24; overflow: hidden; }}
        .card-front {{ background: repeating-linear-gradient(45deg, #1e1b4b, #1e1b4b 10px, #312e81 10px, #312e81 20px); display: flex; align-items: center; justify-content: center; }}
        .card-front::after {{ content: '👁️'; font-size: 60px; }}
        .card-back {{ background: #0f172a; transform: rotateY(180deg); display: flex; align-items: center; justify-content: center; }}
        .card-back img {{ width: 100%; height: 100%; object-fit: cover; opacity: 0.9; }}
        .card-back.reversed img {{ transform: rotate(180deg); }}

        /* タロットの診断結果表示エリア */
        .tarot-result-details {{ background: rgba(255, 255, 255, 0.95); color: #333; padding: 25px; border-radius: 12px; width: 100%; text-align: left; box-sizing: border-box; box-shadow: 0 10px 25px rgba(0,0,0,0.3); border-top: 4px solid #8b5cf6; opacity: 0; transform: translateY(20px); transition: all 1s ease 0.5s; }}
        .tarot-result-details.show {{ opacity: 1; transform: translateY(0); }}
        
        .result-head {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }}
        .card-name-display {{ font-size: 22px; font-weight: bold; color: #4c1d95; }}
        .card-position {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: bold; }}
        .pos-upright {{ background-color: #dcfce7; color: #16a34a; border: 1px solid #86efac; }}
        .pos-reversed {{ background-color: #fee2e2; color: #e11d48; border: 1px solid #fca5a5; }}
        
        .meaning-keyword {{ font-size: 15px; color: #64748b; font-weight: bold; margin-bottom: 15px; text-align: center; }}
        
        .advice-box {{ background: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #fbbf24; }}
        .advice-title {{ font-size: 14px; color: #b45309; font-weight: bold; margin-bottom: 5px; }}
        .advice-text {{ font-size: 15px; line-height: 1.6; color: #334155; margin: 0; }}

        .loto-recommend {{ display: flex; justify-content: center; gap: 20px; margin-top: 20px; padding-top: 20px; border-top: 1px dashed #cbd5e1; }}
        .loto-item {{ text-align: center; }}
        .loto-item span {{ display: block; font-size: 12px; color: #64748b; margin-bottom: 5px; }}
        .loto-item strong {{ font-size: 24px; color: #e11d48; }}
        .loto-item .badge {{ background: #4c1d95; color: white; padding: 5px 15px; border-radius: 8px; font-size: 16px; font-weight: bold; }}

        /* ▼▼▼ ランキング用CSS ▼▼▼ */
        .ranking-card {{ padding: 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); transition: transform 0.2s; }}
        .ranking-card:hover {{ transform: translateX(5px); }}
        .rank-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #cbd5e1; padding-bottom: 10px; margin-bottom: 10px; flex-wrap: wrap; gap: 10px; }}
        .rank-title {{ font-size: 20px; font-weight: bold; color: #1e293b; }}
        .lucky-number {{ background: #fee2e2; color: #be123c; padding: 5px 15px; border-radius: 20px; font-size: 14px; font-weight: bold; }}
        .lucky-number span {{ font-size: 20px; }}
        .fortune-text {{ font-size: 15px; color: #475569; line-height: 1.7; font-weight: bold; }}
        .fortune-stats {{ display: flex; gap: 15px; flex-wrap: wrap; margin-top: 15px; font-size: 14px; background: white; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0; }}
        .stat-item {{ font-weight: bold; }}

        footer {{ background-color: #1e293b; color: #94a3b8; text-align: center; padding: 40px 20px; margin-top: 60px; font-size: 13px; border-top: 4px solid #3b82f6; }}
    </style>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1431683156739681"
     crossorigin="anonymous"></script>
</head>
<body>
    <header>
        <a href="index.html" style="text-decoration: none;">
            <img src="Lotologo001.png" alt="ロト＆ナンバーズ攻略局🎯完全無料のAI予想" style="max-width: 100%; height: auto; max-height: 180px;">
            <div style="color: white; font-size: 32px; font-weight: bold; margin-top: 5px; letter-spacing: 1px;">今日の星座占い＆宝くじ</div>
        </a>
    </header>

    <nav>
        <a href="index.html">トップ</a>
        <a href="loto7.html">ロト7</a>
        <a href="loto6.html">ロト6</a>
        <a href="numbers.html">ナンバーズ</a>
        <a href="jumbo.html">ジャンボ</a>
        <a href="column.html">攻略ガイド🔰</a>
        <a href="horoscope.html" class="active">占い🔮</a>
    </nav>

    <div class="container">
        <div class="tarot-area">
            <h2 style="margin-top: 0; color: #fbbf24; font-size: 24px;">🌟 生年月日×本格タロット 宝くじ診断</h2>
            <p style="font-size: 14px; margin-bottom: 20px; color: #e2e8f0; line-height: 1.6;">
                大アルカナ22枚が導き出すあなたの運命。<br>生年月日を入力し、潜在意識からのメッセージと「おすすめの宝くじ」を受け取ってください。
            </p>
            
            <div id="input-section" class="input-group">
                <input type="date" id="birthdate" required>
                <br>
                <button class="btn-divination" onclick="startDivination()">運命のカードを引く</button>
            </div>

            <div class="card-scene" id="tarot-scene">
                <div class="card-inner">
                    <div class="card-3d-wrapper" id="tarot-card">
                        <div class="card-face card-front"></div>
                        <div class="card-face card-back" id="tarot-back">
                            <img src="" id="tarot-img" alt="Tarot Card">
                        </div>
                    </div>
                    
                    <div class="tarot-result-details" id="tarot-details">
                        <div class="result-head">
                            <div class="card-name-display" id="res-card-name">愚者</div>
                            <div class="card-position" id="res-position">正位置</div>
                        </div>
                        <div class="meaning-keyword" id="res-meaning">自由・型破り・無邪気・純粋</div>
                        
                        <div class="advice-box">
                            <div class="advice-title">💰 金運・宝くじへの暗示</div>
                            <p class="advice-text" id="res-money">ここに宝くじ運が表示されます。</p>
                        </div>
                        
                        <div class="advice-box" style="border-left-color: #8b5cf6;">
                            <div class="advice-title">🌌 潜在意識からのアドバイス</div>
                            <p class="advice-text" id="res-advice">ここに深層心理からのアドバイスが表示されます。</p>
                        </div>
                        
                        <div class="loto-recommend">
                            <div class="loto-item">
                                <span>ラッキーナンバー</span>
                                <strong id="res-num">7</strong>
                            </div>
                            <div class="loto-item">
                                <span>今日のおすすめ</span>
                                <div class="badge" id="res-loto">ロト6</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <p id="loading-text" style="display: none; color: #fbbf24; font-weight: bold; margin-top: 15px; font-size: 18px; letter-spacing: 2px;">宇宙の意志をカードに降ろしています...</p>
        </div>
        
        <div style="text-align: center; margin: 25px 0;">
            <span style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 5px;">スポンサーリンク</span>
            <script src="https://adm.shinobi.jp/s/4275e4a786993be6d30206e03ec2de0f"></script>
        </div>

        <div class="section-card">
            <h2 class="section-header"><span>👑</span> 本日（{date_str}）の12星座 運勢ランキング</h2>
            {ranking_html}
        </div>
    </div>

    <footer>
        <p>&copy; 2026 ロト＆ナンバーズ攻略局🎯完全無料のAI予想 All Rights Reserved.</p>
    </footer>

    <script>
        // Pythonから渡された本格タロットデータ（全22枚×2位置）
        const tarotDeck = {tarot_json};
        const lotteries = ["ロト7", "ロト6", "ナンバーズ4", "ナンバーズ3", "ビンゴ5"];
        
        function startDivination() {{
            const dateInput = document.getElementById('birthdate').value;
            if(!dateInput) {{
                alert('生年月日を入力してください。星の導きを得るために必要です。');
                return;
            }}

            // 1. 日付と生年月日からハッシュを作成（その日は同じ結果になる）
            const today = new Date();
            const seedStr = dateInput + today.getFullYear() + today.getMonth() + today.getDate();
            let hash = 0;
            for (let i = 0; i < seedStr.length; i++) {{
                hash = seedStr.charCodeAt(i) + ((hash << 5) - hash);
            }}
            
            // 2. ハッシュ値からカード、位置、ラッキー番号を決定
            const absHash = Math.abs(hash);
            const cardIndex = absHash % 22;           // 0〜21 (大アルカナ)
            const isReversed = (absHash % 2 === 1);   // 0=正位置, 1=逆位置
            const luckyNum = absHash % 10;            // 0〜9
            const loto = lotteries[absHash % lotteries.length]; // おすすめ宝くじ
            
            const cardData = tarotDeck[cardIndex];
            const reading = isReversed ? cardData.reversed : cardData.upright;
            
            // 3. 画面の要素にデータをセット
            document.getElementById('tarot-img').src = cardData.img;
            document.getElementById('res-card-name').innerText = cardData.name;
            
            const posBadge = document.getElementById('res-position');
            const cardBack = document.getElementById('tarot-back');
            if(isReversed) {{
                posBadge.innerText = "逆位置";
                posBadge.className = "card-position pos-reversed";
                cardBack.classList.add('reversed'); // 画像を逆さまにするCSSクラス
            }} else {{
                posBadge.innerText = "正位置";
                posBadge.className = "card-position pos-upright";
                cardBack.classList.remove('reversed');
            }}
            
            document.getElementById('res-meaning').innerText = `キーワード：${{reading.meaning}}`;
            document.getElementById('res-money').innerText = reading.money;
            document.getElementById('res-advice').innerText = reading.advice;
            document.getElementById('res-num').innerText = luckyNum;
            document.getElementById('res-loto').innerText = loto;

            // 4. アニメーション演出（滞在時間稼ぎのキラーロジック）
            document.getElementById('input-section').style.display = 'none';
            document.getElementById('tarot-scene').style.display = 'block';
            
            const card3D = document.getElementById('tarot-card');
            const loadText = document.getElementById('loading-text');
            const detailsArea = document.getElementById('tarot-details');
            
            // 初期化
            card3D.classList.remove('is-flipped');
            detailsArea.classList.remove('show');
            
            // ガタガタ揺らす（念を込める演出）
            card3D.classList.add('is-shaking');
            loadText.style.display = 'block';

            // 3.5秒間ユーザーを惹きつけ、その後にカードをめくる
            setTimeout(() => {{
                card3D.classList.remove('is-shaking');
                loadText.style.display = 'none';
                card3D.classList.add('is-flipped'); // カード裏返り
                
                // カードがめくれた少し後（0.8秒後）に診断結果をフワッと表示
                setTimeout(() => {{
                    detailsArea.classList.add('show');
                }}, 800);
                
            }}, 3500);
        }}
    </script>
</body>
</html>"""

    with open('horoscope.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ 星座占い＆本格タロットページ (horoscope.html) の生成が完了しました！")

# =========================================================
# インスタストーリーズ用の縦長画像を生成する関数（維持）
# =========================================================
def create_story_image(date_str, daily_data):
    print("🎨 Instagramストーリーズ用のランキング画像を生成中...")
    width, height = 1080, 1920
    
    img = Image.new('RGB', (width, height), (30, 58, 138))
    draw = ImageDraw.Draw(img)
    
    font_path = "NotoSansJP-Bold.ttf"
    if not os.path.exists(font_path):
        font_url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/static/NotoSansJP-Bold.ttf"
        urllib.request.urlretrieve(font_url, font_path)

    font_title = ImageFont.truetype(font_path, 80)
    font_date = ImageFont.truetype(font_path, 60)
    font_rank = ImageFont.truetype(font_path, 100)
    font_desc = ImageFont.truetype(font_path, 50)
    
    draw.text((80, 150), f"本日の星座占いランキング", font=font_title, fill=(255, 255, 255))
    draw.text((80, 250), f"{date_str}", font=font_date, fill=(253, 224, 71)) 
    
    y_offset = 450
    colors = [(251, 191, 36), (148, 163, 184), (180, 83, 9)] 
    
    for i in range(3):
        zodiac = daily_data[i]
        rank_str = f"第{i+1}位"
        
        draw.rounded_rectangle([60, y_offset, 1020, y_offset + 300], radius=20, fill=(255, 255, 255))
        
        draw.text((100, y_offset + 50), f"{rank_str}", font=font_rank, fill=colors[i])
        draw.text((400, y_offset + 50), f"{zodiac['name']}", font=font_rank, fill=(30, 58, 138))
        
        desc = f"ラッキー数字: {zodiac['lucky_num']}  /  金運: {zodiac['money'][:3]}"
        draw.text((100, y_offset + 200), desc, font=font_desc, fill=(71, 85, 105))
        
        y_offset += 350

    promo_text = "4位以降のランキングと\n本格タロット宝くじ診断は\nプロフィールのリンクから！"
    draw.multiline_text((width/2, 1500), promo_text, font=font_title, fill=(253, 224, 71), align="center", anchor="ma")
    
    output_path = "story_horoscope.jpg"
    img.save(output_path, "JPEG", quality=95)
    print(f"✅ ストーリーズ画像 ({output_path}) の生成が完了しました！")
    return output_path

# =========================================================
# 画像アップロードとInstagram Storiesへの自動投稿（維持）
# =========================================================
def upload_image_to_server(image_path):
    url = "https://freeimage.host/api/1/upload"
    print("☁️ 画像をサーバーにアップロード中...")
    try:
        with open(image_path, "rb") as file:
            b64_image = base64.b64encode(file.read()).decode('utf-8')
            
        payload = {
            "key": "6d207e02198a847aa98d0a2a901485a5",
            "action": "upload",
            "source": b64_image,
            "format": "json"
        }
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            image_url = res.json()["image"]["url"]
            print(f"✅ 画像URL化成功: {image_url}")
            return image_url
    except Exception as e:
        print(f"❌ アップロードエラー: {e}")
    return None

def post_story_to_instagram(image_url):
    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    
    if not ig_account_id or not access_token:
        print("⚠️ InstagramのAPIキーが設定されていないため、ストーリーズ投稿をスキップしました。")
        return

    container_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
    payload = {
        'image_url': image_url,
        'media_type': 'STORIES', 
        'access_token': access_token
    }
    
    print("☁️ Instagram ストーリーズへのコンテナ作成をリクエスト中...")
    res = requests.post(container_url, data=payload)
    data = res.json()
    
    if 'id' not in data:
        print(f"❌ コンテナ作成エラー: {data}")
        print("⚠️ 通常のフィード投稿（画像）としてリトライします...")
        payload.pop('media_type')
        payload['caption'] = "本日の星座占いランキングトップ3！続きはプロフィールのリンクから！🔮✨"
        res = requests.post(container_url, data=payload)
        data = res.json()
        if 'id' not in data: return

    creation_id = data['id']
    time.sleep(10)
    
    publish_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
    pub_payload = {
        'creation_id': creation_id,
        'access_token': access_token
    }
    print("☁️ ストーリーズを公開中...")
    pub_res = requests.post(publish_url, data=pub_payload)
    pub_data = pub_res.json()
    
    if 'id' in pub_data:
        print("🎉🎉🎉 Instagram ストーリーズへの自動投稿が完了しました！ 🎉🎉🎉")
    else:
        print(f"❌ ストーリーズ公開エラー: {pub_data}")

# =========================================================
# メイン処理
# =========================================================
if __name__ == "__main__":
    date_str, daily_data = generate_daily_horoscope()
    build_html(date_str, daily_data)
    image_path = create_story_image(date_str, daily_data)
    image_url = upload_image_to_server(image_path)
    if image_url:
        post_story_to_instagram(image_url)