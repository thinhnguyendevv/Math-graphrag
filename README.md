# Math GraphRAG: Frontend trắng + Backend Neo4j đã nối API

## Cấu trúc

- `backend/`: backend GraphRAG Python thật, đọc dữ liệu từ Neo4j và trả lời bằng `GraphRAGRetriever`.
- `frontend/`: giao diện React/Vite theme trắng, các route `/api/query`, `/api/graph/stats`, `/api/graph/data` đã proxy sang Python API.

## 1. Chạy Neo4j

Mở Neo4j Desktop và start database đang chứa dữ liệu đã index.

File `backend/.env` cần có dạng:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mat_khau_cua_ban
GOOGLE_API_KEY=api_key_moi_neu_dung_gemini
LLM_PROVIDER=gemini
```

## 2. Chạy backend Python API

Trong thư mục `backend`:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Kiểm tra nhanh:

```text
http://127.0.0.1:8000/api/health
```

## 3. Chạy frontend theme trắng

Mở terminal khác, trong thư mục `frontend`:

```powershell
npm install
npm run dev
```

Mở:

```text
http://localhost:3000
```

## Ghi chú quan trọng

- Frontend không còn tự dùng Gemini để build graph giả nữa. Nó gọi backend GraphRAG thật qua `GRAPH_API_URL=http://127.0.0.1:8000`.
- Muốn nạp sách mới: chạy pipeline build/index ở backend như cũ, sau đó refresh frontend.
- Nếu frontend báo không kết nối được Python API, kiểm tra backend API đã chạy ở port `8000` chưa.
- Nếu backend báo lỗi Neo4j, kiểm tra Neo4j Desktop, mật khẩu và biến môi trường trong `.env`.
