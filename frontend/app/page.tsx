

export default function Home() {
  return (
      <div className="bg-white w-full min-h-screen">
        <header className="bg-zinc-50 text-zinc-900 px-6 py-8">
          <h2 className="text-4xl font-bold">
            面接評価ブレ対策ツール
          </h2>
          <p className="text-sm mt-2 text-gray-600">
            新卒採用一次面接の評価記録・比較・出力（ブラウザ内のみで動作、データはページを閉じると消えます）
          </p>
        </header>

          <nav className="flex justify-center gap-12 mt-8">
            <button className="text-gray-500 hover:text-gray-700">
              評価入力
            </button>
            <button className="text-gray-500 hover:text-gray-700">
              一覧・検索・比較
            </button>
            <button className="text-gray-500 hover:text-gray-700">
              Excel出力
            </button>
          </nav>
          <main>
           <p className="text-center text-gray-600 mt-12">
             ここにメインコンテンツが表示されます
           </p>
          </main>
      </div>
  );
}
