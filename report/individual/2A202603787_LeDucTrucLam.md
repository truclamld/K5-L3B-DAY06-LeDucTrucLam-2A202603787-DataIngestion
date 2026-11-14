# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline

- Corpus là *Python Tutorial 3.7.0*, PDF `data/Tutorial_EDIT.pdf`, source ID `python-tutorial-3-7-0`. Manifest ghi 98 trang nội dung thuộc Chapters 1–15 trên tổng 155 trang vật lý; pipeline trích xuất đủ 98 trang không rỗng. Manifest ghi nguồn Python Software Foundation và giấy phép Python Software Foundation License Version 2. Phạm vi đếm loại mục lục, trang bìa, trang trắng, phần mở đầu, phụ lục ngoài phạm vi và các trang chỉ có đầu/chân trang.
- Pipeline trích xuất PDF, chuẩn hóa Unicode và khoảng trắng, giữ số trang vật lý, tạo chunk, embedding và truy xuất bằng PostgreSQL + pgvector. Giới hạn: chất lượng kết quả phụ thuộc text extraction của PDF; chunking thực hiện theo từng trang nên nội dung qua ranh giới trang không được nối.
- Embedding: OpenAI `text-embedding-3-small`, 1536 chiều. Vector store: PostgreSQL/pgvector, tìm kiếm cosine. Lệnh chạy từ thư mục gốc: `cd starter && python -m src.run` (cần cấu hình `starter/.env` và database). Lần chạy hiện tại ghi thời gian embedding tài liệu A = 6.989 s, B = 4.154 s, C = 0.000 s; C tái sử dụng vector của B trong cùng lần chạy. Đây không phải tổng thời gian ingest và benchmark.
- Metadata của chunk gồm `source`, `page`, `section`, `version`, `language`, `title` và thông tin chunk. Filter dùng `section` lấy từ manifest; giá trị filter được khai báo là ngữ cảnh truy vấn có trước khi tìm kiếm.

## Cấu hình và benchmark

- **A — fixed-size:** cửa sổ 1000 ký tự, overlap 150; 270 chunks.
- **B — paragraph-aware:** chia theo đoạn, tối đa 1200 ký tự; 218 chunks.
- **C — paragraph + filter:** cùng chunks và embedding như B; thêm filter `section` khi câu hỏi có điều kiện lọc; 218 chunks. C không lọc với câu hỏi không cung cấp filter.
- Benchmark có 20 câu, chia 15 dev / 5 test; có ba câu filter: q16, q17 (dev) và q20 (test). Cả 20 câu được chạy qua mỗi cấu hình, tạo 60 trace top-3. Gold được so khớp bằng source, trang và evidence quote đã chuẩn hóa khoảng trắng/Unicode. Một quote bị chia qua nhiều chunk có thể không khớp một chunk riêng lẻ; metric hiện không gộp bằng chứng từ nhiều chunk.
- Split dev/test đã được tạo trước thử nghiệm. Tuy nhiên, kết quả test đã được xem trước lần chạy metric đã sửa; lần sửa này đổi cách tính metric, không đổi cấu hình retrieval. Vì chưa có tiêu chí chọn cấu hình được ghi trước khi xem test, kết quả test được trình bày như kết quả quan sát của bộ nhỏ này, không phải holdout độc lập cho quyết định cuối.

## Kết quả truy xuất

Hit@1 được tính là 1 khi kết quả hạng 1 khớp gold source, page và evidence. Evidence Hit@3 được tính là 1 khi có ít nhất một kết quả trong top-3 khớp đủ ba thành phần đó. Summary đã được đối chiếu lại với các cờ trong trace; cả hai metric đều thống nhất.

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunks | Thời gian embedding |
|---|---:|---:|---:|---:|---:|
| A_fixed | dev | 2/15 (0.133) | 4/15 (0.267) | 270 | 6.989 s |
| A_fixed | test | 0/5 (0.000) | 3/5 (0.600) | 270 | 6.989 s |
| B_paragraph | dev | 2/15 (0.133) | 3/15 (0.200) | 218 | 4.154 s |
| B_paragraph | test | 2/5 (0.400) | 3/5 (0.600) | 218 | 4.154 s |
| C_paragraph_filter | dev | 2/15 (0.133) | 3/15 (0.200) | 218 | 0.000 s* |
| C_paragraph_filter | test | 3/5 (0.600) | 3/5 (0.600) | 218 | 0.000 s* |

`*` C dùng lại embedding của B trong cùng lần chạy, nên không tạo embedding tài liệu mới. Con số 0 giây không đại diện cho tổng thời gian hay chi phí vận hành C.

Trong ba câu có filter, C trả về top-3 với `section` khớp giá trị được yêu cầu ở cả 3/3 câu. Đây là kiểm tra tuân thủ filter trên các trace; chưa thay thế audit thủ công độ đúng/đủ của toàn bộ metadata. Các trace và summary nằm ở `starter/results/traces.json` và `starter/results/summary.json`; thống kê tài nguyên ở `starter/results/resource_usage.json`.

## Đánh giá thủ công có AI hỗ trợ

Các nhãn dưới đây được tạo với AI hỗ trợ bằng cách đọc câu hỏi, gold evidence và nội dung top-3 theo thang rubric trong GUIDE. Tác giả đã rà soát và chấp nhận các nhãn. Đây không phải đánh giá độc lập hoặc ground truth; phương pháp và vai trò hỗ trợ AI được công khai để người đọc diễn giải phù hợp.

- **Grounding:** chấm top-3 cho năm câu test mỗi cấu hình. Cả A/B/C có phân bố 0 điểm: 1 câu, 1 điểm: 0 câu, 2 điểm: 4 câu; trung bình **1.6/2**. q19 được 0 vì không có kết quả nào nêu mẫu `L=None`; bốn câu còn lại được 2 vì bằng chứng đủ nằm trong top-3. q15 và q20 được chấm theo nội dung có thể trả lời câu hỏi dù exact quote tự động không khớp ở một số hạng do lỗi/khác biệt trích xuất PDF.
- **Metadata:** đã đối chiếu `source`, `page`, `physical_page`, `section`, `version`, `title` và `language` trong 45 hit (5 câu test × top-3 × 3 cấu hình) với manifest/corpus. Kết quả audit: **45/45 đủ và đúng**. Với C, top-3 tuân thủ filter `section` ở **3/3 câu có filter**. Metadata giúp truy vết về trang/chương và lọc theo chương; hạn chế là các trường phản ánh một PDF/phiên bản đơn lẻ nên chưa kiểm tra khả năng phân biệt nhiều tài liệu hoặc phiên bản.
- **Chunk coherence:** chọn đoạn nội dung đầu tiên trên 10 trang nội dung đầu tiên trong manifest (trang vật lý 9, 10, 11, 12, 13, 15, 16, 17, 18, 19), rồi chấm chunk chứa đoạn đó cho mỗi cấu hình. Cả ba có điểm **18/10 = 1.8/2**: 8 vị trí đạt 2 và 2 vị trí đạt 1; không có vị trí 0. Hai điểm 1 là trang 10 và 19, nơi chunk bắt đầu giữa mạch ví dụ/văn bản và cần thêm ngữ cảnh. A/B/C có cùng điểm trên mẫu này; C dùng lại chunks B. Mẫu nhỏ và chỉ lấy đầu trang nên không đại diện toàn bộ corpus.
- Nhãn và lý do từng câu/hit được lưu trong `starter/results/manual_assessment_samples.json`; 30 nhãn coherence cùng vị trí cụ thể (trang PDF, offset trong text chuẩn hóa, excerpt mở đầu), chunk ID và lý do được lưu trong `starter/results/coherence_assessment.json`.

## Phân tích

- **A so với B:** B giảm số chunk từ 270 xuống 218 (52 chunk, khoảng 19.3%). Thời gian embedding tài liệu ghi nhận giảm từ 6.989 xuống 4.154 giây trong lần chạy này. Evidence Hit@3 test bằng nhau ở 3/5; Hit@1 test của B là 2/5, A là 0/5. Với chỉ năm câu test và việc đã xem test, không nên suy rộng chênh lệch này.
- **B so với C:** C giữ nguyên chunking và vector, chỉ áp dụng filter theo section khi được cung cấp. Trên test, Hit@1 là 3/5 ở C so với 2/5 ở B, còn Evidence Hit@3 đều là 3/5. Với q20, filter `chapter-11` đưa chunk evidence trang 101 lên hạng 1; ở B chunk này nằm hạng 2. Ba câu filter đều tuân thủ section yêu cầu. Mẫu này cho thấy filter có thể cải thiện thứ hạng khi phạm vi được biết trước, nhưng chưa đủ để kết luận hiệu quả tổng quát.
- **Ví dụ lỗi:** q01 hỏi kiểu kết quả của phép `/`; gold ở trang 16 không xuất hiện trong top-3 của cả ba chiến lược. q19 hỏi mẫu tham số mặc định `L=None`; gold ở trang 31 cũng không xuất hiện trong top-3. Đây là các lỗi retrieval rõ trong trace hiện tại.
- Chỉ số test hiện tại cho thấy B/C có Hit@1 cao hơn A, còn Evidence Hit@3 bằng nhau ở cả ba. Kết quả dev khác: A có Evidence Hit@3 4/15, B/C 3/15. Mẫu nhỏ, metric nghiêm ngặt theo quote và test đã được xem nên chưa đủ cơ sở chọn một chiến lược tối ưu ngoài corpus này.

## Giới hạn

- **Phạm vi đánh giá còn hẹp:** grounding chỉ có năm câu test cho mỗi cấu hình, coherence lấy mẫu 10 vị trí đầu corpus, còn kiểm tra filter chỉ có ba câu. Các câu hỏi cũng tập trung vào một tài liệu Python Tutorial 3.7.0. Vì vậy, kết quả hiện tại mô tả corpus và bộ câu hỏi này, chưa cho biết các cấu hình sẽ hoạt động ra sao với tài liệu, chủ đề hoặc phiên bản khác. Nếu mở rộng, nên xây dựng bộ câu hỏi lớn hơn, lấy mẫu ở nhiều chương và nhiều dạng nội dung, đồng thời bổ sung tài liệu/phiên bản khác và một tập test độc lập chưa dùng trong quá trình điều chỉnh.
- **Đánh giá có yếu tố chủ quan:** nhãn grounding và coherence được tạo với AI hỗ trợ rồi tác giả rà soát; cách chấm vẫn có thể chịu ảnh hưởng từ diễn giải của người đánh giá. Nên để ít nhất hai người chấm độc lập trên một phần hoặc toàn bộ mẫu, thống nhất rubric trước khi chấm, đo mức độ đồng thuận và phân xử các trường hợp bất đồng. Các kết quả nên tiếp tục được ghi rõ là đánh giá thủ công, không phải ground truth.
- **Chất lượng đầu vào và ranh giới chunk:** độ chính xác truy xuất phụ thuộc vào việc trích xuất văn bản từ PDF. Chunking theo từng trang giữ được số trang để truy vết nhưng có thể cắt rời câu, ví dụ hoặc bằng chứng nằm qua ranh giới trang; cách so khớp quote trên một chunk cũng có thể bỏ sót bằng chứng tương đương bị chia nhỏ. Có thể cải thiện bằng cách kiểm tra/chỉnh các trang trích xuất lỗi, thử chunking nối nội dung qua trang theo cấu trúc đoạn hoặc tiêu đề, và đánh giá thêm cách ghép bằng chứng từ nhiều chunk.
- **Metadata và filter mới được kiểm tra ở quy mô nhỏ:** audit 45 hit và ba truy vấn có filter cho thấy dữ liệu trong mẫu là đúng, nhưng chưa kiểm chứng toàn bộ corpus hoặc khả năng phân biệt nhiều nguồn và phiên bản. Khi mở rộng, nên tự động kiểm tra metadata trên toàn bộ chunk, thêm ca kiểm thử trùng tên chương/khác phiên bản, và xác nhận filter không loại nhầm bằng chứng phù hợp.
- **Benchmark chưa phản ánh đầy đủ chi phí vận hành:** thời gian được ghi nhận hiện chỉ là thời gian embedding tài liệu trong một lần chạy, không gồm trích xuất, chunking, lưu dữ liệu hay truy vấn. C dùng lại embedding của B nên số 0 giây không thể so sánh như một lần ingest độc lập. Cần đo riêng từng giai đoạn và truy vấn, chạy lặp lại trong điều kiện nhất quán, báo cáo độ trễ cùng tài nguyên/chi phí, đồng thời phân biệt rõ thời gian cache và thời gian chạy mới.
- **Khả năng tái lập thí nghiệm còn hạn chế:** các trace và summary đã lưu giúp kiểm tra kết quả, nhưng nhật ký `artifacts/experiment_log.csv` chưa ghi đầy đủ tham số, giả thuyết và kết quả A/B/C. Nếu làm lại, nên hoàn thiện nhật ký và lưu cùng lần chạy cấu hình, phiên bản dữ liệu/mã nguồn, câu hỏi, metric và môi trường để người khác có thể tái lập phép so sánh.

## Sử dụng AI

- **Công cụ đã sử dụng:** OpenAI Codex (model Luna 6 Medium)

- **Quá trình sử dụng:**
    - Giải thích về đề bài và các yêu cầu đề bài và nộp bài
    - Kiểm tra tài liệu, bao gồm quyền tái sử dụng và đề xuất cách phân chia dữ liệu trong tài liệu
    - Kiểm tra và chỉnh sửa 1 phần các câu hỏi benchmark
    - Hỗ trợ viết code pipeline trong `starter/src/`
    - Hỗ trợ đánh giá và chấm điểm các cấu hình benchmark; học viên có rà soát, kiểm tra và chỉnh sửa một phần cách trình bày, còn nội dung chấm được chấp nhận và không có sửa đổi thêm.
