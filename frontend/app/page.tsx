import EvaluationInput from "@/components/EvaluationInput";
import Image from "next/image";

export default function Home() {
  return (
      <div className="bg-white w-full min-h-screen">
        <header className="bg-zinc-50 text-zinc-900 px-6 py-8">
        <div className="flex items-center gap-4">
        <Image
          src={"/myicon.png"}
          className="rounded-full object-cover"
          alt="My Icon"
          width={100}
          height={100}
        />
          <h2 className="text-4xl font-bold">
            面接評価ブレ対策ツール
          </h2>
          </div>
          <p className="text-sm mt-2 text-gray-600">
            新卒採用一次面接の評価記録・比較・出力（ブラウザ内のみで動作、データはページを閉じると消えます）
          </p>
        </header>

          <main>
            <EvaluationInput/>
          </main>
      </div>
    );
  }
