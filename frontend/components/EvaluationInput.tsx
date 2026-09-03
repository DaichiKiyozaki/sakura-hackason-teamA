export default function EvaluationInput() {
　const standardScores = ["論理性", "コミュニケーション能力", "協調性", "熱意"];
  return (
    <section className="w-2/3 mx-auto mt-8 space-y-6">
      <div className="mb-4 rounded-[10px] border boder-[#d9e0e3] bg-white px-22 py-5">
        <h2 className="mb-4 text-[32px] font-semibold text-gray-800 justify-center flex">
            面接記録
        </h2>
      </div>
      <div>
        <label className="flex flex-col gap-2">
            面接日
        </label>
        <input
          type="date"
          className="w-full rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div>
        <label className="flex flex-col gap-2">
            学生名
        </label>
        <input
          type="text"
          className="w-full rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div>
        <label className="flex flex-col gap-2">
            面接官
        </label>
        <input
          type="text"
          className="w-full rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div>
        <label className="flex flex-col gap-2">
            面接メモ
        </label>
        <textarea
          className="w-full rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={4}
        />
      </div>
      <div>
        <button className="mt-4 rounded-[10px] bg-blue-500 px-4 py-2 text-white hover:bg-blue-600">
            要約
        </button>
      </div>
      <div>
        <h2>
            評価スコア
        </h2>
        <div className="mt-4 grid grid-cols-2 gap-4">
          {standardScores.map((score) => (
            <div key={score} className="flex flex-col gap-2">
              <label className="text-gray-700">{score}</label>
              <input
                type="number"
                min="1"
                max="5"
                className="w-full rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ))}
        </div>
        <div>
            <label className="flex flex-col gap-2">
                評価プロセス
            </label>
            <textarea
              className="w-full rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
            />
        </div>
        <div className="mt-4">
          <button className="rounded-[10px] bg-green-500 px-4 py-2 text-white hover:bg-green-600 mb-4">
              評価を保存
          </button>
        </div>
      </div>
    </section>
  );
}