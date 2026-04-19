// app/loto6/result/page.tsx
import Link from 'next/link';

export default function Loto6ResultDetail() {
  // ※実際にはここでJSONBinからデータをfetchします。以下はモックデータです。
  const resultData = {
    round: "第2094回",
    date: "2026年4月16日(木)",
    numbers: ["01", "12", "23", "34", "45", "46"],
    bonus: "09",
    prizes: [
      { grade: "1等", winners: "1口", prize: "200,000,000円" },
      { grade: "2等", winners: "14口", prize: "15,234,500円" },
      { grade: "3等", winners: "245口", prize: "340,000円" },
      { grade: "4等", winners: "10,230口", prize: "6,800円" },
      { grade: "5等", winners: "154,320口", prize: "1,000円" },
    ],
    carryover: "123,456,789円",
    has_carryover: true
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 pb-20">
      <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg overflow-hidden">
        
        {/* ヘッダー部分 */}
        <div className="bg-blue-600 text-white text-center py-4">
          <h1 className="text-xl font-bold">ロト6 抽選結果詳細</h1>
          <p className="text-sm opacity-90">{resultData.round} / {resultData.date}</p>
        </div>

        <div className="p-5">
          {/* 本数字・ボーナス数字 */}
          <div className="mb-6">
            <h2 className="text-sm font-bold text-gray-500 mb-2">本数字 / ボーナス</h2>
            <div className="flex flex-wrap gap-2">
              {resultData.numbers.map((num, i) => (
                <span key={i} className="w-10 h-10 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold text-lg shadow">
                  {num}
                </span>
              ))}
              <span className="w-10 h-10 rounded-full bg-red-500 text-white flex items-center justify-center font-bold text-lg shadow ml-2">
                {resultData.bonus}
              </span>
            </div>
          </div>

          {/* キャリーオーバー情報 */}
          {resultData.has_carryover && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 font-bold text-center">
              💰 キャリーオーバー発生中！<br/>
              <span className="text-xl">{resultData.carryover}</span>
            </div>
          )}

          {/* 各等級の詳細テーブル */}
          <h2 className="text-sm font-bold text-gray-500 mb-2">当せん金額・口数</h2>
          <div className="overflow-hidden border border-gray-200 rounded-lg">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-600 font-bold">等級</th>
                  <th className="px-4 py-2 text-right text-gray-600 font-bold">当せん金額</th>
                  <th className="px-4 py-2 text-right text-gray-600 font-bold">口数</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {resultData.prizes.map((prize, idx) => (
                  <tr key={idx} className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                    <td className="px-4 py-3 font-bold text-gray-800">{prize.grade}</td>
                    <td className="px-4 py-3 text-right text-blue-600 font-bold">{prize.prize}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{prize.winners}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 戻るボタン */}
          <div className="mt-8 text-center">
            <Link href="/loto6" className="inline-block bg-gray-200 hover:bg-gray-300 text-gray-700 font-bold py-3 px-8 rounded-full transition-colors">
              ロト6 トップに戻る
            </Link>
          </div>

        </div>
      </div>
    </div>
  );
}