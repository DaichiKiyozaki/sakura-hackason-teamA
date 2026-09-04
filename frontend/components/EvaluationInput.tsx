"use client";

import { useState } from "react";

type QuestionAnswer = {
    questionNo: number;
    question: string;
    answer: string;
    answerSummary: string;
};

export default function EvaluationInput() {
    const standardScores = [
        { id : "communication", label: "コミュニケーション能力" },
        { id : "problem_Solving", label: "問題解決力" },
        { id : "logical_thinking", label: "論理的思考力" },
        { id : "initiative", label: "主体性" },
        { id : "collaboration", label: "協調性" },
    ];
    const [isTranscriptModalopen, setIsTranscriptModalopen] = useState(false);
    const [transcript, setTranscript] = useState("");
    const [questionAnswers, setQuestionAnswers] = useState<QuestionAnswer[]>([]);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [interviewDate, setInterviewDate] = useState("");
    const [candidateName, setCandidateName] = useState(""); 
    const [overallcomment, setOverallComment] = useState("");
    const handleAnalyze = async () => {
        if (!transcript.trim()) {
            alert("文字起こしを入力してください");
            return;
        }

    setIsAnalyzing(true);
    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ transcript }),
        });
        
        if (!response.ok) {
            if (response.status === 400) {
                alert("入力内容を確認してください。");
            }
            throw new Error("分析に失敗しました。");
        }

        const result = await response.json();
        setQuestionAnswers(result.questionAnswers);
    } catch (error) {
        console.error("Error:", error);
        alert("エラーが発生しました。");
    } finally {
        setIsAnalyzing(false);
    }
};

    return (
        <main className="w-2/3 mx-auto mt-8 space-y-6">
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
                    value={interviewDate}
                    onChange={(e) => setInterviewDate(e.target.value)}
                />
            </div>
            <div>
                <label className="flex flex-col gap-2">
                    学生名
                </label>
                <input
                    type="text"
                    className="w-full rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={candidateName}
                    onChange={(e) => setCandidateName(e.target.value)}
                />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 items-start">
                <div>
                    <div>
                        <h2 className="mt-4 text-lg font-semibold text-gray-800">
                            面接メモ
                        </h2>
                        <textarea
                            className="w-full rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            rows={4}
                        />
                    </div>
                    <h2 className="mt-4 text-lg font-semibold text-gray-800">
                        評価スコア
                    </h2>
                    <div className="mt-4 grid grid-cols-2 gap-4">
                        {standardScores.map((score) => (
                            <div key={score.id} className="flex flex-col gap-2">
                                <label className="text-gray-700">{score.label}</label>
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
                <div className="overscroll-y-auto max-h-[600px] overflow-y-auto">
                    <div>
                        <h2 className="mt-4 text-lg font-semibold text-gray-800">
                            文字起こし・要約
                        </h2>
                    </div>
                    <div className="rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800">
                        <div>
                            <button
                                className="rounded-[10px] bg-blue-500 px-4 py-2 text-white hover:bg-blue-600 mt-4"
                                onClick={() => setIsTranscriptModalopen(true)}
                            >
                                文字起こし・要約を入力
                            </button>
                        </div>
                        <div className="mt-4">
                            <h3 className="text-lg font-semibold text-gray-800">
                                文字起こし・要約内容
                            </h3>
                            <div>
                                {questionAnswers.length === 0 ? (
                                    <p className="text-gray-500">まだ要約がありません。</p>
                                ) : (
                                    questionAnswers.map((item) => (
                                        <div key={item.questionNo} className="mt-2">
                                            <p className="font-semibold text-gray-800 mt-3">
                                                質問{item.questionNo}
                                            </p>
                                            <div>
                                                <h2 className="font-semibold text-gray-600">
                                                    【質問】
                                                </h2>
                                                <p className="text-gray-800">
                                                    {item.question}
                                                </p>
                                            </div>
                                            <div>
                                                <h2 className="font-semibold text-gray-600 mt-2">
                                                    【回答】
                                                </h2>
                                                <p className="text-gray-800">
                                                    {item.answer}
                                                </p>
                                                <div>
                                                    <h2 className="font-semibold text-gray-600 mt-2">
                                                        【要約】
                                                    </h2>
                                                    <p className="text-gray-800">
                                                        {item.answerSummary}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {isTranscriptModalopen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="w-2/3 rounded-[10px] bg-white p-6">
                        <h2 className="text-lg font-semibold text-gray-800">
                            文字起こし・要約
                        </h2>
                        <label>
                            文字起こしを入力してください
                        </label>
                        <textarea
                            className="w-full rounded-[10px] border border-[#d9e0e3] bg-white px-4 py-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={transcript}
                            onChange={(e) => setTranscript(e.target.value)}
                            rows={8}
                        />
                        <div className="flex justify-end">
                        <button
                            type="button"
                            className="rounded-[10px] bg-green-500 px-4 py-2 text-white hover:bg-green-600 mr-3"
                            onClick={handleAnalyze}
                            disabled={isAnalyzing}
                        >
                            {isAnalyzing ? "要約中..." : "要約"}
                        </button>
                        <button
                            className="rounded-[10px] bg-red-500 px-4 py-2 text-white hover:bg-red-600"
                            onClick={() => setIsTranscriptModalopen(false)}
                        >
                            閉じる
                        </button>
                        </div>
                    </div>
                </div>
            )}
        </main>
    );
}