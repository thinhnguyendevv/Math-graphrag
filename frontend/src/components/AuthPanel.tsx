import React, { useState } from "react";
import { User } from "../types";
import { ShieldAlert, ArrowLeft, Key, Mail, User as UserIcon, LogIn, UserPlus } from "lucide-react";

interface AuthPanelProps {
  initialMode: "login" | "register";
  onSuccess: (user: User) => void;
  onBack: () => void;
}

export default function AuthPanel({ initialMode, onSuccess, onBack }: AuthPanelProps) {
  const [mode, setMode] = useState<"login" | "register">(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!email || !password || (mode === "register" && !fullName)) {
      setError("Vui lòng điền đầy đủ tất cả thông tin yêu cầu.");
      return;
    }

    setLoading(true);
    const endpoint = mode === "register" ? "/api/auth/register" : "/api/auth/login";
    const body = mode === "register" 
      ? { email, password, fullName } 
      : { email, password };

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Có lỗi xảy ra, vui lòng thử lại.");
      }

      if (mode === "register") {
        setMessage("Đăng ký thành công! Đang tự động đăng nhập...");
        setTimeout(() => {
          onSuccess({ email: email.toLowerCase().trim(), fullName: fullName.trim() });
        }, 1200);
      } else {
        setMessage("Đăng nhập thành công!");
        setTimeout(() => {
          onSuccess(data.user);
        }, 800);
      }
    } catch (err: any) {
      setError(err.message || "Không thể kết nối đến máy chủ.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col justify-center items-center px-4 relative">
      {/* Background radial soft light blobs */}
      <div className="absolute top-1/4 left-1/4 w-80 h-80 bg-indigo-100/60 rounded-full blur-3xl -z-10 animate-pulse"></div>
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-600/10 rounded-full blur-3xl -z-10"></div>

      <button
        onClick={onBack}
        className="absolute top-6 left-6 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition"
      >
        <ArrowLeft className="w-4 h-4" />
        Quay lại trang chủ
      </button>

      <div className="w-full max-w-md bg-slate-50 border border-slate-200 rounded-2xl p-8 shadow-2xl">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-black text-slate-900 leading-tight">
            {mode === "login" ? "Chào mừng trở lại" : "Tạo tài khoản mới"}
          </h2>
          <p className="text-xs text-slate-500 mt-2">
            {mode === "login" 
              ? "Hãy đăng nhập để lưu trữ Đồ thị Tri thức và lịch sử truy vấn" 
              : "Bản đồ liên kết và hệ thống GraphRAG đang đợi thực thi"
            }
          </p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex gap-2 items-center">
            <ShieldAlert className="w-4 h-4 shrink-0 text-red-600" />
            <span>{error}</span>
          </div>
        )}

        {message && (
          <div className="mb-5 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs flex gap-2 items-center">
            <LogIn className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>{message}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <div>
              <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-1.5">
                Họ và Tên
              </label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Ví dụ: Nguyễn Văn A"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors"
                  required
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-1.5">
              Địa chỉ Email
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
              <input
                type="email"
                placeholder="email@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-1.5">
              Mật khẩu
            </label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
              <input
                type="password"
                placeholder="Nhập mật khẩu"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 mt-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition shadow-lg shadow-indigo-200 flex items-center justify-center gap-1.5 disabled:opacity-40 select-none active:translate-y-px"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            ) : mode === "login" ? (
              <>
                <LogIn className="w-4 h-4" /> Đăng nhập hệ thống
              </>
            ) : (
              <>
                <UserPlus className="w-4 h-4" /> Đăng ký thành viên
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-slate-200 text-center">
          <button
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="text-xs text-indigo-600 hover:text-indigo-700 transition"
          >
            {mode === "login" 
              ? "Bạn chưa có tài khoản? Đăng ký ngay" 
              : "Đã sẵn có tài khoản? Quay về Đăng nhập"
            }
          </button>
        </div>
      </div>
    </div>
  );
}
