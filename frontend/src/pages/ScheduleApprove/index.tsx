import { useEffect, useState, type ReactNode } from 'react';
import { ArrowLeft, Building2, CalendarDays, CheckCircle2, Clock3, Loader2, MapPin, UserRound, XCircle } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchBooking, updateBookingReview, type Booking } from './api';

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function statusLabel(status: Booking['status']): string {
  if (status === 'pending_approval') return 'Chờ duyệt';
  if (status === 'confirmed') return 'Đã duyệt';
  if (status === 'expired') return 'Đã hết hạn';
  return 'Đã từ chối';
}

export default function ScheduleApprove() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<'confirmed' | 'rejected' | null>(null);
  const [error, setError] = useState('');
  const [staffNote, setStaffNote] = useState('');

  useEffect(() => {
    if (!id) {
      setError('Mã lịch hẹn không hợp lệ.');
      setLoading(false);
      return;
    }

    fetchBooking(id)
      .then(setBooking)
      .catch((cause: unknown) => {
        setError(cause instanceof Error ? cause.message : 'Không thể tải thông tin lịch hẹn.');
      })
      .finally(() => setLoading(false));
  }, [id]);

  const handleReview = async (nextStatus: 'confirmed' | 'rejected') => {
    if (!id || !booking || booking.status !== 'pending_approval' || action) return;
    const note = staffNote.trim();
    if (nextStatus === 'rejected' && !note) {
      setError('Vui lòng nhập lý do từ chối lịch hẹn.');
      return;
    }

    setError('');
    setAction(nextStatus);
    try {
      await updateBookingReview(id, nextStatus, note || undefined);
      navigate('/staff/appointments');
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Không thể cập nhật trạng thái lịch hẹn.');
      setAction(null);
    }
  };

  if (loading) {
    return <LoadingState />;
  }

  if (!booking) {
    return (
      <section className="mx-auto max-w-3xl rounded-2xl border border-red-200 bg-red-50 p-8">
        <h1 className="text-xl font-bold text-red-900">Không thể tải lịch hẹn</h1>
        <p className="mt-2 text-sm text-red-700">{error}</p>
        <button onClick={() => navigate('/staff/appointments')} className="mt-5 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white">
          Quay lại hàng đợi
        </button>
      </section>
    );
  }

  const isPending = booking.status === 'pending_approval';

  return (
    <section className="mx-auto max-w-7xl space-y-6 p-6">
      <button onClick={() => navigate('/staff/appointments')} className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-sky-700">
        <ArrowLeft className="h-4 w-4" /> Quay lại hàng đợi duyệt lịch
      </button>

      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:flex-row sm:items-start">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-sky-600">Thẩm định booking</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">{booking.booking_code}</h1>
          <p className="mt-2 text-sm text-slate-500">Yêu cầu tạo lúc {formatDateTime(booking.created_at)}</p>
        </div>
        <span className={booking.status === 'confirmed'
          ? 'rounded-full bg-emerald-100 px-4 py-2 text-sm font-bold text-emerald-700'
          : booking.status === 'rejected'
            ? 'rounded-full bg-rose-100 px-4 py-2 text-sm font-bold text-rose-700'
            : booking.status === 'expired'
              ? 'rounded-full bg-orange-100 px-4 py-2 text-sm font-bold text-orange-700'
              : 'rounded-full bg-amber-100 px-4 py-2 text-sm font-bold text-amber-700'}>
          {statusLabel(booking.status)}
        </span>
      </div>

      {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-6">
          <Panel title="Thông tin bệnh nhân" icon={<UserRound className="h-5 w-5" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Info label="Họ tên" value={booking.patient_name} />
              <Info label="Tuổi" value={booking.patient_age ? `${booking.patient_age} tuổi` : 'Chưa cập nhật'} />
              <Info label="Giới tính" value={booking.patient_gender || 'Chưa cập nhật'} />
              <Info label="Số điện thoại" value={booking.patient_phone || 'Chưa cập nhật'} />
              <Info label="CCCD" value={booking.patient_cccd || 'Chưa cập nhật'} />
              <Info label="Mã BHYT" value={booking.patient_bhyt || 'Chưa cập nhật'} />
            </div>
          </Panel>

          <Panel title="Chi tiết lịch hẹn" icon={<CalendarDays className="h-5 w-5" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Info label="Bác sĩ" value={`${booking.doctor_title ? `${booking.doctor_title} ` : ''}${booking.doctor_name}`} />
              <Info label="Chuyên khoa" value={booking.specialty_name} />
              <Info label="Dịch vụ" value={booking.service_name} />
              <Info label="Hình thức" value={booking.encounter_type === 'in_person' ? 'Khám trực tiếp' : 'Telehealth'} />
              <Info label="Thời gian bắt đầu" value={formatDateTime(booking.starts_at)} />
              <Info label="Thời gian kết thúc" value={formatDateTime(booking.ends_at)} />
            </div>
            <div className="mt-5 rounded-xl bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-800"><Building2 className="h-4 w-4 text-sky-600" /> Cơ sở khám</div>
              <p className="mt-2 font-semibold text-slate-900">{booking.facility_name}</p>
              {booking.facility_address && <p className="mt-1 flex items-center gap-1 text-sm text-slate-600"><MapPin className="h-4 w-4" /> {booking.facility_address}</p>}
              {booking.room && <p className="mt-1 text-sm text-slate-600">{booking.room}</p>}
            </div>
          </Panel>

          <Panel title="Lý do và ghi chú của bệnh nhân" icon={<Clock3 className="h-5 w-5" />}>
            <p className="text-sm leading-6 text-slate-800">{booking.reason}</p>
            {booking.patient_note && <p className="mt-4 border-l-2 border-sky-300 pl-3 text-sm italic text-slate-600">{booking.patient_note}</p>}
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="Quyết định nghiệp vụ" icon={<CheckCircle2 className="h-5 w-5" />}>
            {isPending ? (
              <>
                <p className="text-sm leading-6 text-slate-600">Kiểm tra thông tin bệnh nhân, dịch vụ và khung giờ trước khi ghi nhận quyết định.</p>
                <textarea
                  value={staffNote}
                  onChange={(event) => setStaffNote(event.target.value)}
                  maxLength={2000}
                  rows={4}
                  placeholder="Ghi chú duyệt hoặc lý do từ chối"
                  className="mt-4 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
                />
                <div className="mt-5 space-y-3">
                  <button onClick={() => handleReview('confirmed')} disabled={Boolean(action)} className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 font-bold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50">
                    {action === 'confirmed' ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Duyệt lịch hẹn
                  </button>
                  <button onClick={() => handleReview('rejected')} disabled={Boolean(action)} className="flex w-full items-center justify-center gap-2 rounded-xl border border-rose-200 px-4 py-3 font-bold text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50">
                    {action === 'rejected' ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />} Từ chối lịch hẹn
                  </button>
                </div>
              </>
            ) : (
              <div className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">Booking này đã được xử lý, không thể thay đổi quyết định.</div>
            )}
          </Panel>

          <Panel title="Trạng thái đồng bộ" icon={<Clock3 className="h-5 w-5" />}>
            <div className="space-y-3 text-sm">
              <Info label="Trạng thái" value={statusLabel(booking.status)} />
              <Info label="Ghi chú staff" value={booking.staff_note || 'Chưa có'} />
              <p className="text-xs leading-5 text-slate-500">Thông báo bệnh nhân và các bước thanh toán sẽ được nối vào workflow riêng sau khi API notification/billing sẵn sàng.</p>
            </div>
          </Panel>
        </div>
      </div>
    </section>
  );
}

function Panel({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-5 flex items-center gap-2 text-base font-bold text-slate-900">{icon} {title}</h2>
      {children}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p><p className="mt-1 break-words text-sm font-medium text-slate-800">{value}</p></div>;
}

function LoadingState() {
  return <div className="flex min-h-[420px] items-center justify-center text-sky-700"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Đang tải thông tin lịch hẹn...</div>;
}
