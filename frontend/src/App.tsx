import React, { useState, useEffect } from "react";
import { User, Message, EntityNode, RelationshipLink, Community } from "./types";
import LandingIntro from "./components/LandingIntro";
import AuthPanel from "./components/AuthPanel";
import GraphVisualizer from "./components/GraphVisualizer";
import { 
  Network, 
  Send, 
  Trash2, 
  Database, 
  Compass, 
  LogOut, 
  User as UserIcon, 
  BookOpen, 
  HelpCircle, 
  Settings, 
  UploadCloud, 
  FileText, 
  Activity, 
  Sparkles,
  RefreshCw,
  Sliders,
  CheckCircle2,
  AlertCircle
} from "lucide-react";

export default function App() {
  // Navigation states: 'landing' | 'auth' | 'workspace'
  const [view, setView] = useState<"landing" | "auth" | "workspace">("landing");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  
  // User Session state
  const [user, setUser] = useState<User | null>(null);

  // Graph state
  const [nodes, setNodes] = useState<EntityNode[]>([]);
  const [links, setLinks] = useState<RelationshipLink[]>([]);
  const [stats, setStats] = useState({
    entities: 0,
    relationships: 0,
    communities: 0
  });

  // Sidebar settings
  const [queryMode, setQueryMode] = useState<"graphrag" | "vector">("vector");
  const [topK, setTopK] = useState<number>(5);

  // Raw text upload states
  const [manualText, setManualText] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{
    type: "idle" | "processing" | "success" | "error";
    message: string;
  }>({ type: "idle", message: "" });

  const [selectedFileLabel, setSelectedFileLabel] = useState<string | null>(null);

  // Chat states
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "bot",
      text: "Chào mừng bạn đến với Math GraphRAG! Hệ thống đã nối với backend Neo4j thật. Hãy đặt câu hỏi về dữ liệu sách Toán đã được index.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      mode: null
    }
  ]);
  const [question, setQuestion] = useState("");
  const [loadingAnswer, setLoadingAnswer] = useState(false);

  // Load user from localStorage if saved
  useEffect(() => {
    const savedUser = localStorage.getItem("graphrag_user");
    if (savedUser) {
      try {
        const parsed = JSON.parse(savedUser);
        setUser(parsed);
        setView("workspace");
      } catch (err) {
        console.error("Failed to parse saved user", err);
      }
    }
    // Fetch initial graph data
    refreshGraphData();
  }, []);

  const refreshGraphData = async () => {
    try {
      const gRes = await fetch("/api/graph/data");
      if (gRes.ok) {
        const gData = await gRes.json();
        setNodes(gData.nodes || []);
        setLinks(gData.links || []);
      }

      const sRes = await fetch("/api/graph/stats");
      if (sRes.ok) {
        const sData = await sRes.json();
        setStats({
          entities: sData.total_entities || 0,
          relationships: sData.total_relationships || 0,
          communities: sData.total_communities || 0
        });
      }
    } catch (err) {
      console.error("Error refreshing graph statistics:", err);
    }
  };

  const handleAuthSuccess = (loggedUser: User) => {
    setUser(loggedUser);
    localStorage.setItem("graphrag_user", JSON.stringify(loggedUser));
    setView("workspace");
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("graphrag_user");
    setView("landing");
  };

  // Extract from text & build Graph
  const handleBuildGraph = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualText.trim()) return;

    setUploading(true);
    setUploadStatus({ type: "processing", message: "Đang gửi yêu cầu sang backend GraphRAG..." });

    try {
      const response = await fetch("/api/graph/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: manualText,
          filename: selectedFileLabel || "chu-de-tu-do.txt"
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Có lỗi khi phân tích văn bản.");
      }

      setUploadStatus({
        type: "success",
        message: `Đã kết xuất thành công ${data.extracted.nodesCount} đỉnh mới và ${data.extracted.linksCount} liên kết!`
      });
      setManualText("");
      setSelectedFileLabel(null);
      
      // Update graph lists and stats immediately
      refreshGraphData();

      // Add notice in chat
      setMessages(prev => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          role: "bot",
          text: `📢 [Thông báo Hệ thống] Đã nạp thành công dữ liệu mới vào Đồ thị tri thức! 
          \n- Thêm mới: +${data.extracted.nodesCount} Thực thể, +${data.extracted.linksCount} Mối quan hệ.
          \n- Hiện tại Đồ thị có: **${data.stats.total_entities} Entities**, **${data.stats.total_relationships} Relationships**.
          \nBạn đã có thể hỏi đáp nâng cao nhắm vào các thực thể vừa dệt cấu trúc.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          mode: null
        }
      ]);

    } catch (err: any) {
      setUploadStatus({
        type: "error",
        message: err.message || "Kết xuất lỗi, vui lòng thử lại."
      });
    } finally {
      setUploading(false);
    }
  };

  // Clear Graph Data
  const handleResetGraph = async () => {
    if (!window.confirm("Bạn có chắc chắn muốn xóa sạch toàn bộ Đồ thị tri thức để xây lại từ đầu?")) return;

    try {
      const r = await fetch("/api/graph/reset", { method: "POST" });
      if (r.ok) {
        setUploadStatus({ type: "idle", message: "" });
        refreshGraphData();
        setMessages([
          {
            id: `sys-reset-${Date.now()}`,
            role: "bot",
            text: "Đồ thị tri thức đã được dọn sạch về trạng thái ban đầu. Hãy nạp nguồn tài liệu mới.",
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            mode: null
          }
        ]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Submit search query
  const handleSendQuestion = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!question.trim() || loadingAnswer) return;

    const userMsgText = question;
    setQuestion("");
    setLoadingAnswer(true);

    const userMessage: Message = {
      id: `usr-${Date.now()}`,
      role: "user",
      text: userMsgText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMsgText,
          mode: queryMode,
          top_k: topK
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Gặp lỗi khi xử lý câu hỏi.");
      }

      setMessages(prev => [
        ...prev,
        {
          id: `bot-${Date.now()}`,
          role: "bot",
          text: data.answer,
          mode: data.mode,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);

    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: `bot-err-${Date.now()}`,
          role: "bot",
          text: `⚠️ Có lỗi xảy ra: ${err.message}. Hãy kiểm tra Python API, Neo4j và biến môi trường backend.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoadingAnswer(false);
    }
  };

  // Prepopulate query chips 
  const useQuickChip = (text: string) => {
    setQuestion(text);
  };

  // Trigger file upload read
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedFileLabel(file.name);
    
    // Check file type
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        setManualText(content);
        setUploadStatus({
          type: "idle",
          message: `Đã đọc được file "${file.name}" (${content.length} ký tự). Hãy bấm Build Graph để trích xuất.`
        });
      }
    };
    reader.onerror = () => {
      setUploadStatus({
        type: "error",
        message: "Không thể đọc tệp này. Thử copy dán nội dung thủ công."
      });
    };
    reader.readAsText(file);
  };

  // Main navigation switches
  if (view === "landing") {
    return (
      <LandingIntro
        onStart={() => {
          if (user) {
            setView("workspace");
          } else {
            setView("auth");
            setAuthMode("register");
          }
        }}
        onGoToAuth={(mode) => {
          setView("auth");
          setAuthMode(mode);
        }}
      />
    );
  }

  if (view === "auth") {
    return (
      <AuthPanel
        initialMode={authMode}
        onSuccess={handleAuthSuccess}
        onBack={() => setView("landing")}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col overflow-hidden">
      {/* Upper Unified Admin Navigation Header */}
      <header className="h-14 border-b border-slate-200 bg-white px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setView("landing")} 
            className="flex items-center gap-2 text-left hover:opacity-90 transition"
          >
            <div className="p-1 px-1.5 bg-indigo-600 text-white rounded-md">
              <Network className="w-4 h-4 stroke-[2.5]" />
            </div>
            <span className="font-extrabold text-sm tracking-tight text-slate-900 hidden sm:inline">
              Graph<span className="text-indigo-600 font-medium">RAG Explorer</span>
            </span>
          </button>
          
          <div className="h-4 w-[1px] bg-slate-100 hidden md:block"></div>

          {/* Symmetrical Stats Ribbon from user index */}
          <div className="flex items-center gap-4 text-[11px] font-mono leading-none">
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-2 py-1 rounded">
              <span className="text-slate-500">Entities:</span>
              <strong className="text-indigo-600 font-bold">{stats.entities.toLocaleString()}</strong>
            </div>

            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-2 py-1 rounded">
              <span className="text-slate-500">Relationships:</span>
              <strong className="text-purple-600 font-bold">{stats.relationships.toLocaleString()}</strong>
            </div>

            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-2 py-1 rounded hidden md:flex">
              <span className="text-slate-500">Communities:</span>
              <strong className="text-emerald-600 font-bold">{stats.communities.toLocaleString()}</strong>
            </div>
          </div>
        </div>

        {/* User Badge Profile / Log Out */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-50 px-3 py-1 rounded-lg border border-slate-200 text-xs text-slate-700">
            <UserIcon className="w-3.5 h-3.5 text-indigo-600" />
            <span className="max-w-[120px] truncate hidden md:inline">
              {user ? user.fullName : "Khách dùng thử"}
            </span>
          </div>

          <button
            onClick={handleLogout}
            className="p-1.5 bg-white border border-slate-200 hover:border-red-200 hover:bg-red-50 rounded-lg text-slate-500 hover:text-red-600 transition"
            title="Đăng xuất khỏi hệ thống"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Workspace Frame */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Control Sidebar */}
        <aside className="w-[300px] border-r border-slate-200 bg-white/40 p-4 shrink-0 overflow-y-auto flex flex-col gap-5">
          
          {/* Top segment: Build Knowledge Graph */}
          <div className="flex flex-col gap-3 p-3 bg-slate-50/50 border border-slate-200/80 rounded-xl">
            <div className="flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-indigo-600" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-700">Nạp dữ liệu nguồn</h2>
            </div>

            <p className="text-[10px] text-slate-500 leading-relaxed">
              Frontend đang nối với backend GraphRAG thật. Để nạp sách mới, chạy pipeline build index ở backend rồi bấm refresh/truy vấn lại.
            </p>

            <form onSubmit={handleBuildGraph} className="space-y-2.5">
              <div>
                <textarea
                  value={manualText}
                  onChange={(e) => setManualText(e.target.value)}
                  placeholder="Dán bất kỳ đoạn văn bản, khái niệm hoặc thông tin kỹ thuật nào..."
                  className="w-full h-24 p-2 bg-white border border-slate-200 rounded-lg text-xs placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition resize-none leading-relaxed text-slate-800"
                />
              </div>

              {/* Enhanced Interactive File Selector */}
              <div className="relative">
                <label className="flex items-center justify-center gap-1.5 py-2 px-3 border border-slate-200 border-dashed rounded-lg bg-white hover:bg-slate-50 cursor-pointer text-[11px] text-slate-500 hover:text-slate-900 transition">
                  <UploadCloud className="w-3.5 h-3.5 text-indigo-600" />
                  <span>{selectedFileLabel ? "Tập tin đã chọn ✓" : "Tải lên tài liệu TXT/MD/PDF"}</span>
                  <input
                    type="file"
                    accept=".txt,.md,.pdf,.json"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
                {selectedFileLabel && (
                  <p className="text-[9px] font-mono text-emerald-600 mt-1 text-center truncate">
                    📄 {selectedFileLabel}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={uploading || !manualText.trim()}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-200 disabled:opacity-30 disabled:hover:bg-indigo-600 text-white cursor-pointer active:translate-y-px transition flex items-center justify-center gap-1.5"
              >
                {uploading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Trích xuất...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-indigo-200" /> 🔨 Build Knowledge Graph
                  </>
                )}
              </button>
            </form>

            {/* Micro Status Indicators from instructions */}
            {uploadStatus.type !== "idle" && (
              <div className={`p-2.5 rounded-lg border text-[10px] leading-relaxed flex gap-1.5 ${
                uploadStatus.type === "processing" 
                  ? "bg-amber-50 border-amber-200 text-amber-700"
                  : uploadStatus.type === "success"
                  ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                  : "bg-red-50 border-red-200 text-red-700"
              }`}>
                {uploadStatus.type === "processing" && <RefreshCw className="w-3.5 h-3.5 shrink-0 animate-spin text-amber-600" />}
                {uploadStatus.type === "success" && <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-600" />}
                {uploadStatus.type === "error" && <AlertCircle className="w-3.5 h-3.5 shrink-0 text-red-600" />}
                <span>{uploadStatus.message}</span>
              </div>
            )}
          </div>

          {/* Mode parameters / top k slider */}
          <div className="flex flex-col gap-3.5 p-3 bg-slate-50/50 border border-slate-200/80 rounded-xl">
            <div className="flex items-center gap-1.5">
              <Sliders className="w-4 h-4 text-purple-600" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-700">Cấu hình truy vấn lai</h2>
            </div>

            {/* Mode selection options */}
            <div className="space-y-2">
              <label className="text-[10px] text-slate-500 font-mono uppercase tracking-wide">Query Mode</label>
              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => setQueryMode("vector")}
                  className={`py-1.5 rounded-lg text-[11px] font-semibold transition ${
                    queryMode === "vector"
                      ? "bg-indigo-600 text-white/15 border border-indigo-500/50 text-indigo-700"
                      : "bg-white border border-slate-200 text-slate-500 hover:text-slate-700"
                  }`}
                >
                  Factual Vector
                </button>
                <button
                  type="button"
                  onClick={() => setQueryMode("graphrag")}
                  className={`py-1.5 rounded-lg text-[11px] font-semibold transition ${
                    queryMode === "graphrag"
                      ? "bg-purple-600/15 border border-purple-500/50 text-purple-700"
                      : "bg-white border border-slate-200 text-slate-500 hover:text-slate-700"
                  }`}
                >
                  Global GraphRAG
                </button>
              </div>
              <p className="text-[9px] text-slate-500 leading-normal">
                {queryMode === "vector" 
                  ? "Tìm các thực thể khớp trực tiếp và các mối quan hệ liền kề. Cực kỳ tối ưu cho sự kiện cụ thể." 
                  : "Mở rộng liên kết nhóm, tổng hòa báo cáo cộng đồng để thấu hiểu câu hỏi rộng mang tính lập luận cao."
                }
              </p>
            </div>

            {/* Top k range selection */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-500 font-mono">Đo độ sâu thu hồi (K):</span>
                <span className="text-indigo-600 font-bold font-mono">{topK} facts</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                className="w-full accent-indigo-500 bg-white h-1 rounded cursor-pointer mt-1"
              />
            </div>
          </div>

          {/* Symmetrical Action Clear Tool as in index file */}
          <div className="mt-auto pt-2 flex flex-col gap-2">
            <button
              onClick={handleResetGraph}
              className="w-full py-2 hover:bg-red-50 hover:text-red-700 text-slate-500 hover:border-red-900/30 border border-slate-200 rounded-lg text-[10px] font-mono transition flex items-center justify-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5" /> DỌN DẸP TOÀN BỘ ĐỒ THỊ
            </button>
          </div>
        </aside>

        {/* Central Workspace Canvas split into Left: Chat + Right: Forces Visualizer */}
        <main className="flex-1 flex flex-col md:flex-row overflow-hidden bg-slate-50">
          
          {/* Chat Panel Partition */}
          <div className="flex-1 flex flex-col border-r border-slate-200 bg-white/20 overflow-hidden h-full">
            
            {/* Messages Screen */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col max-w-[85%] ${
                    msg.role === "user" ? "ml-auto items-end" : "mr-auto items-start"
                  }`}
                >
                  <span className="text-[9px] text-slate-500 font-mono mb-1 px-1">
                    {msg.role === "user" ? "Bạn" : "GraphRAG System"}
                  </span>

                  <div className={`p-3.5 rounded-2xl text-xs leading-relaxed border ${
                    msg.role === "user"
                      ? "bg-slate-100/80 border-indigo-500 text-slate-900 rounded-tr-none"
                      : "bg-indigo-50 border-indigo-200 text-slate-800 rounded-tl-none font-sans"
                  }`}>
                    {msg.mode && (
                      <span className={`inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full mb-1.5 ${
                        msg.mode === "graphrag" 
                          ? "bg-purple-50 border border-purple-200 text-purple-700"
                          : "bg-indigo-50 border border-indigo-200 text-indigo-700"
                      }`}>
                        {msg.mode === "graphrag" ? "🌐 Global GraphRAG Mode" : "🎯 Vector Facts Mode"}
                      </span>
                    )}
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                  </div>
                </div>
              ))}

              {loadingAnswer && (
                <div className="mr-auto items-start flex flex-col max-w-[80%] gap-1">
                  <span className="text-[9px] text-slate-500 font-mono">system</span>
                  <div className="p-3 bg-slate-50/40 border border-slate-200/50 rounded-2xl rounded-tl-none flex items-center gap-1.5 self-start">
                    <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce"></span>
                    <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce delay-100"></span>
                    <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce delay-200"></span>
                    <span className="text-[10px] text-slate-500 ml-1.5 font-mono">Đồ thị đang được truy vấn...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Chips Prompts area as in user index visual style */}
            {messages.length === 1 && (
              <div className="px-4 py-2 flex flex-wrap gap-1.5 bg-white/40 justify-center">
                <button
                  onClick={() => useQuickChip("Tóm tắt nội dung chính đang có trong đồ thị tri thức")}
                  className="px-2.5 py-1 bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-indigo-700 border border-slate-200 rounded-full text-[10px] transition cursor-pointer"
                >
                  📋 Tóm tắt chính
                </button>
                <button
                  onClick={() => useQuickChip("Các loại thực thể là gì và liên hệ với nhau ra sao?")}
                  className="px-2.5 py-1 bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-indigo-700 border border-slate-200 rounded-full text-[10px] transition cursor-pointer"
                >
                  🕸 Liên hệ thực thể
                </button>
                <button
                  onClick={() => useQuickChip("Giải thích mối liên kết giữa các node quan trọng")}
                  className="px-2.5 py-1 bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-indigo-700 border border-slate-200 rounded-full text-[10px] transition cursor-pointer"
                >
                  🔗 Giải thích liên kết
                </button>
              </div>
            )}

            {/* Input Bar Section */}
            <div className="p-4 bg-white/80 border-t border-slate-200/80">
              <form onSubmit={handleSendQuestion} className="flex gap-2">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Đặt câu hỏi thông thái dựa trên các thực thể & mối quan hệ..."
                  className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 transition"
                  disabled={loadingAnswer}
                />
                <button
                  type="submit"
                  disabled={loadingAnswer || !question.trim()}
                  className="px-4 py-2 bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-slate-100 disabled:text-slate-400 rounded-xl transition shadow-lg shadow-indigo-200 flex items-center justify-center shrink-0 cursor-pointer disabled:opacity-40"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
              <div className="flex justify-between text-[9px] text-slate-500 mt-2 font-mono">
                <span>Nhấn Enter để gửi đi nhanh</span>
                <span>Backend: Math GraphRAG + Neo4j</span>
              </div>
            </div>
          </div>

          {/* Right Graph Visualizer Panel */}
          <div className="flex-1 md:max-w-[48%] h-full p-4 flex flex-col gap-4 overflow-hidden bg-white/40">
            <div className="flex-1 h-full min-h-[350px]">
              <GraphVisualizer 
                nodes={nodes} 
                links={links} 
                onSelectNode={(node) => {
                  // Add a micro recommendation hint directly in input so they can easily query about clicked nodes:
                  setQuestion(`Giải thích mối quan hệ và ý nghĩa thực thể "${node.label}"`);
                }}
              />
            </div>
          </div>

        </main>
      </div>
    </div>
  );
}
