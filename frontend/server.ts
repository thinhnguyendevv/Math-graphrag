import express from "express";
import path from "path";
import fs from "fs";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = Number(process.env.FRONTEND_PORT || 3000);
const GRAPH_API_URL = (process.env.GRAPH_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

app.use(express.json({ limit: "50mb" }));

const DB_DIR = path.join(process.cwd(), "data");
const DB_FILE = path.join(DB_DIR, "db.json");

interface UserRecord {
  email: string;
  passwordHash: string;
  fullName: string;
}
interface DBStructure {
  users: UserRecord[];
}

function initDB(): DBStructure {
  if (!fs.existsSync(DB_DIR)) fs.mkdirSync(DB_DIR, { recursive: true });
  if (fs.existsSync(DB_FILE)) {
    try {
      const old = JSON.parse(fs.readFileSync(DB_FILE, "utf-8"));
      return { users: Array.isArray(old.users) ? old.users : [] };
    } catch (e) {
      console.error("Error reading local auth db, resetting:", e);
    }
  }
  const defaultDB = { users: [] };
  saveDB(defaultDB);
  return defaultDB;
}

function saveDB(db: DBStructure) {
  fs.writeFileSync(DB_FILE, JSON.stringify(db, null, 2), "utf-8");
}

let db = initDB();

async function proxyToGraphAPI(req: express.Request, res: express.Response, apiPath: string) {
  try {
    const targetUrl = `${GRAPH_API_URL}${apiPath}`;
    const response = await fetch(targetUrl, {
      method: req.method,
      headers: { "Content-Type": "application/json" },
      body: ["GET", "HEAD"].includes(req.method) ? undefined : JSON.stringify(req.body || {}),
    });

    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
      const message = typeof data === "object" && data !== null
        ? (data.detail || data.error || JSON.stringify(data))
        : String(data);
      return res.status(response.status).json({ error: message });
    }
    return res.status(response.status).json(data);
  } catch (error: any) {
    return res.status(502).json({
      error: `Không kết nối được Python GraphRAG API tại ${GRAPH_API_URL}. Hãy chạy: uvicorn api:app --host 127.0.0.1 --port 8000`,
      detail: error?.message || String(error),
    });
  }
}

// Local auth only for frontend session.
app.post("/api/auth/register", (req, res) => {
  const { email, password, fullName } = req.body;
  if (!email || !password || !fullName) return res.status(400).json({ error: "Vui lòng điền đầy đủ thông tin" });

  const normalizedEmail = String(email).toLowerCase().trim();
  if (db.users.some(u => u.email === normalizedEmail)) return res.status(400).json({ error: "Email này đã được sử dụng" });

  const newUser = { email: normalizedEmail, passwordHash: String(password), fullName: String(fullName).trim() };
  db.users.push(newUser);
  saveDB(db);
  return res.json({ success: true, message: "Đăng ký tài khoản thành công!", user: { email: newUser.email, fullName: newUser.fullName } });
});

app.post("/api/auth/login", (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ error: "Vui lòng nhập Email và Mật khẩu" });

  const normalizedEmail = String(email).toLowerCase().trim();
  const user = db.users.find(u => u.email === normalizedEmail && u.passwordHash === String(password));
  if (!user) return res.status(401).json({ error: "Email hoặc mật khẩu không chính xác" });

  return res.json({ success: true, message: "Đăng nhập thành công!", user: { email: user.email, fullName: user.fullName } });
});

// Real GraphRAG endpoints proxied to Python backend.
app.get("/api/health", (req, res) => proxyToGraphAPI(req, res, "/api/health"));
app.get("/api/graph/stats", (req, res) => proxyToGraphAPI(req, res, "/api/graph/stats"));
app.get("/api/graph/data", (req, res) => proxyToGraphAPI(req, res, "/api/graph/data"));
app.post("/api/query", (req, res) => proxyToGraphAPI(req, res, "/api/query"));
app.post("/api/graph/reset", (req, res) => proxyToGraphAPI(req, res, "/api/graph/reset"));
app.post("/api/graph/build", (req, res) => proxyToGraphAPI(req, res, "/api/graph/build"));

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({ server: { middlewareMode: true }, appType: "spa" });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => res.sendFile(path.join(distPath, "index.html")));
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Frontend: http://localhost:${PORT}`);
    console.log(`GraphRAG API: ${GRAPH_API_URL}`);
  });
}

startServer();
