# Trình thu thập dữ liệu chuyên gia Vinmec

Trình thu thập dữ liệu tìm kiếm và phân tích các hồ sơ chuyên gia công khai từ hai trang:

- Tiếng Việt: `https://www.vinmec.com/vie/chuyen-gia-y-te/`
- Tiếng Anh: `https://www.vinmec.com/eng/professionals/`

Trước khi thu thập, chương trình kiểm tra `robots.txt`, mặc định chờ hai giây
giữa các yêu cầu và thử lại khi gặp lỗi tạm thời. Mỗi record thành công được
append và `fsync` ngay vào JSONL ngôn ngữ; mỗi lỗi được ghi ngay vào
`errors/failed_urls.jsonl`.

## Bước 1: Tìm tất cả URL hồ sơ

Chạy lệnh sau từ thư mục gốc của repository:

```powershell
.venv\Scripts\python.exe -m src.data.crawlers_doctors.discover_vinmec_urls
```

Mỗi dòng trong `src/data/output_doctors/urls_crawl.txt` sẽ chứa một URL hồ sơ.
Khi chạy lại, lệnh sẽ thay thế file hiện tại bằng danh sách mới đã được sắp xếp
và loại bỏ URL trùng lặp.

## Bước 2: Thu thập dữ liệu từ các URL đã tìm thấy

```powershell
.venv\Scripts\python.exe -m src.data.crawlers_doctors --urls-file src/data/output_doctors/urls_crawl.txt
```

Lệnh trên tự resume: URL đã có trong JSONL sẽ được bỏ qua. Các chế độ quản trị:

```powershell
# Thử lại riêng các URL từng lỗi, vẫn giữ dữ liệu thành công
.venv\Scripts\python.exe -m src.data.crawlers_doctors --urls-file src/data/output_doctors/urls_crawl.txt --retry-failed

# Chỉ kiểm tra JSONL và sinh lại JSON/all.jsonl, không gọi mạng
.venv\Scripts\python.exe -m src.data.crawlers_doctors --rebuild

# Lưu bản dữ liệu hiện có vào thư mục backup rồi crawl mới hoàn toàn
.venv\Scripts\python.exe -m src.data.crawlers_doctors --urls-file src/data/output_doctors/urls_crawl.txt --fresh
```

`checkpoints/crawler.lock` ngăn hai tiến trình ghi đồng thời;
`checkpoints/{vi,en}_state.json` lưu tiến độ quan sát được. JSON và
`vinmec_professionals_all.jsonl` là dữ liệu dẫn xuất từ hai JSONL ngôn ngữ.

Nếu bỏ qua `--urls-file`, trình thu thập vẫn có thể tự tìm URL và thu thập dữ
liệu trong cùng một lệnh.

## Bước 3: Tạo tài liệu RAG

File JSONL đã chuẩn hóa là nguồn dữ liệu chính. Dùng lệnh sau để tạo các đoạn
Markdown theo từng mục và lưu dưới dạng JSONL kèm metadata:

```powershell
.venv\Scripts\python.exe -m src.data.crawlers_doctors.build_rag_documents
```

Đầu vào mặc định là `processed/jsonl/vinmec_professionals_all.jsonl` và đầu ra
mặc định là `rag/documents.jsonl`. Có thể điều chỉnh kích thước đoạn khi cần:

```powershell
.venv\Scripts\python.exe -m src.data.crawlers_doctors.build_rag_documents --chunk-size 500 --chunk-overlap 80
```

Chạy kiểm tra nhanh (một trang danh sách và một hồ sơ cho mỗi ngôn ngữ):

```powershell
.venv\Scripts\python.exe -m src.data.crawlers_doctors --max-pages 1 --max-profiles 1
```

Các tùy chọn hữu ích:

```text
--language {vi,en,both}
--delay SECONDS
--max-pages NUMBER
--max-profiles NUMBER
--output-dir PATH
--urls-file PATH
--no-raw
--resume
--retry-failed
--rebuild
--fresh
```

Cấu trúc thư mục đầu ra:

```text
src/data/output_doctors/
├── urls_crawl.txt
├── checkpoints/{vi_state.json,en_state.json,crawler.lock}
├── errors/failed_urls.jsonl
├── raw/
│   ├── vi/{listings,profiles}/
│   └── en/{listings,profiles}/
├── processed/
│   ├── json/
│   │   ├── vinmec_professionals_vi.json
│   │   ├── vinmec_professionals_en.json
│   │   ├── vinmec_professionals_all.json
│   │   └── crawl_summary.json
│   └── jsonl/
│       ├── vinmec_professionals_vi.jsonl
│       ├── vinmec_professionals_en.jsonl
│       └── vinmec_professionals_all.jsonl
└── rag/
    └── documents.jsonl
```

Dữ liệu đã xử lý sử dụng định dạng JSON vì các trường trong hồ sơ có cấu trúc,
thuận tiện cho việc nhập vào cơ sở dữ liệu hoặc chuyển đổi sang Markdown sau
này. HTML thô được giữ lại theo mặc định để có thể kiểm tra quá trình phân tích
mà không cần tải lại các trang.
