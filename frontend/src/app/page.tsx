"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type StoryStyle = "治愈" | "冒险" | "暗黑";

interface VisionAnalysis {
  item_name: string;
  visual_features: string[];
  personality_traits: string[];
  story_character_hint: string;
}

interface GeneratedStory {
  title: string;
  full_text: string;
  page_texts: string[];
}

interface StoryOutline {
  theme: string;
  pages: { page: number; scene: string; plot: string; emotion: string }[];
}

interface GenerateResult {
  task_id: string;
  status: string;
  vision_analysis: VisionAnalysis | null;
  story: GeneratedStory | null;
  story_outline: StoryOutline | null;
  image_urls: string[];
  step_timings: Record<string, number>;
  error_message?: string;
}

const STYLES: { value: StoryStyle; label: string; emoji: string; desc: string; color: string }[] = [
  { value: "治愈", label: "治愈", emoji: "🌿", desc: "温暖治愈的故事", color: "from-emerald-400 to-teal-400" },
  { value: "冒险", label: "冒险", emoji: "⚔️", desc: "充满冒险的旅程", color: "from-orange-400 to-red-400" },
  { value: "暗黑", label: "暗黑", emoji: "🌑", desc: "深邃暗黑的寓言", color: "from-purple-500 to-indigo-600" },
];

const PIPELINE_STEPS = [
  { key: "vision", label: "分析物品", icon: "👁️", duration: 3 },
  { key: "rag", label: "检索模板", icon: "📚", duration: 1 },
  { key: "outline", label: "构思大纲", icon: "📝", duration: 18 },
  { key: "narrative", label: "撰写故事", icon: "✍️", duration: 22 },
  { key: "image", label: "绘制插图", icon: "🎨", duration: 18 },
  { key: "check", label: "质量检查", icon: "✅", duration: 1 },
];

// ============================================================
// 绘本阅读模式组件
// ============================================================
function BookReader({
  result,
  onClose,
}: {
  result: GenerateResult;
  onClose: () => void;
}) {
  const [currentPage, setCurrentPage] = useState(0);
  const totalPages = result.story?.page_texts.length || 0;

  const goNext = useCallback(() => {
    if (currentPage < totalPages - 1) setCurrentPage((p) => p + 1);
  }, [currentPage, totalPages]);

  const goPrev = useCallback(() => {
    if (currentPage > 0) setCurrentPage((p) => p - 1);
  }, [currentPage]);

  // 键盘导航
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " ") goNext();
      if (e.key === "ArrowLeft") goPrev();
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [goNext, goPrev, onClose]);

  const imgUrl = result.image_urls[currentPage];
  const fullImgUrl = imgUrl
    ? imgUrl.startsWith("http") ? imgUrl : `${API_BASE}${imgUrl}`
    : "";

  return (
    <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center">
      {/* 关闭按钮 */}
      <button
        onClick={onClose}
        className="absolute top-6 right-6 text-white/60 hover:text-white text-3xl z-10 transition-colors"
      >
        ✕
      </button>

      <div className="w-full max-w-5xl mx-auto px-8 flex flex-col items-center">
        {/* 标题 */}
        <h2 className="text-white text-2xl font-bold mb-6">
          {result.story?.title}
        </h2>

        {/* 主体：图片 + 文字 */}
        <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          {/* 插图 */}
          <div className="aspect-square rounded-2xl overflow-hidden bg-gray-900 shadow-2xl">
            {fullImgUrl ? (
              <img
                src={fullImgUrl}
                alt={`第${currentPage + 1}页`}
                className="w-full h-full object-cover transition-all duration-500"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-600">
                暂无插图
              </div>
            )}
          </div>

          {/* 文字 */}
          <div className="text-white/90 space-y-4">
            <div className="flex items-center gap-3 mb-4">
              <span className="bg-white/10 px-3 py-1 rounded-full text-sm">
                第 {currentPage + 1} / {totalPages} 页
              </span>
              {result.story_outline?.pages[currentPage] && (
                <span className="text-white/50 text-sm">
                  {result.story_outline.pages[currentPage].scene} · {result.story_outline.pages[currentPage].emotion}
                </span>
              )}
            </div>
            <p className="text-lg leading-9 font-light">
              {result.story?.page_texts[currentPage]}
            </p>
          </div>
        </div>

        {/* 翻页控制 */}
        <div className="flex items-center gap-6 mt-8">
          <button
            onClick={goPrev}
            disabled={currentPage === 0}
            className={`px-6 py-2 rounded-full text-sm transition-all ${
              currentPage === 0
                ? "bg-white/5 text-white/20 cursor-not-allowed"
                : "bg-white/10 text-white hover:bg-white/20"
            }`}
          >
            ← 上一页
          </button>

          {/* 页码指示器 */}
          <div className="flex gap-2">
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentPage(i)}
                className={`w-3 h-3 rounded-full transition-all ${
                  i === currentPage ? "bg-amber-400 scale-125" : "bg-white/20 hover:bg-white/40"
                }`}
              />
            ))}
          </div>

          <button
            onClick={goNext}
            disabled={currentPage === totalPages - 1}
            className={`px-6 py-2 rounded-full text-sm transition-all ${
              currentPage === totalPages - 1
                ? "bg-white/5 text-white/20 cursor-not-allowed"
                : "bg-white/10 text-white hover:bg-white/20"
            }`}
          >
            下一页 →
          </button>
        </div>

        <p className="text-white/30 text-xs mt-4">
          使用方向键或空格翻页 · ESC 退出
        </p>
      </div>
    </div>
  );
}

// ============================================================
// 主页面
// ============================================================
export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [style, setStyle] = useState<StoryStyle>("治愈");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [error, setError] = useState("");
  const [currentStep, setCurrentStep] = useState(-1);
  const [elapsed, setElapsed] = useState(0);
  const [showBook, setShowBook] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 进度模拟
  useEffect(() => {
    if (loading) {
      const startTime = Date.now();
      setCurrentStep(0);
      setElapsed(0);

      timerRef.current = setInterval(() => {
        const sec = Math.floor((Date.now() - startTime) / 1000);
        setElapsed(sec);

        let cumulative = 0;
        for (let i = 0; i < PIPELINE_STEPS.length; i++) {
          cumulative += PIPELINE_STEPS[i].duration;
          if (sec < cumulative) {
            setCurrentStep(i);
            break;
          }
          if (i === PIPELINE_STEPS.length - 1) setCurrentStep(i);
        }
      }, 500);

      return () => {
        if (timerRef.current) clearInterval(timerRef.current);
      };
    } else {
      setCurrentStep(-1);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, [loading]);

  const handleFile = (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError("");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  // 拖拽上传
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) handleFile(file);
  };

  const handleGenerate = async () => {
    if (!selectedFile) {
      setError("请先上传一张物品照片");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("style", style);

      const res = await axios.post<GenerateResult>(
        `${API_BASE}/api/generate`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 180000,
        }
      );
      setResult(res.data);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        if (err.code === "ECONNABORTED") {
          setError("生成超时，请重试（完整流程约需 60 秒）");
        } else {
          setError(err.response?.data?.detail || err.message);
        }
      } else {
        setError("生成失败，请重试");
      }
    } finally {
      setLoading(false);
    }
  };

  const getImgUrl = (url: string) =>
    url.startsWith("http") ? url : `${API_BASE}${url}`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50">
      {/* 绘本阅读模式 */}
      {showBook && result && (
        <BookReader result={result} onClose={() => setShowBook(false)} />
      )}

      {/* Header */}
      <header className="border-b border-amber-200 bg-white/60 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-3xl">📖</div>
            <div>
              <h1 className="text-2xl font-bold text-amber-900">FableLens</h1>
              <p className="text-sm text-amber-600">寓言透镜 — 让物品讲述自己的故事</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {result?.story && (
              <button
                onClick={() => setShowBook(true)}
                className="px-4 py-2 bg-amber-500 text-white rounded-xl text-sm font-medium hover:bg-amber-600 transition-colors shadow-sm"
              >
                📖 绘本模式
              </button>
            )}
            <span className="text-xs text-amber-400 hidden md:block">
              LangGraph + qwen-vl-max + FLUX.1
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* 进度条 */}
        {loading && (
          <div className="mb-8 bg-white rounded-2xl shadow-sm border border-amber-100 p-6 animate-in fade-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-amber-900">
                LangGraph Pipeline 运行中...
              </h3>
              <span className="text-sm text-amber-500 tabular-nums">{elapsed}s</span>
            </div>
            <div className="flex items-center gap-1 sm:gap-2">
              {PIPELINE_STEPS.map((step, i) => (
                <div key={step.key} className="flex-1">
                  <div
                    className={`h-2 rounded-full transition-all duration-700 ${
                      i < currentStep
                        ? "bg-amber-500"
                        : i === currentStep
                        ? "bg-amber-400 animate-pulse"
                        : "bg-gray-200"
                    }`}
                  />
                  <div className="flex items-center gap-1 mt-2">
                    <span className="text-xs sm:text-sm">{step.icon}</span>
                    <span
                      className={`text-xs hidden sm:inline ${
                        i <= currentStep
                          ? "text-amber-700 font-medium"
                          : "text-gray-400"
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* ====== 左侧：控制面板 ====== */}
          <div className="lg:col-span-3 space-y-5">
            {/* 上传区 */}
            <div className="bg-white rounded-2xl shadow-sm border border-amber-100 p-5">
              <h2 className="text-base font-semibold text-amber-900 mb-3">上传物品照片</h2>
              <div
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                  dragOver
                    ? "border-amber-500 bg-amber-50 scale-[1.02]"
                    : "border-amber-300 hover:border-amber-500 hover:bg-amber-50"
                }`}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
              >
                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt="预览"
                    className="max-h-40 mx-auto rounded-lg object-contain"
                  />
                ) : (
                  <div className="space-y-2">
                    <div className="text-3xl">📷</div>
                    <p className="text-sm text-amber-700">点击或拖拽上传</p>
                    <p className="text-xs text-amber-400">JPG / PNG</p>
                  </div>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileChange}
              />
            </div>

            {/* 风格选择 */}
            <div className="bg-white rounded-2xl shadow-sm border border-amber-100 p-5">
              <h2 className="text-base font-semibold text-amber-900 mb-3">故事风格</h2>
              <div className="space-y-2">
                {STYLES.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => setStyle(s.value)}
                    className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all ${
                      style === s.value
                        ? "border-amber-500 bg-amber-50 shadow-sm"
                        : "border-gray-100 hover:border-amber-200"
                    }`}
                  >
                    <span className="text-base mr-2">{s.emoji}</span>
                    <span className="font-medium text-amber-900 text-sm">{s.label}</span>
                    <span className="text-xs text-amber-500 ml-2">{s.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* 生成按钮 */}
            <button
              onClick={handleGenerate}
              disabled={loading || !selectedFile}
              className={`w-full py-4 rounded-2xl text-base font-bold transition-all ${
                loading || !selectedFile
                  ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                  : "bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600 shadow-lg hover:shadow-xl active:scale-[0.98]"
              }`}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  生成中... ({elapsed}s)
                </span>
              ) : (
                "生成寓言故事"
              )}
            </button>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-600 text-sm">
                {error}
              </div>
            )}

            {/* 视觉分析卡片 */}
            {result?.vision_analysis && (
              <div className="bg-white rounded-2xl shadow-sm border border-amber-100 p-5">
                <h2 className="text-base font-semibold text-amber-900 mb-3">物品分析</h2>
                <div className="space-y-2 text-sm">
                  <p>
                    <span className="font-medium text-amber-700">名称：</span>
                    {result.vision_analysis.item_name}
                  </p>
                  <p>
                    <span className="font-medium text-amber-700">特征：</span>
                    {result.vision_analysis.visual_features.join("、")}
                  </p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {result.vision_analysis.personality_traits.map((t, i) => (
                      <span
                        key={i}
                        className="bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full text-xs"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                  <p className="text-amber-600 italic text-xs mt-2">
                    &ldquo;{result.vision_analysis.story_character_hint}&rdquo;
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* ====== 中间：故事文本 ====== */}
          <div className="lg:col-span-5">
            <div className="bg-white rounded-2xl shadow-sm border border-amber-100 p-6 min-h-[600px]">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-amber-900">寓言故事</h2>
                {result?.story && (
                  <span className="text-xs text-amber-400">
                    {result.story.full_text.length} 字
                  </span>
                )}
              </div>

              {result?.story ? (
                <div className="space-y-5">
                  <div className="text-center pb-4 border-b border-amber-100">
                    <h3 className="text-2xl font-bold text-amber-800">
                      {result.story.title}
                    </h3>
                    {result.story_outline && (
                      <p className="text-sm text-amber-500 mt-1">
                        {result.story_outline.theme}
                      </p>
                    )}
                  </div>

                  <div className="space-y-5">
                    {result.story.page_texts.map((text, i) => (
                      <div key={i} className="group">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="w-6 h-6 bg-amber-100 text-amber-700 rounded-full text-xs flex items-center justify-center font-bold">
                            {i + 1}
                          </span>
                          {result.story_outline?.pages[i] && (
                            <span className="text-xs text-amber-400">
                              {result.story_outline.pages[i].scene} ·{" "}
                              {result.story_outline.pages[i].emotion}
                            </span>
                          )}
                        </div>
                        <p className="text-gray-700 text-sm leading-8 pl-8 border-l-2 border-amber-200 group-hover:border-amber-400 transition-colors">
                          {text}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* 底部操作 */}
                  <div className="pt-4 border-t border-amber-100 flex items-center justify-between">
                    <button
                      onClick={() => setShowBook(true)}
                      className="text-sm text-amber-600 hover:text-amber-800 font-medium transition-colors"
                    >
                      📖 进入绘本阅读模式
                    </button>
                    <span className="text-xs text-amber-300">
                      {result.step_timings?.pipeline_total || 0}s
                    </span>
                  </div>
                </div>
              ) : (
                <div className="h-96 flex flex-col items-center justify-center text-amber-300 gap-3">
                  <div className="text-5xl opacity-30">📖</div>
                  <p className="text-sm">上传图片并点击生成</p>
                  <p className="text-xs">故事将在这里展示</p>
                </div>
              )}
            </div>
          </div>

          {/* ====== 右侧：绘本画廊 ====== */}
          <div className="lg:col-span-4">
            <div className="bg-white rounded-2xl shadow-sm border border-amber-100 p-6 min-h-[600px]">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-amber-900">绘本插图</h2>
                {result?.image_urls && result.image_urls.filter(Boolean).length > 0 && (
                  <span className="text-xs text-amber-400">
                    {result.image_urls.filter(Boolean).length} 张
                  </span>
                )}
              </div>

              {result?.story_outline ? (
                <div className="space-y-4">
                  {result.story_outline.pages.map((page, i) => (
                    <div
                      key={i}
                      className="border border-amber-100 rounded-xl overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => {
                        if (result.image_urls[i]) {
                          setShowBook(true);
                        }
                      }}
                    >
                      <div className="bg-amber-50 aspect-[16/10] flex items-center justify-center text-amber-300 relative">
                        {result.image_urls[i] ? (
                          <>
                            <img
                              src={getImgUrl(result.image_urls[i])}
                              alt={`第${page.page}页插图`}
                              className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-0 bg-black/0 hover:bg-black/10 transition-colors flex items-center justify-center">
                              <span className="opacity-0 hover:opacity-100 text-white text-sm bg-black/40 px-3 py-1 rounded-full transition-opacity">
                                点击阅读
                              </span>
                            </div>
                          </>
                        ) : (
                          <div className="flex flex-col items-center gap-1">
                            <div className="animate-pulse w-8 h-8 bg-amber-200 rounded-full" />
                            <span className="text-xs">生成中...</span>
                          </div>
                        )}
                      </div>
                      <div className="p-3 flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-amber-800">
                            {page.scene}
                          </p>
                          <p className="text-xs text-amber-500">{page.emotion}</p>
                        </div>
                        <span className="text-xs text-amber-300">第{page.page}页</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-96 flex flex-col items-center justify-center text-amber-300 gap-3">
                  <div className="text-5xl opacity-30">🎨</div>
                  <p className="text-sm">插图将在这里展示</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 任务信息 */}
        {result && (
          <div className="mt-6 bg-white rounded-2xl shadow-sm border border-amber-100 p-4">
            <div className="flex flex-wrap gap-4 text-sm text-amber-600">
              <span>
                <span className="font-medium">任务：</span>
                {result.task_id}
              </span>
              <span>
                <span className="font-medium">状态：</span>
                <span className={result.status === "completed" ? "text-green-600" : "text-orange-500"}>
                  {result.status === "completed" ? "已完成" : result.status}
                </span>
              </span>
              {result.error_message && (
                <span className="text-orange-500">
                  <span className="font-medium">提示：</span>
                  {result.error_message}
                </span>
              )}
            </div>
            {result.step_timings &&
              Object.keys(result.step_timings).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-amber-400">
                  {Object.entries(result.step_timings)
                    .sort(([, a], [, b]) => b - a)
                    .map(([k, v]) => (
                      <span
                        key={k}
                        className="bg-amber-50 px-2 py-1 rounded"
                      >
                        {k}: {v}s
                      </span>
                    ))}
                </div>
              )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-amber-100 bg-white/40 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between text-xs text-amber-400">
          <span>FableLens v0.1.0 — 寓言透镜</span>
          <span>VLM + RAG + LangGraph + FLUX.1</span>
        </div>
      </footer>
    </div>
  );
}
