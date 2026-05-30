# Math GraphRAG LangChain

Project này xây dựng hệ thống **Domain Knowledge Graph + GraphRAG** cho dữ liệu PDF/Markdown sách Toán cấp 3 tiếng Việt.

Pipeline chính:

```text
PDF scan / Markdown sách
→ Preprocess Markdown, giữ số trang
→ Chunking theo cấu trúc sách
→ LLM batch extract Entity + Relationship, có type + semantic_summary
→ Lưu graph vào Neo4j local
→ Phân cụm phân tầng community theo tinh thần Microsoft GraphRAG
→ Embedding chunk/entity/community
→ Query decomposition + hybrid retrieval + graph expansion
→ Query bằng terminal chat
```

## Các chỉnh sửa chính trong bản này

- Đã bỏ Docker khỏi project. Neo4j dùng bản local trên máy của bạn.
- Thêm `ENV_EXAMPLE.txt` để dễ nhìn trên Windows. Copy file này thành `.env`.
- Bỏ bước merge node riêng biệt; khi ghi Neo4j chỉ dùng khóa chuẩn hóa để tránh tạo node rác.
- Extraction chuyển sang batch extraction (`extraction.batch_size`) để LLM nhìn nhiều chunk gần nhau và sinh thêm `cross_chunk_relationships`.
- Entity được bổ sung `type`, `semantic_summary`, `definition`, `properties` để node có ngữ nghĩa rõ hơn.
- Community detection được sửa thành phân cụm phân tầng: ưu tiên `hierarchical_leiden`, fallback bằng recursive greedy community nếu môi trường không cài được `graspologic`.
- Query understanding có thêm `sub_queries` để query decomposition trước khi hybrid retrieval.

Nếu bạn đã OCR PDF sang Markdown rồi thì **không cần chạy lại PDF/Marker**. Chỉ cần chạy preprocess, build index, rồi chat.

---

## 1. Cấu trúc project

```text
math_graphrag_final/
├── chat.py
├── ENV_EXAMPLE.txt                  # file mẫu env dễ nhìn trên Windows
├── .env.example                     # file mẫu env dạng chuẩn, có thể bị Windows ẩn
├── scripts/
│   ├── 01_marker_ocr.py             # PDF scan -> Markdown bằng Marker, optional
│   ├── 01_preprocess_md.py          # làm sạch Markdown sau OCR, giữ số trang
│   ├── 02_build_index.py            # build graph/vector/community vào Neo4j local
│   └── run_pipeline.py
├── src/math_graphrag/
│   ├── schema.py
│   ├── preprocess.py
│   ├── chunking.py
│   ├── extraction.py
│   ├── neo4j_store.py
│   ├── community.py
│   ├── indexing.py
│   ├── retrieval.py
│   ├── query_understanding.py
│   ├── llm.py
│   ├── embedding.py
│   └── prompts.py
├── configs/config.yaml
├── requirements.txt
├── pyproject.toml
└── data/
    ├── pdf/
    ├── md_raw/
    ├── md_clean/
    └── output/
```

---

## 2. Cài môi trường Python

### Windows PowerShell

```bash
cd math_graphrag_final
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

### Linux / macOS

```bash
cd math_graphrag_final
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

`pip install -e .` giúp Python import được package `math_graphrag` từ thư mục `src/`.

---

## 3. Chuẩn bị Neo4j local

Project này **không dùng Docker** nữa.

Bạn mở Neo4j Desktop hoặc Neo4j local server đang có trên máy, sau đó bật database.

Thông tin thường dùng:

```text
URI: bolt://localhost:7687
User: neo4j
Password: mật khẩu Neo4j local của bạn
Database: neo4j
```

Kiểm tra Neo4j Browser:

```text
http://localhost:7474
```

Đăng nhập được Neo4j Browser thì project mới kết nối được qua `bolt://localhost:7687`.

---

## 4. Tạo file `.env`

Vì Windows có thể ẩn file bắt đầu bằng dấu chấm, project có sẵn file:

```text
ENV_EXAMPLE.txt
```

Copy thành `.env`:

### Windows PowerShell

```bash
copy ENV_EXAMPLE.txt .env
```

### Linux / macOS

```bash
cp ENV_EXAMPLE.txt .env
```

Mở `.env` và sửa:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mat_khau_neo4j_local_cua_ban

LLM_PROVIDER=gemini
GOOGLE_API_KEY=api_key_gemini_cua_ban
```

Nếu Gemini báo `API key expired`, tạo key mới rồi thay vào `GOOGLE_API_KEY`.

---

## 5. Đặt dữ liệu Markdown

Nếu đã có Markdown sau OCR, đặt vào:

```text
data/md_raw/
```

Ví dụ:

```text
data/md_raw/giaitich12.md
```

Sau đó chạy preprocess:

```bash
python scripts/01_preprocess_md.py --input data/md_raw --output data/md_clean
```

Hoặc chạy riêng một file:

```bash
python scripts/01_preprocess_md.py --input data/md_raw/giaitich12.md --output data/md_clean/giaitich12.md
```

Bước này sẽ làm sạch lỗi OCR nhẹ và giữ số trang. Nếu Markdown có marker như dưới đây thì hệ thống có thể dẫn chứng trang khi trả lời:

```md
<!-- page: 12 -->
```

---

## 6. Build GraphRAG index vào Neo4j local

Chạy build lại từ đầu:

```bash
python scripts/02_build_index.py --reset
```

Lệnh này sẽ làm:

```text
đọc data/md_clean
→ chunking
→ batch extract entity/relationship
→ lưu graph vào Neo4j local
→ phân cụm phân tầng community
→ summarize community
→ embedding chunk/entity/community
→ tạo index tìm kiếm
```

Nếu không muốn xóa dữ liệu cũ trong Neo4j:

```bash
python scripts/02_build_index.py
```

Nhưng khi vừa sửa pipeline, nên dùng `--reset`.

---

## 7. Chat thử

```bash
python chat.py
```

Ví dụ hỏi:

```text
Đạo hàm là gì?
```

hoặc:

```text
Trình bày các công thức đạo hàm cơ bản và dẫn chứng trang trong sách.
```

---

## 8. Lệnh chạy nhanh trên Windows

```bash
cd math_graphrag_final
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
copy ENV_EXAMPLE.txt .env
```

Sau đó sửa `.env`, bật Neo4j local, rồi chạy:

```bash
python scripts/01_preprocess_md.py --input data/md_raw --output data/md_clean
python scripts/02_build_index.py --reset
python chat.py
```

---

## 9. Lỗi hay gặp

### Không thấy `.env.example`

Dùng file này thay thế:

```text
ENV_EXAMPLE.txt
```

Rồi copy:

```bash
copy ENV_EXAMPLE.txt .env
```

### Lỗi `ModuleNotFoundError: No module named 'math_graphrag'`

Chạy lại:

```bash
pip install -e .
```

### Lỗi Neo4j `ServiceUnavailable`

Kiểm tra:

```text
1. Neo4j local đã Start chưa?
2. Neo4j Browser có vào được http://localhost:7474 không?
3. Password trong .env có đúng không?
4. URI có đúng bolt://localhost:7687 không?
```

### Build quá chậm hoặc JSON extract hay lỗi

Giảm batch size trong `configs/config.yaml`:

```yaml
extraction:
  batch_size: 2
```

Nếu vẫn lỗi, giảm tiếp:

```yaml
extraction:
  batch_size: 1
```

### Muốn xóa graph cũ

Dùng:

```bash
python scripts/02_build_index.py --reset
```
