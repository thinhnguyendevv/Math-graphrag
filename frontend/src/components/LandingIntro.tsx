import React from "react";
import { Network, Search, Cpu, Database, ChevronRight, Server, CheckCircle, Shield, FileText } from "lucide-react";

interface LandingIntroProps {
  onStart: () => void;
  onGoToAuth: (mode: "login" | "register") => void;
}

export default function LandingIntro({ onStart, onGoToAuth }: LandingIntroProps) {
  return (
    <div className="min-h-screen bg-white text-slate-900 flex flex-col justify-between overflow-y-auto select-none">
      {/* Header section */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-indigo-600 text-white rounded-lg shadow-lg shadow-indigo-200">
              <Network className="w-5.5 h-5.5 text-white stroke-[2.5]" />
            </div>
            <span className="font-extrabold text-lg tracking-tight text-slate-900 bg-clip-text">
              Graph<span className="text-indigo-500 font-medium">RAG Explorer</span>
            </span>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => onGoToAuth("login")}
              className="text-slate-500 hover:text-slate-900 transition-colors text-sm font-medium"
            >
              Đăng nhập
            </button>
            <button
              onClick={() => onGoToAuth("register")}
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition shadow-lg shadow-indigo-200 active:translate-y-px"
            >
              Đăng ký dùng thử
            </button>
          </div>
        </div>
      </header>

      {/* Hero section */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-12 md:py-16 grid md:grid-cols-12 gap-12 items-center">
        <div className="md:col-span-7 flex flex-col gap-6 text-left">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 border border-indigo-200 rounded-full text-indigo-600 text-xs font-mono w-fit">
            <Cpu className="w-3.5 h-3.5" />
            <span>Next-Gen Information Retrieval System</span>
          </div>

          <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 leading-tight tracking-tight">
            Vượt xa Tìm kiếm Văn bản.<br />
            Khai phá Sức mạnh của<br />
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              Knowledge Graph & GraphRAG
            </span>
          </h2>

          <p className="text-slate-500 text-sm md:text-[15px] leading-relaxed max-w-xl">
            Các hệ thống RAG truyền thống tìm kiếm tài liệu dựa trên mức độ khớp văn bản tĩnh (Vector Search), hoàn toàn bỏ lỡ mối quan hệ sâu sắc giữa các khái niệm.
            <strong> GraphRAG Explorer</strong> dùng AI trích xuất các Thực thể dệt thành Đồ thị Tri thức Động để trả lời những câu hỏi mang tính cấu trúc tổng thể phức tạp.
          </p>

          <div className="flex flex-col sm:flex-row gap-3.5 mt-2">
            <button
              onClick={onStart}
              className="px-6 py-3.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition shadow-xl shadow-indigo-600/30 flex items-center justify-center gap-2 group active:translate-y-px cursor-pointer"
            >
              Trải nghiệm ứng dụng ngay
              <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </button>
            <button
              onClick={() => {
                const element = document.getElementById("features-section");
                element?.scrollIntoView({ behavior: "smooth" });
              }}
              className="px-6 py-3.5 text-sm font-medium text-slate-700 hover:text-slate-900 border border-slate-200 hover:border-slate-700 bg-slate-50/40 hover:bg-slate-50/60 rounded-xl transition flex items-center justify-center gap-2"
            >
              Tìm hiểu hoạt động
            </button>
          </div>

          {/* Quick stats banner */}
          <div className="grid grid-cols-3 gap-6 pt-6 border-t border-slate-200 mt-4">
            <div>
              <div className="text-2xl font-black text-slate-900 font-mono">98%</div>
              <p className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">Bảo toàn văn cảnh</p>
            </div>
            <div>
              <div className="text-2xl font-black text-indigo-600 font-mono">10x</div>
              <p className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">Sự thông hiểu liên ngữ</p>
            </div>
            <div>
              <div className="text-2xl font-black text-purple-600 font-mono">Gemini</div>
              <p className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">Đối tác trí tuệ</p>
            </div>
          </div>
        </div>

        {/* Dynamic decorative model display of Graph vs Vector */}
        <div className="md:col-span-5 relative flex justify-center items-center">
          <div className="absolute w-72 h-72 bg-indigo-100/60 rounded-full blur-3xl -z-10 animate-pulse"></div>
          <div className="w-full max-w-sm bg-gradient-to-b from-white to-slate-50 p-[1px] rounded-2xl border border-slate-200 shadow-2xl">
            <div className="bg-white rounded-2xl p-6 flex flex-col gap-5">
              <div className="flex justify-between items-center border-b border-slate-200 pb-3">
                <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">Kiến trúc So sánh</span>
                <span className="px-2 py-0.5 bg-slate-50 text-[10px] text-indigo-600 font-mono rounded">Methodology</span>
              </div>

              {/* Vector RAG list */}
              <div className="flex flex-col gap-2 bg-slate-50/30 border border-slate-200/50 p-3 rounded-xl">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500">
                  <div className="p-1 rounded bg-slate-100 text-slate-500">
                    <Search className="w-3.5 h-3.5" />
                  </div>
                  <span>Vector RAG Thông thường</span>
                </div>
                <p className="text-[11px] text-slate-500">
                  Cắt văn bản thành các Chunk biệt lập. Tìm kiếm chỉ đối khớp khoảng cách từ ngữ (Semantic search). Không hiểu được mối liên hệ chéo.
                </p>
              </div>

              {/* Arrow sign */}
              <div className="flex justify-center -my-2">
                <div className="w-0.5 h-6 bg-indigo-500/20"></div>
              </div>

              {/* GraphRAG list */}
              <div className="flex flex-col gap-2 bg-indigo-50 border border-indigo-200 p-3.5 rounded-xl">
                <div className="flex items-center gap-2 text-xs font-bold text-indigo-600">
                  <div className="p-1 rounded bg-indigo-900/40 text-indigo-600">
                    <Network className="w-3.5 h-3.5" />
                  </div>
                  <span>GraphRAG Thống hợp</span>
                </div>
                <p className="text-[11px] text-indigo-700/80">
                  Các Chunk được AI phân tích trích xuất <strong>Entities (Thực thể)</strong> và <strong>Relationships (Cung liên kết)</strong> tạo thành bản đồ mạng lưới giúp dẫn dắt LLM tổng ôn văn cảnh cực kỳ sâu sắc.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Features section layout */}
      <section id="features-section" className="bg-slate-50/30 border-t border-slate-200 py-16 px-6">
        <div className="max-w-7xl mx-auto flex flex-col gap-10">
          <div className="text-center max-w-xl mx-auto flex flex-col gap-2.5">
            <h3 className="text-2xl font-extrabold text-slate-900">Tính năng Nổi bật trong Hệ sinh thái</h3>
            <p className="text-slate-500 text-xs md:text-sm">
              Trang bị toàn diện các module hoạt động hoàn chỉnh và tối ưu hóa cho người dùng.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white/50 p-5 rounded-2xl border border-slate-200/70 hover:border-indigo-200 transition">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 mb-4 border border-indigo-200">
                <FileText className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-sm text-slate-900 mb-2">Trích xuất Tri thức Thực thể</h4>
              <p className="text-slate-500 text-xs leading-relaxed">
                Nạp tài liệu dài hoặc dán văn bản tùy thích. Gemini sẽ phân tích ngữ nghĩa, nhận diện các danh từ khoa học, lý thuyết hoặc nhân vật để gắn nhãn danh vị.
              </p>
            </div>

            <div className="bg-white/50 p-5 rounded-2xl border border-slate-200/70 hover:border-indigo-200 transition">
              <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600 mb-4 border border-purple-200">
                <Network className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-sm text-slate-900 mb-2">Đồ thị Tri thức Động</h4>
              <p className="text-slate-500 text-xs leading-relaxed">
                Mô phỏng đồ thị 2D dựa trên mô hình vật lý lò xo tương tác chuột thật. Tự do kéo thả, click phóng to chi tiết hay kiểm tra quan hệ bắc cầu mượt mà.
              </p>
            </div>

            <div className="bg-white/50 p-5 rounded-2xl border border-slate-200/70 hover:border-indigo-200 transition">
              <div className="w-10 h-10 rounded-xl bg-blue-950 flex items-center justify-center text-blue-400 mb-4 border border-blue-900/30">
                <Database className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-sm text-slate-900 mb-2">Hai chế độ truy vấn lai</h4>
              <p className="text-slate-500 text-xs leading-relaxed">
                Linh hoạt chuyển đổi: Chế độ <strong>GraphRAG</strong> phục vụ câu hỏi tổng hợp bao quát cộng đồng, và Chế độ <strong>Vector</strong> cho các sự kiện chi tiết hóa cục bộ.
              </p>
            </div>

            <div className="bg-white/50 p-5 rounded-2xl border border-slate-200/70 hover:border-indigo-200 transition">
              <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center text-slate-500 mb-4 border border-slate-200">
                <Shield className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-sm text-slate-900 mb-2">Bảo trì cá nhân hóa</h4>
              <p className="text-slate-500 text-xs leading-relaxed">
                Hệ thống đăng ký đăng nhập giúp lưu giữ sơ đồ đồ thị cá nhân của bạn trên trình duyệt, không lo thất lạc thông tin bài tập hay tài liệu giảng dạy.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer text */}
      <footer className="border-t border-slate-200 bg-white py-6 px-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-3">
          <p>© 2026 GraphRAG Explorer. Thiết kế thông tin tinh tuyển, cấu trúc tối ưu.</p>
          <div className="flex gap-4">
            <span className="hover:text-slate-500 transition cursor-pointer">LlamaIndex Ecosystem</span>
            <span className="hover:text-slate-500 transition cursor-pointer">Neo4j Technology Group</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
