# Starter · PostgreSQL + pgvector

Pipeline mẫu có thể chạy benchmark với PostgreSQL + pgvector và embedding API tương thích OpenAI. Docker Compose dựng database cục bộ; `scripts/check_setup.py` kiểm tra kết nối và extension pgvector. Nếu thay backend, dùng Qdrant, Chroma hoặc vector store tương đương theo [GUIDE.md](../GUIDE.md) và cập nhật phần tích hợp tương ứng.

## Cấu trúc và vị trí dữ liệu

```text
starter/
├── docker-compose.yml       # PostgreSQL + pgvector, chỉ bind localhost
├── init.sql                 # bật extension khi khởi tạo volume mới
├── requirements.txt         # dependencies nền tảng
├── .env.example             # cấu hình mẫu; sao chép thành .env
├── scripts/check_setup.py   # kiểm tra DB và extension
├── src/                     # pipeline ingestion và benchmark
├── data/                    # chỗ tùy chọn cho dữ liệu riêng (hiện chỉ .gitkeep)
└── results/                 # trace, summary, tài nguyên và audit

../data/Tutorial_EDIT.pdf   # PDF corpus hiện tại ở root repo
../data/manifest.json       # nguồn, quyền, phạm vi và danh sách trang
../data/corpus.jsonl        # văn bản đã trích xuất để kiểm tra/truy vết
../benchmark/questions.jsonl # 20 câu hỏi: 15 dev / 5 test
```

Mặc định [`src/run.py`](src/run.py) tìm manifest và PDF trong `../data/`, benchmark trong `../benchmark/`, và ghi kết quả vào `starter/results/`. Có thể đổi đường dẫn bằng `MANIFEST_PATH`, `CORPUS_PDF`, `BENCHMARK_PATH` trong `.env`. Đường dẫn tương đối được hiểu theo thư mục làm việc hiện tại; hãy chạy lệnh từ `starter/`. Manifest mô tả Python Tutorial 3.7.0: 98 trang nội dung thuộc Chương 1–15, tính theo trang vật lý PDF; xem chi tiết và quy tắc loại trang trong [`../data/manifest.json`](../data/manifest.json). `starter/data/` hiện chưa chứa corpus.

## Yêu cầu

Docker Desktop hoặc Docker Engine + Compose, Python 3.11–3.14, và mạng để tải dependencies/container hoặc gọi dịch vụ embedding. `requirements.txt` cài psycopg, pypdf và python-dotenv; thư viện/SDK riêng cho model bạn chọn có thể cần cài bổ sung.

## 1. Dựng database và kiểm tra kết nối

Chạy các lệnh từ root repo:

```bash
cd starter
python3 -m venv .venv
```

Kích hoạt môi trường:

```bash
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Cài dependencies, tạo cấu hình local và khởi động database:

```bash
python -m pip install -r requirements.txt
# macOS/Linux
cp .env.example .env
# Windows PowerShell
Copy-Item .env.example .env
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Kết quả mong đợi: in tên database, phiên bản PostgreSQL và pgvector, sau đó `Setup OK`. Đây chỉ là **kiểm tra hạ tầng**, chưa gọi embedding API hay chạy benchmark. DB chỉ bind `127.0.0.1:55433`, với thông tin đăng nhập mẫu dành cho lab local. Nếu cổng bận, đổi port trong `docker-compose.yml` và host/port tương ứng trong `DATABASE_URL` của `.env`. `init.sql` chỉ chạy trên volume mới; không xóa volume nếu cần giữ dữ liệu.

Dừng container mà giữ dữ liệu:

```bash
docker compose -p day6_student_starter stop
```

## 2. Cấu hình embedding model

Adapter `src/embeddings.py` gọi endpoint embeddings tương thích OpenAI. Trong `.env`, đặt `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` và một trong `OPENAI_API_KEY` / `OPENROUTER_API_KEY`. Endpoint mặc định là `https://api.openai.com/v1`; với OpenRouter, đặt `EMBEDDING_BASE_URL=https://openrouter.ai/api/v1`. Chỉ cần URL gốc, adapter tự thêm `/embeddings`. Không commit `.env`. Dùng cùng model cho cả ba cấu hình; lần chạy mới gọi provider và có thể phát sinh chi phí. Ghi provider, model/phiên bản, số chiều và chi phí thực tế trong báo cáo.

## 3. Chạy benchmark

Chạy từ `starter/` sau khi đã khởi động database, cài dependencies và cấu hình embedding API:

```bash
python -m src.run
```

Runner mặc định dùng corpus PDF + manifest ở `../data/`, benchmark ở `../benchmark/`; có thể đặt lại các biến đường dẫn đã nêu ở trên. Lệnh xây ba cấu hình dùng cùng corpus/model/benchmark: A fixed-size, B theo đoạn, C như B nhưng bật metadata filter cho câu hỏi có filter. Runner gọi embedding API, chạy top-3 cho cả 20 câu và ghi bốn file vào `results/`: `traces.json`, `summary.json`, `resource_usage.json`, `manual_assessment_samples.json`. Các file này được ghi đè mỗi lần chạy. Kiểm tra `summary.json` và trace sau khi chạy; hoàn tất audit thủ công theo [`../GUIDE.md`](../GUIDE.md). Cách tính Hit@1/Evidence Hit@3 và yêu cầu benchmark nằm trong [`../BENCHMARK.md`](../BENCHMARK.md) và [`../SUBMISSION.md`](../SUBMISSION.md).

Nếu dùng dữ liệu riêng, đặt chúng trong `starter/data/` hoặc vị trí khác có thể truy cập được, rồi cập nhật manifest, biến đường dẫn và benchmark/gold evidence. Ghi nguồn, quyền sử dụng, ID trang/vị trí và quy tắc đếm; nếu không thể chia sẻ bản gốc, hướng dẫn người chấm truy cập/tái tạo và cung cấp minh chứng được phép chia sẻ.

## Kết quả hiện có

`results/` có trace, summary, resource usage và mẫu audit. Trước khi nộp, kiểm tra chúng khớp với lần chạy cuối; kèm cấu hình model, thời điểm chạy, chi phí, báo cáo cá nhân và experiment log. Không đưa API key, dữ liệu riêng tư hoặc dữ liệu không có quyền chia sẻ vào repo. Xem checklist [SUBMISSION.md](../SUBMISSION.md).
