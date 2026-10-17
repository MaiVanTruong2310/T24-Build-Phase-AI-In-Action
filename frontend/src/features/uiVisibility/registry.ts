// Danh mục thành phần giao diện người dùng có thể ẩn/hiện từ /staff/ui-editor.
// `locked: true` = thành phần an toàn/pháp lý, luôn hiển thị; phải khớp LOCKED_UI_KEYS ở
// src/api/endpoints/ui_visibility.py (tests/test_api/test_ui_visibility.py kiểm tra đồng bộ).

export type UiPageId =
  | 'global' | 'home' | 'consult' | 'doctors' | 'doctor_profile' | 'booking' | 'departments'
  | 'progress' | 'history' | 'appointment_detail' | 'profile' | 'requests' | 'auth';

export interface UiPage { id: UiPageId; label: string; path: string; note?: string }
export interface UiEntry { id: string; label: string; page: UiPageId; locked?: boolean; reason?: string }

export const UI_PAGES: UiPage[] = [
  { id: 'global', label: 'Header & thành phần chung', path: '/' },
  { id: 'home', label: 'Trang chủ', path: '/' },
  { id: 'consult', label: 'Tư vấn AI (khung chat)', path: '/patient' },
  { id: 'doctors', label: 'Tìm bác sĩ', path: '/patient/doctors' },
  { id: 'doctor_profile', label: 'Hồ sơ bác sĩ', path: '/patient/doctors', note: 'Bấm "Xem hồ sơ" một bác sĩ trong khung xem trước.' },
  { id: 'booking', label: 'Đặt lịch khám', path: '/patient/appointments' },
  { id: 'departments', label: 'Chuyên khoa', path: '/patient/departments' },
  { id: 'progress', label: 'Tiến trình điều trị', path: '/patient/progress', note: 'Cần dữ liệu bệnh nhân: tài khoản admin chỉ thấy bố cục.' },
  { id: 'history', label: 'Lịch sử lịch hẹn', path: '/patient/appointments/history', note: 'Cần dữ liệu bệnh nhân.' },
  { id: 'appointment_detail', label: 'Chi tiết lịch hẹn', path: '/patient/progress', note: 'Mở một lịch hẹn trong khung xem trước (cần dữ liệu bệnh nhân).' },
  { id: 'profile', label: 'Hồ sơ bệnh án', path: '/patient/profile', note: 'Cần dữ liệu bệnh nhân.' },
  { id: 'requests', label: 'Phiếu đăng ký điều phối', path: '/patient/requests' },
  { id: 'auth', label: 'Đăng nhập / Đăng ký', path: '/login' },
];

const SAFETY = 'Thành phần an toàn: luôn hiển thị.';

export const UI_REGISTRY = [
  // Header & chung
  { id: 'header.brand', label: 'Logo VCare+', page: 'global' },
  { id: 'header.nav.home', label: 'Menu: Trang chủ', page: 'global' },
  { id: 'header.nav.consult', label: 'Menu: Tư vấn AI', page: 'global' },
  { id: 'header.nav.doctors', label: 'Menu: Tìm bác sĩ', page: 'global' },
  { id: 'header.nav.booking', label: 'Menu: Đặt lịch', page: 'global' },
  { id: 'header.nav.progress', label: 'Menu: Tiến trình điều trị', page: 'global' },
  { id: 'header.sos', label: 'Nút Cấp cứu 115', page: 'global', locked: true, reason: SAFETY },
  { id: 'header.notifications', label: 'Chuông thông báo', page: 'global' },
  { id: 'header.simple_toggle', label: 'Nút Đơn giản / Mặc định', page: 'global' },
  { id: 'header.theme_toggle', label: 'Công tắc sáng / tối', page: 'global' },
  { id: 'header.login', label: 'Nút Đăng nhập', page: 'global' },
  { id: 'header.cta', label: 'Nút Tư vấn ngay / Đặt lịch khám', page: 'global' },
  { id: 'global.footer', label: 'Chân trang', page: 'global' },
  { id: 'global.zalo_button', label: 'Nút Zalo Bot', page: 'global' },
  { id: 'global.floating_chat', label: 'Bong bóng trợ lý (góc phải)', page: 'global' },

  // Trang chủ
  { id: 'landing.hero', label: 'Khối giới thiệu đầu trang', page: 'home' },
  { id: 'landing.hero_emergency', label: 'Dòng "Đau ngực, khó thở…? Gọi ngay 115"', page: 'home', locked: true, reason: SAFETY },
  { id: 'landing.story', label: 'Câu chuyện cuộn', page: 'home' },
  { id: 'landing.features', label: 'Tính năng', page: 'home' },
  { id: 'landing.doctors', label: 'Đội ngũ bác sĩ', page: 'home' },
  { id: 'landing.cta', label: 'Lời kêu gọi cuối trang', page: 'home' },

  // Tư vấn AI
  { id: 'consult.patient_selector', label: 'Chọn người khám', page: 'consult' },
  { id: 'consult.progress', label: 'Thanh tiến trình 4 bước', page: 'consult' },
  { id: 'consult.body_map', label: 'Hình cơ thể (cột trái)', page: 'consult' },
  { id: 'consult.body_map_button', label: 'Nút 📍 mở hình cơ thể', page: 'consult' },
  { id: 'consult.starter', label: 'Thẻ gợi ý "Bạn muốn bắt đầu từ đâu?"', page: 'consult' },
  { id: 'consult.quick_replies', label: 'Nút trả lời nhanh', page: 'consult' },
  { id: 'consult.schedule_grid', label: 'Lưới lịch trống 7 ngày', page: 'consult' },
  { id: 'consult.support_button', label: 'Nút Yêu cầu hỗ trợ', page: 'consult' },
  { id: 'consult.history_button', label: 'Nút Lịch sử', page: 'consult' },
  { id: 'consult.booking_button', label: 'Nút Phiếu khám', page: 'consult' },
  { id: 'consult.new_chat_button', label: 'Nút Cuộc mới', page: 'consult' },
  { id: 'consult.voice_button', label: 'Nút nhập giọng nói', page: 'consult' },
  { id: 'chat.emergency_banner', label: 'Huy hiệu mức ưu tiên / Cấp cứu (ATS)', page: 'consult', locked: true, reason: SAFETY },
  { id: 'chat.coordinator_status', label: 'Trạng thái bác sĩ điều phối', page: 'consult', locked: true, reason: SAFETY },
  { id: 'chat.disclaimer', label: 'Dòng "không chẩn đoán hay kê đơn, gọi 115"', page: 'consult', locked: true, reason: SAFETY },

  // Tìm bác sĩ / hồ sơ bác sĩ
  { id: 'doctors.heading', label: 'Tiêu đề trang', page: 'doctors' },
  { id: 'doctors.search', label: 'Thanh tìm kiếm', page: 'doctors' },
  { id: 'doctors.advanced', label: 'Nút Bộ lọc nâng cao', page: 'doctors' },
  { id: 'doctors.chips', label: 'Chọn nhanh chuyên khoa', page: 'doctors' },
  { id: 'doctor_profile.quick', label: 'Thông tin nhanh', page: 'doctor_profile' },
  { id: 'doctor_profile.booking', label: 'Khối Đặt lịch / Lịch khám', page: 'doctor_profile' },
  { id: 'doctor_profile.facilities', label: 'Nơi làm việc', page: 'doctor_profile' },
  { id: 'doctor_profile.about', label: 'Giới thiệu', page: 'doctor_profile' },
  { id: 'doctor_profile.details', label: 'Chuyên môn, kinh nghiệm, quá trình đào tạo', page: 'doctor_profile' },

  // Đặt lịch
  { id: 'booking.heading', label: 'Tiêu đề trang', page: 'booking' },
  { id: 'booking.mode_switch', label: 'Chuyển Khám bác sĩ / Gói khám', page: 'booking' },
  { id: 'booking.consent', label: 'Đồng ý chia sẻ thông tin', page: 'booking', locked: true, reason: 'Yêu cầu pháp lý: luôn hiển thị.' },

  // Trang khác
  { id: 'departments.heading', label: 'Tiêu đề trang', page: 'departments' },
  { id: 'departments.search', label: 'Bộ lọc tìm kiếm', page: 'departments' },
  { id: 'progress.heading', label: 'Tiêu đề trang', page: 'progress' },
  { id: 'progress.filters', label: 'Bộ lọc & nút Làm mới', page: 'progress' },
  { id: 'history.heading', label: 'Tiêu đề & nút Đặt lịch mới', page: 'history' },
  { id: 'appointment_detail.info', label: 'Thông tin lịch hẹn', page: 'appointment_detail' },
  { id: 'appointment_detail.instructions', label: 'Dặn dò trước khám', page: 'appointment_detail' },
  { id: 'appointment_detail.actions', label: 'Thao tác với lịch hẹn', page: 'appointment_detail' },
  { id: 'profile.family', label: 'Hồ sơ người thân', page: 'profile' },
  { id: 'profile.records', label: 'Hồ sơ khám & điều trị', page: 'profile' },
  { id: 'requests.heading', label: 'Tiêu đề trang', page: 'requests' },
  { id: 'auth.register_link', label: 'Dòng "Chưa có hồ sơ? Đăng ký ngay"', page: 'auth' },
  { id: 'auth.alt_login', label: 'Đăng nhập bằng CCCD / Google / Zalo', page: 'auth' },
  { id: 'auth.security_badge', label: 'Dòng bảo mật cuối form', page: 'auth' },
] as const satisfies readonly UiEntry[];

export type UiKey = (typeof UI_REGISTRY)[number]['id'];
export const UI_ENTRY = new Map<string, UiEntry>(UI_REGISTRY.map((entry) => [entry.id, entry]));
