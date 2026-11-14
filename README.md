# Day 06 · Data Ingestion Engineering

Lab cá nhân về xây dựng pipeline ingestion và đánh giá truy xuất bằng vector search. Repo có corpus, manifest, benchmark và pipeline chạy được với PostgreSQL + pgvector cùng embedding API tương thích OpenAI.

## Dữ liệu và benchmark trong repo

- **PDF corpus:** [`data/Tutorial_EDIT.pdf`](data/Tutorial_EDIT.pdf), Python Tutorial 3.7.0.
- **Manifest:** [`data/manifest.json`](data/manifest.json) ghi nguồn, giấy phép, phiên bản, quy tắc đếm trang và danh sách trang nội dung. Phạm vi là Chương 1–15: **98 trang nội dung** (trên 155 trang PDF vật lý), 204.510 ký tự. Các trang bìa, mục lục, trang trống, trang phân cách chương và phụ lục ngoài phạm vi được loại trừ.
- **Corpus trích xuất:** [`data/corpus.jsonl`](data/corpus.jsonl); giữ ID nguồn, số trang và văn bản để kiểm tra/truy vết.
- **Benchmark:** [`benchmark/questions.jsonl`](benchmark/questions.jsonl), 20 câu hỏi, chia 15 dev / 5 test, có evidence và câu hỏi metadata filter. Không sửa test sau khi xem kết quả.
- [`data/format-example.json`](data/format-example.json) chỉ là ví dụ định dạng, không phải dữ liệu đánh giá.

Các đường dẫn lệnh bên dưới giả định chạy từ thư mục `starter/`. Mặc định pipeline đọc manifest, PDF và benchmark từ các thư mục gốc `../data/` và `../benchmark/`; kết quả được ghi vào `starter/results/`.

## Yêu cầu

- Python 3.11 trở lên (starter khai báo hỗ trợ 3.11–3.14), Docker Desktop/Engine + Compose.
- Một embedding model thật, API tương thích OpenAI hoặc model local; ghi rõ model và số chiều. Dùng cùng model cho cả ba cấu hình.
- Kết nối mạng khi cài thư viện/tải Docker image hoặc gọi embedding API.

## Setup starter PostgreSQL + pgvector

```bash
cd starter
python3 -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# macOS/Linux
cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

`check_setup.py` kiểm tra riêng kết nối PostgreSQL/pgvector; thông báo `Setup OK` không có nghĩa pipeline hay benchmark đã chạy. Compose ánh xạ DB về `127.0.0.1:55433`; cấu hình mặc định chỉ dành cho local lab. Nếu đổi cổng, cập nhật cả `docker-compose.yml` và `DATABASE_URL` trong `.env`. Không xóa Docker volume nếu cần giữ database.

## Chạy lại benchmark

Pipeline nằm trong `starter/src/`. Runner dùng PostgreSQL + pgvector và gọi embedding API tương thích OpenAI; cần có thông tin model và API key hợp lệ. Trong `starter/.env`, điền `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` và một trong `OPENAI_API_KEY` / `OPENROUTER_API_KEY`. Với OpenRouter hoặc endpoint tương thích khác, đặt `EMBEDDING_BASE_URL` thành URL gốc API (ví dụ `https://openrouter.ai/api/v1`); mặc định là `https://api.openai.com/v1`. Không commit `.env`.

Từ `starter/`:

```bash
python -m src.run
```

Lệnh chạy toàn bộ 20 câu hỏi trên ba cấu hình A (fixed-size), B (paragraph) và C (paragraph + metadata filter), tạo trace top-3 và ghi đè `starter/results/traces.json`, `summary.json`, `resource_usage.json` và `manual_assessment_samples.json`. Nó gọi embedding API và có thể phát sinh chi phí; thời gian chạy phụ thuộc provider. Mỗi lần chạy sẽ nạp lại các chunk theo strategy vào database. Đọc [`GUIDE.md`](GUIDE.md) để biết định nghĩa chỉ số và cách hoàn tất đánh giá thủ công.

Nếu thay dữ liệu, cập nhật manifest và gold evidence/benchmark tương ứng. Với nguồn không thể đưa vào repo, ghi URL/quyền truy cập và hướng dẫn tái tạo; đảm bảo người chấm có cách xác minh. Manifest phải nêu số trang hợp lệ và quy tắc tính, không chỉ dựa vào số trang vật lý.

## Đường dẫn bài nộp và tài liệu

- Mã pipeline mẫu: [`starter/src/`](starter/src/)
- Manifest / corpus: [`data/manifest.json`](data/manifest.json), [`data/corpus.jsonl`](data/corpus.jsonl), [`data/Tutorial_EDIT.pdf`](data/Tutorial_EDIT.pdf)
- Benchmark và log thí nghiệm: [`benchmark/questions.jsonl`](benchmark/questions.jsonl), [`artifacts/experiment_log.csv`](artifacts/experiment_log.csv)
- Trace/kết quả/audit mẫu: [`starter/results/`](starter/results/)
- Báo cáo cá nhân: [`report/individual/2A202603787_LeDucTrucLam.md`](report/individual/2A202603787_LeDucTrucLam.md)
- Hướng dẫn chi tiết: [`GUIDE.md`](GUIDE.md), [`BENCHMARK.md`](BENCHMARK.md), [`SUBMISSION.md`](SUBMISSION.md), [`RUBRIC.md`](RUBRIC.md), [`RULES.md`](RULES.md)

Trước khi nộp, kiểm tra các trace/kết quả khớp với lần chạy cuối, điền [`STUDENT.md`](STUDENT.md), ghi model/phiên bản/chi phí/thời điểm chạy và bảo đảm repo không chứa secret hay dữ liệu không được phép chia sẻ. Xem checklist đầy đủ trong [`SUBMISSION.md`](SUBMISSION.md).
