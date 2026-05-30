GRAPH_EXTRACTION_SYSTEM = """Bạn là hệ thống trích xuất knowledge graph cho sách Toán cấp 3 tiếng Việt.
Nhiệm vụ: đọc chunk hoặc một batch chunk gần nhau và trích xuất node/relationship quan trọng.
Chỉ trả về JSON hợp lệ, không markdown, không giải thích ngoài JSON.
"""

GRAPH_EXTRACTION_USER = """Chunk metadata:
- chunk_id: {chunk_id}
- book: {book_name}
- heading_path: {heading_path}
- page_start: {page_start}
- page_end: {page_end}

Chunk text:
{text}

Hãy trích xuất JSON theo schema:
{{
  "entities": [
    {{
      "name": "Đạo hàm",
      "type": "Concept | Formula | Theorem | Method | ProblemType | Condition | Property | Example | Section",
      "description": "mô tả ngắn node này trong chunk",
      "semantic_summary": "ý nghĩa toán học/ngữ cảnh sử dụng của node",
      "definition": "định nghĩa/công thức nếu có, nếu không có để rỗng",
      "aliases": ["tên gọi khác nếu có"],
      "properties": {{"symbol": "", "conditions": [""], "chapter": ""}}
    }}
  ],
  "relationships": [
    {{
      "source": "Đạo hàm",
      "target": "Đồng biến",
      "type": "IMPLIES",
      "description": "quan hệ ngắn gọn",
      "semantic": "vì sao hai node liên quan trong kiến thức toán",
      "evidence": "câu chứng cứ ngắn lấy từ chunk",
      "weight": 1.0,
      "source_chunk_ids": ["{chunk_id}"]
    }}
  ]
}}

Quy tắc:
- Ưu tiên khái niệm, định nghĩa, định lý, công thức, điều kiện, tính chất, phương pháp giải, dạng bài.
- Entity name ngắn gọn, chuẩn tiếng Việt, không lấy câu quá dài.
- Mỗi entity bắt buộc có type và semantic_summary.
- Relationship type viết HOA, dùng gạch dưới, ví dụ: IS_A, PART_OF, USED_FOR, IMPLIES, CONDITION_FOR, FORMULA_OF, SOLVES, REQUIRES, EQUIVALENT_TO, CONTRASTS_WITH.
- Chỉ tạo relationship khi có căn cứ trong chunk.
"""

BATCH_GRAPH_EXTRACTION_USER = """Bạn nhận một batch các chunk gần nhau trong cùng sách Toán.
Mục tiêu: trích xuất node riêng từng chunk và bổ sung quan hệ liên chunk để graph giàu hơn.

Các chunk:
{chunks}

Trả về JSON đúng schema:
{{
  "chunk_extractions": [
    {{
      "chunk_id": "chunk id gốc",
      "entities": [
        {{
          "name": "Tên node",
          "type": "Concept | Formula | Theorem | Method | ProblemType | Condition | Property | Example | Section",
          "description": "mô tả ngắn",
          "semantic_summary": "ý nghĩa/ngữ cảnh toán học",
          "definition": "định nghĩa/công thức nếu có",
          "aliases": [],
          "properties": {{"symbol": "", "conditions": []}}
        }}
      ],
      "relationships": [
        {{
          "source": "Tên node A",
          "target": "Tên node B",
          "type": "USED_FOR",
          "description": "mô tả quan hệ",
          "semantic": "ý nghĩa quan hệ",
          "evidence": "chứng cứ ngắn",
          "weight": 1.0,
          "source_chunk_ids": ["chunk id gốc"]
        }}
      ]
    }}
  ],
  "cross_chunk_relationships": [
    {{
      "source": "node ở chunk trước",
      "target": "node ở chunk sau",
      "type": "PART_OF | REQUIRES | USED_FOR | FORMULA_OF | CONDITION_FOR | SOLVES | RELATED_TO",
      "description": "quan hệ liên chunk",
      "semantic": "vì sao quan hệ này giúp nối mạch kiến thức",
      "evidence": "chứng cứ ngắn từ các chunk",
      "weight": 0.8,
      "source_chunk_ids": ["chunk_1", "chunk_2"]
    }}
  ]
}}

Quy tắc:
- Không tạo node trùng tên quá nhiều; dùng tên chuẩn ngắn.
- Không tự thêm kiến thức ngoài nội dung batch.
- cross_chunk_relationships chỉ dùng khi hai chunk thật sự có liên hệ kiến thức.
- JSON phải hợp lệ tuyệt đối.
"""

COMMUNITY_SUMMARY_PROMPT = """Bạn là trợ lý tóm tắt community trong GraphRAG cho sách Toán cấp 3.
Đây là community ở level {level} trong phân cụm phân tầng.

Entity trong community:
{entities}

Một số quan hệ nội bộ:
{relationships}

Hãy đặt title và summary cho community này. Summary cần nói được chủ đề toán học chính,
các node quan trọng, và vai trò của cụm trong việc trả lời câu hỏi.
Trả về JSON hợp lệ:
{{"title": "...", "summary": "..."}}
"""

QUERY_UNDERSTANDING_PROMPT = """Bạn là bộ phân tích câu hỏi cho hệ thống GraphRAG sách Toán cấp 3 tiếng Việt.
Hãy chuyển câu hỏi của người dùng thành JSON hợp lệ, không markdown.

Câu hỏi: {question}

Schema cần trả về:
{{
  "rewritten_query": "câu truy vấn ngắn, rõ nghĩa để tìm trong sách",
  "intent": "explain | solve | define | formula | compare | proof | page_lookup | multi_hop",
  "entities": ["khái niệm/công thức/dạng bài quan trọng"],
  "keywords": ["từ khóa tìm kiếm"],
  "query_variants": ["biến thể truy vấn 1", "biến thể truy vấn 2"],
  "sub_queries": [
    "truy vấn con 1 nếu câu hỏi có nhiều ý hoặc cần multi-hop",
    "truy vấn con 2"
  ],
  "answer_style": "cách trả lời phù hợp",
  "filters": {{"page_start": null, "page_end": null, "book_name": null}}
}}

Quy tắc:
- Query decomposition: nếu câu hỏi gồm nhiều ý, nhiều khái niệm, hoặc cần so sánh/giải thích theo bước, tách thành 2-5 sub_queries độc lập.
- Nếu câu hỏi đơn giản, sub_queries có thể gồm chính rewritten_query.
- Giữ thuật ngữ toán học tiếng Việt: đạo hàm, cực trị, tiệm cận, nguyên hàm, logarit, tích phân, số phức.
- Nếu câu hỏi có số trang, đưa vào filters.page_start/page_end.
- Không tự giải bài. Chỉ phân tích để retrieval tốt hơn.
"""

ANSWER_PROMPT = """Bạn là trợ lý học tập Toán cấp 3. Chỉ trả lời dựa trên context được cung cấp.
Nếu context không đủ, hãy nói rõ: "Dữ liệu trong sách chưa đủ để trả lời chắc chắn."

Câu hỏi: {question}

Context từ sách và knowledge graph:
{context}

Yêu cầu format đầu ra:

1. Không chào hỏi, không viết "Chào bạn", không nói lan man.
2. Không đoán lỗi chính tả dài dòng. Nếu cần hiểu lại câu hỏi, chỉ dùng cách hiểu đã chỉnh trong nội dung trả lời.
3. Không nhắc đến các nhãn nội bộ như: Chunk, Relevant chunks, Relevant entities, Graph paths, Community, score, context.
4. Không viết "(không rõ trang)" hoặc "không rõ trang".
5. Nếu có nguồn trang thì ghi ngắn gọn ở cuối câu: (trang 12) hoặc (trang 12-13).
6. Nếu không có metadata trang thì bỏ phần nguồn, không được ghi "không rõ trang".
7. Công thức toán viết dạng text dễ đọc trong terminal, không dùng ký hiệu $...$ hoặc $$...$$.
8. Không dùng LaTeX phức tạp như \\mathbb{{R}}, \\frac{{}}{{}}, \\int_{{a}}^{{b}} nếu không cần thiết.
9. Ưu tiên viết công thức dạng:
   - z = a + bi
   - i^2 = -1
   - a, b thuộc R
   - tích phân f(x) dx = F(x) + C
   - F'(x) = f(x)
10. Không bịa kiến thức ngoài context.
11. Nếu câu hỏi có nhiều ý, trình bày theo format sau:

[Tiêu đề ngắn]

1. Ý chính thứ nhất
Nội dung giải thích ngắn gọn.

2. Ý chính thứ hai
Nội dung giải thích ngắn gọn.

3. Công thức / ví dụ nếu có
Nội dung công thức hoặc ví dụ.

Kết luận:
Tóm tắt 1-2 câu dễ hiểu.
"""
