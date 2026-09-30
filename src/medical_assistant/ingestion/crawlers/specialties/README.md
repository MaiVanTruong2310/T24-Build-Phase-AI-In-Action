# Trình thu thập dữ liệu chuyên khoa Vinmec

Pipeline này hoạt động độc lập với trình thu thập dữ liệu chuyên gia. Mã nguồn
nằm trong `src/data/crawlers_specialties/`; các file được tạo ra nằm trong
`src/data/output_specialties/`.

Chạy các lệnh dưới đây từ thư mục gốc của repository.

## 1. Tìm URL chuyên khoa tiếng Việt và tiếng Anh

```powershell
python -m src.data.crawlers_specialties.discover_specialty_urls
```

Đầu ra: `src/data/output_specialties/urls_crawl.txt`.

## 2. Thu thập dữ liệu của tất cả chuyên khoa đã tìm thấy

```powershell
python -m src.data.crawlers_specialties `
  --urls-file src/data/output_specialties/urls_crawl.txt
```

Mặc định crawler tự resume từ JSONL và append từng record ngay sau khi parse.
Các lệnh quản trị tương ứng:

```powershell
python -m src.data.crawlers_specialties --urls-file src/data/output_specialties/urls_crawl.txt --retry-failed
python -m src.data.crawlers_specialties --rebuild
python -m src.data.crawlers_specialties --urls-file src/data/output_specialties/urls_crawl.txt --fresh
```

Tiến độ nằm trong `checkpoints/`, lỗi được append ngay vào
`errors/failed_urls.jsonl`, còn JSON và `all.jsonl` được dựng lại từ JSONL ngôn
ngữ sau mỗi lần chạy.

Để chạy kiểm tra nhanh:

```powershell
python -m src.data.crawlers_specialties `
  --urls-file src/data/output_specialties/urls_crawl.txt `
  --max-specialties 1
```

## 3. Tạo các đoạn dữ liệu RAG

```powershell
python -m src.data.crawlers_specialties.build_rag_documents
```

Builder dùng mặc định 500 token/chunk và overlap 80 token trong cùng một block:

```powershell
python -m src.data.crawlers_specialties.build_rag_documents --chunk-size 500 --chunk-overlap 80
```

Cấu trúc thư mục đầu ra:

```text
src/data/output_specialties/
├── urls_crawl.txt
├── checkpoints/{vi_state.json,en_state.json,crawler.lock}
├── errors/failed_urls.jsonl
├── raw/
│   ├── vi/{listings,profiles}/
│   └── en/{listings,profiles}/
├── processed/
│   ├── json/
│   │   ├── vinmec_specialties_vi.json
│   │   ├── vinmec_specialties_en.json
│   │   ├── vinmec_specialties_all.json
│   │   └── crawl_summary.json
│   └── jsonl/
│       ├── vinmec_specialties_vi.jsonl
│       ├── vinmec_specialties_en.jsonl
│       └── vinmec_specialties_all.jsonl
└── rag/
    └── documents.jsonl
```

Mỗi bản ghi chuyên khoa chứa tên, ảnh bìa, nội dung tổng quan, dịch vụ, công
nghệ, URL của các chuyên gia liên quan, URL nguồn, ngôn ngữ và thời gian thu
thập dữ liệu.
