import { CalendarCheck2, Check } from 'lucide-react';

export function BookingHeader() {
  const steps = ['Chuyên khoa', 'Cơ sở khám', 'Bác sĩ', 'Ngày & khung giờ', 'Xác nhận'];

  return (
    <header className="mb-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1.5 text-xs font-bold text-sky-700">
            <CalendarCheck2 className="h-4 w-4" /> Đặt lịch khám trực tuyến
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Đặt lịch khám</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Chọn đúng chuyên khoa, dịch vụ, cơ sở và khung giờ đang còn chỗ. Thông tin hiển thị được lấy từ danh mục và lịch làm việc hiện tại.
          </p>
        </div>
        <p className="max-w-xs text-sm leading-6 text-slate-500 lg:text-right">
          Bạn có thể xem hoặc hủy lịch đã đặt trong mục lịch hẹn của mình.
        </p>
      </div>

      <ol className="mt-8 grid gap-3 sm:grid-cols-5">
        {steps.map((step, index) => (
          <li key={step} className="flex items-center gap-3 rounded-xl bg-slate-50 px-3 py-3 text-sm">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-600 text-xs font-bold text-white">
              {index === 0 ? <Check className="h-4 w-4" /> : index + 1}
            </span>
            <span className="font-semibold text-slate-700">{step}</span>
          </li>
        ))}
      </ol>
    </header>
  );
}
