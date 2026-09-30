# MediCare AI Frontend

Frontend cho nền tảng tư vấn, điều hướng và điều phối khám bệnh thông minh. Sản phẩm phục vụ đồng thời bệnh nhân/người nhà và nhân viên tiếp đón/y tế.

MediCare AI được định hướng là một web responsive có khả năng cài đặt như PWA, sử dụng AI để hỗ trợ tư vấn không chẩn đoán, tìm khoa/phòng, hướng dẫn quy trình khám, đặt lịch và tra cứu thông tin theo quyền truy cập.

> Lưu ý: repository hiện mới ở giai đoạn scaffold. Các page nghiệp vụ, API backend thật, authentication hoàn chỉnh và AI orchestration sẽ được triển khai ở các bước tiếp theo.

## Công nghệ chính

- React 19 + TypeScript strict
- Vite
- Tailwind CSS 4
- Redux Toolkit + React Redux
- React Router
- RTK Query-ready cho server state và API cache
- Zod cho validation/schema
- Lucide React cho icon
- Vite PWA plugin
- ESLint + TypeScript ESLint

## Yêu cầu môi trường

- Node.js 20 trở lên
- npm 10 trở lên
- Backend API đang phát triển được cấu hình riêng khi bắt đầu tích hợp

Kiểm tra phiên bản:

```bash
node --version
npm --version
```

## Cài đặt và chạy local

```bash
npm install
npm run dev
```

Sau đó mở URL Vite hiển thị trong terminal, thường là `http://localhost:5173`.

Frontend gọi trực tiếp backend theo môi trường. CI/CD lấy URL từ secret
`API_DOMAIN_DEV` khi build branch `develop` và `API_DOMAIN_PROD` khi build branch
`main`.

Khi chạy local, có thể ghi đè bằng `VITE_API_BASE_URL` trong
`frontend/.env.local`. Nếu giá trị không có protocol, frontend mặc định thêm
`http://`.

## Các lệnh thường dùng

```bash
# Chạy development server
npm run dev

# Kiểm tra lint
npm run lint

# Kiểm tra TypeScript và build production
npm run build

# Chạy thử bản build production
npm run preview
```

## Cấu trúc hiện tại

```text
src/
├─ app/
│  └─ store.ts             # Redux store và layout state tối thiểu
├─ layouts/
│  ├─ RootLayout.tsx       # Header 2 tầng và shell chính
│  ├─ PatientLayout.tsx    # Shell khu bệnh nhân
│  ├─ StaffLayout.tsx      # Shell khu nhân viên
│  ├─ BrandMark.tsx        # Nhận diện MediCare AI
│  └─ ChatbotWidget.tsx    # Floating AI widget placeholder
├─ App.tsx                 # Router và placeholder routes
├─ main.tsx                # React entry point + Redux Provider
└─ index.css               # Tailwind và design tokens
```

Các thư mục `pages/`, `features/`, `services/`, `utils/`, `hooks/` và `types/` sẽ được bổ sung khi bắt đầu phát triển nghiệp vụ. Page phải có trách nhiệm ghép layout/feature/component, không chứa toàn bộ logic nghiệp vụ.

## Nhận diện giao diện

- Primary: `#0284c7`
- Navy/text đậm: `#0f172a`
- Background: `#f8fafc` và `#ffffff`
- Critical: `#dc2626`
- Warning: `#d97706`
- Online/safe: `#16a34a`
- AI: `#0891b2`
- Font: Plus Jakarta Sans, fallback Inter/sans-serif
- Bo góc: `8px` cho control, `12px–16px` cho card/modal
- Header: hai tầng
- Chatbot: floating widget tại `bottom-6 right-6`

## Tích hợp backend và AI

Backend dự kiến cung cấp API cho cả `patient` và `staff`, xác thực bằng JWT access/refresh token.

AI provider mặc định là OpenAI; Gemini là provider thay thế. Secret key chỉ được lưu ở backend hoặc secret manager, tuyệt đối không đưa vào frontend, `.env` public hoặc bundle production.

## Trạng thái kiểm tra scaffold

- `npm install`: đã chạy thành công
- `npm run lint`: đạt
- `npm run build`: đạt
- PWA manifest và service worker: đã cấu hình cơ bản

Xem [AGENT.md](./AGENT.md) để biết quy trình phát triển, quy chuẩn code và các lưu ý bắt buộc của dự án.
