import { Booking, Doctor, Facility, MedicalService, Specialty, PackageRequest } from '../appointment-booking/api';
import { AppointmentCatalog, AppointmentDisplayData, BookingType } from './types';

export interface LiveCoordinationCase {
  id: string;
  booking_id: string | null;
  status: string;
  created_at: string;
  patient?: {
    name?: string | null;
    phone?: string | null;
    doctor_name?: string | null;
    notes?: string | null;
    preferred_date?: string | null;
    preferred_period?: 'morning' | 'afternoon' | null;
    facility_preference?: string | null;
  };
  plan?: {
    doctor_id?: string | null;
    facility_id?: string | null;
    service_id?: string | null;
    specialty_id?: string | null;
    specialty_name?: string | null;
  };
  ai_snapshot?: {
    symptoms?: string | string[] | null;
    suggested_department_name?: string | null;
  };
}

export type BookingListItem = Booking & {
  coordinationCase?: LiveCoordinationCase;
  packageRequest?: PackageRequest;
  customBookingType?: BookingType;
};

export function toCatalogMap<T extends { id: string }>(items: T[]): Map<string, T> {
  return new Map(items.map((item) => [item.id, item]));
}

export function formatDateTimeVN(value?: string | null): string {
  if (!value) return 'Đang cập nhật';
  try {
    const d = new Date(value);
    return new Intl.DateTimeFormat('vi-VN', {
      weekday: 'long',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(d);
  } catch {
    return value || '';
  }
}

export function formatDateOnlyVN(value?: string | null): string {
  if (!value) return 'Đang cập nhật';
  try {
    const raw = value.includes('T') ? value : `${value}T08:00:00+07:00`;
    const d = new Date(raw);
    return new Intl.DateTimeFormat('vi-VN', {
      weekday: 'long',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(d);
  } catch {
    return value || '';
  }
}

export function getDisplayData(booking: BookingListItem, catalog: AppointmentCatalog): AppointmentDisplayData {
  const pr = booking.packageRequest;
  const coord = booking.coordinationCase;
  const targetService = catalog.services.get(booking.service_id);
  const isGroupService = booking.booking_mode === 'group' || targetService?.booking_mode === 'group';

  // 1. Gói khám sức khỏe (Health Package)
  if (pr || booking.booking_mode === 'package' || isGroupService) {
    const facility = catalog.facilities.get(booking.facility_id);
    const serviceName = pr?.service_name || targetService?.name || 'Gói khám sức khỏe toàn diện';
    const facilityName = pr?.facility_name || facility?.name || 'Trung tâm Y khoa VCare+';
    const price = pr?.service_price ?? (targetService?.price !== undefined ? Number(targetService.price) : null);
    const periodLabel = pr?.preferred_period === 'morning' ? 'Buổi sáng (07:30 - 11:30)' : pr?.preferred_period === 'afternoon' ? 'Buổi chiều (13:30 - 17:00)' : null;

    let stepIndex = 1;
    let stepLabel = 'Bước 2/4: Tư vấn chuẩn bị';
    let stepDesc = 'Điều phối viên đang chuẩn bị hồ sơ và sẽ gọi để chốt giờ khám & dặn dò trước xét nghiệm.';

    if (booking.status === 'confirmed') {
      stepIndex = 3;
      stepLabel = 'Bước 4/4: Sẵn sàng tiếp đón';
      stepDesc = 'Lịch khám đã được xác nhận. Vui lòng đến viện đúng ngày để làm thủ tục tiếp đón.';
    } else if (booking.status === 'cancelled') {
      stepIndex = 0;
      stepLabel = 'Đã hủy đăng ký';
      stepDesc = 'Đơn đăng ký gói khám đã bị hủy.';
    } else if (pr?.status === 'contacted') {
      stepIndex = 2;
      stepLabel = 'Bước 3/4: Đã tư vấn chuẩn bị';
      stepDesc = 'Đã hoàn tất dặn dò xét nghiệm. Hồ sơ chuyển sang cơ sở y tế.';
    }

    return {
      bookingType: 'package',
      typeBadge: {
        label: 'Gói khám sức khỏe',
        bg: 'bg-emerald-50 dark:bg-emerald-950/60',
        text: 'text-emerald-700 dark:text-emerald-300',
        border: 'border-emerald-200 dark:border-emerald-800',
        icon: '📦',
      },
      primaryTitle: serviceName,
      secondaryTitle: price ? `${price.toLocaleString('vi-VN')} đ · ${facilityName}` : facilityName,
      doctorName: 'Đội ngũ bác sĩ đa khoa & cận lâm sàng',
      doctorTitle: 'Đoàn khám định kỳ VCare+',
      doctorAvatar: null,
      specialtyName: 'Gói kiểm tra sức khỏe tổng quát',
      serviceName,
      servicePrice: price,
      facilityName,
      preferredPeriod: pr?.preferred_period || null,
      startsAtFormatted: `${formatDateOnlyVN(pr?.preferred_date || booking.starts_at)}${periodLabel ? ` (${periodLabel})` : ''}`,
      endsAtFormatted: null,
      notes: pr?.note || booking.reason || null,
      instructions: [
        {
          title: 'Nhịn ăn sáng & thức uống có đường',
          content: 'Nhịn ăn tối thiểu 6-8 tiếng trước giờ lấy mẫu máu. Bạn có thể uống một lượng nhỏ nước lọc khi thấy khát.',
          badge: 'Bắt buộc',
          icon: '🩸',
        },
        {
          title: 'Chuẩn bị siêu âm ổ bụng',
          content: 'Uống nhiều nước lọc và nhịn tiểu khoảng 45-60 phút trước khi siêu âm để hình ảnh quan sát bàng quang và nội tạng đạt độ sắc nét cao nhất.',
          badge: 'Lưu ý',
          icon: '💧',
        },
        {
          title: 'Hồ sơ & thuốc đang dùng',
          content: 'Mang theo CCCD/VssID, danh mục thuốc đang sử dụng tại nhà và các kết quả chụp chiếu gần nhất (nếu có).',
          icon: '📋',
        },
        {
          title: 'Trang phục thoải mái',
          content: 'Nên mặc áo tay ngắn hoặc trang phục rộng rãi thuận tiện cho việc đo điện tim, chụp X-quang và lấy máu xét nghiệm.',
          icon: '👕',
        },
      ],
      progress: {
        steps: ['Đăng ký gói', 'Tư vấn chuẩn bị', 'Chốt ngày khám', 'Tiếp đón tại viện'],
        currentStep: stepIndex,
        stepLabel,
        description: stepDesc,
      },
    };
  }

  // 2. Phân luồng điều phối AI (Coordination Case)
  if (coord) {
    const p = coord.patient || {};
    const ai = coord.ai_snapshot || {};
    const dept = ai.suggested_department_name || coord.plan?.specialty_name || 'Khám chuyên khoa định hướng AI';
    const facilityName = p.facility_preference || 'Bệnh viện ĐKQT Vinmec Riverside';
    const symptoms = p.notes || (Array.isArray(ai.symptoms) ? ai.symptoms.join(', ') : ai.symptoms) || null;

    let stepIndex = 1;
    let stepLabel = 'Bước 2/4: Thẩm định triệu chứng';
    let stepDesc = 'Bác sĩ và trợ lý y tế đang phân tích thông tin bệnh cảnh để chọn bác sĩ phù hợp.';

    if (booking.status === 'confirmed') {
      stepIndex = 3;
      stepLabel = 'Bước 4/4: Đã chốt bác sĩ & lịch hẹn';
      stepDesc = 'Lịch khám chính thức đã được xuất. Vui lòng đến viện đúng khung giờ.';
    } else if (booking.status === 'cancelled') {
      stepIndex = 0;
      stepLabel = 'Đã hủy yêu cầu';
      stepDesc = 'Yêu cầu phân luồng điều phối đã được hủy.';
    } else if (coord.status === 'contacting' || coord.status === 'waiting_patient') {
      stepIndex = 2;
      stepLabel = 'Bước 3/4: Đang liên hệ trao đổi';
      stepDesc = 'Điều phối viên đang liên hệ người bệnh để tư vấn chuyên khoa và thời gian khám.';
    }

    return {
      bookingType: 'coordination',
      typeBadge: {
        label: 'Tư vấn & Điều phối AI',
        bg: 'bg-indigo-50 dark:bg-indigo-950/60',
        text: 'text-indigo-700 dark:text-indigo-300',
        border: 'border-indigo-200 dark:border-indigo-800',
        icon: '🤖',
      },
      primaryTitle: `Phân luồng: ${dept}`,
      secondaryTitle: `Hồ sơ triệu chứng · ${p.name || 'Người bệnh'}`,
      doctorName: p.doctor_name || 'Điều phối viên y tế sắp xếp',
      doctorTitle: 'Trợ lý y tế / Điều phối viên',
      doctorAvatar: null,
      specialtyName: dept,
      serviceName: 'Tư vấn & Phân luồng triệu chứng AI',
      servicePrice: null,
      facilityName,
      preferredPeriod: p.preferred_period || null,
      startsAtFormatted: formatDateTimeVN(booking.starts_at),
      endsAtFormatted: null,
      notes: symptoms,
      instructions: [
        {
          title: 'Giữ liên lạc số điện thoại',
          content: 'Điều phối viên y tế sẽ gọi qua số điện thoại đăng ký trong vòng 15-30 phút làm việc để hoàn tất xếp lịch.',
          badge: 'Quan trọng',
          icon: '📞',
        },
        {
          title: 'Theo dõi diễn biến triệu chứng',
          content: 'Nếu có biểu hiện khẩn cấp (khó thở tăng dần, đau ngực dữ dội, co giật, lú lẫn), hãy gọi ngay cấp cứu 115 hoặc đến cơ sở cấp cứu gần nhất.',
          badge: 'Cảnh báo',
          icon: '⚠️',
        },
        {
          title: 'Chuẩn bị mô tả bệnh sử',
          content: 'Ghi nhớ thời điểm khởi phát triệu chứng, các loại thuốc hạ sốt/giảm đau đã dùng tại nhà để báo cho nhân viên điều phối.',
          icon: '💊',
        },
      ],
      progress: {
        steps: ['AI Tiếp nhận', 'Đánh giá triệu chứng', 'Điều phối tư vấn', 'Xuất lịch hẹn'],
        currentStep: stepIndex,
        stepLabel,
        description: stepDesc,
      },
    };
  }

  // 3. Khám Bác sĩ chuyên khoa (Doctor Visit)
  const doctor = catalog.doctors.get(booking.doctor_id);
  const facility = catalog.facilities.get(booking.facility_id);
  const service = catalog.services.get(booking.service_id);
  const specialty = catalog.specialties.get(booking.specialty_id);

  const docName = doctor?.full_name || (booking.doctor_id ? `Bác sĩ #${booking.doctor_id.slice(0, 8).toUpperCase()}` : 'Bác sĩ chuyên khoa');
  const specName = specialty?.name || 'Khám Chuyên khoa';
  const facName = facility?.name || (booking.facility_id ? `Cơ sở #${booking.facility_id.slice(0, 8).toUpperCase()}` : 'Trung tâm Y khoa VCare+');
  const servName = service?.name || 'Khám Chuyên khoa Bác sĩ';
  const price = service?.price !== undefined ? Number(service.price) : null;

  let stepIndex = 1;
  let stepLabel = 'Bước 2/4: Chờ bác sĩ xác nhận';
  let stepDesc = 'Lịch hẹn đang chờ bác sĩ và phòng khám duyệt khung giờ.';

  if (booking.status === 'confirmed') {
    stepIndex = 2;
    stepLabel = 'Bước 3/4: Đã xác nhận lịch';
    stepDesc = 'Lịch hẹn đã được xác nhận. Vui lòng có mặt tại cơ sở trước giờ hẹn.';
  } else if (booking.status === 'cancelled') {
    stepIndex = 0;
    stepLabel = 'Đã hủy lịch';
    stepDesc = 'Lịch hẹn đã được hủy theo yêu cầu.';
  }

  return {
    bookingType: 'doctor_visit',
    typeBadge: {
      label: 'Khám Bác sĩ chuyên khoa',
      bg: 'bg-sky-50 dark:bg-sky-950/60',
      text: 'text-sky-700 dark:text-sky-300',
      border: 'border-sky-200 dark:border-sky-800',
      icon: '🩺',
    },
    primaryTitle: docName,
    secondaryTitle: `${doctor?.title || 'Bác sĩ chuyên khoa'} · ${specName}`,
    doctorName: docName,
    doctorTitle: doctor?.title || '',
    doctorAvatar: doctor?.avatar_url || null,
    specialtyName: specName,
    serviceName: servName,
    servicePrice: price,
    facilityName: facName,
    preferredPeriod: null,
    startsAtFormatted: formatDateTimeVN(booking.starts_at),
    endsAtFormatted: booking.ends_at ? new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit' }).format(new Date(booking.ends_at)) : null,
    notes: booking.reason || booking.patient_note || null,
    instructions: [
      {
        title: 'Có mặt trước giờ hẹn 15 phút',
        content: 'Đến sớm để hoàn tất thủ tục đo sinh hiệu (mạch, huyết áp, nhiệt độ) và nhận số thứ tự vào phòng khám.',
        badge: 'Đúng giờ',
        icon: '⏰',
      },
      {
        title: 'Mang theo hồ sơ bệnh án cũ',
        content: 'Đem theo đơn thuốc đang dùng, sổ khám bệnh cũ hoặc kết quả chụp chiếu, xét nghiệm gần nhất để bác sĩ chẩn đoán chính xác hơn.',
        icon: '📁',
      },
      {
        title: 'CCCD & Thẻ BHYT',
        content: 'Mang theo căn cước công dân gắn chip hoặc tài khoản VNeID/VssID để đối chiếu thông tin hồ sơ y tế.',
        icon: '🪪',
      },
    ],
    progress: {
      steps: ['Đặt lịch hẹn', 'Bác sĩ duyệt', 'Sẵn sàng tiếp đón', 'Hoàn tất khám'],
      currentStep: stepIndex,
      stepLabel,
      description: stepDesc,
    },
  };
}
