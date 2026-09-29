import type { PatientProfileData } from './types';

/**
 * Simulates an API call to fetch patient profile data.
 * Replace with real endpoint: GET /api/patients/:id/profile
 */
export async function fetchPatientProfile(
  _patientId: string
): Promise<PatientProfileData> {
  // Simulate network latency
  await new Promise((resolve) => setTimeout(resolve, 600));

  return {
    patient: {
      id: 'p-001',
      code: 'BN-98041',
      fullName: 'Nguyễn Văn An',
      avatarUrl: '',
      gender: 'Nam',
      age: 42,
      dateOfBirth: '1982-03-14',
      bloodType: 'O+',
      insuranceId: 'BHYT BQ | 10 BVQNN',
      allergyNote: 'Dị ứng: Penicillin',
      status: 'active',
      activeDate: '2024-09-15',
    },
    infoBar: [
      {
        label: 'CCCD / Mã định danh Y tế',
        value: '001087008847',
      },
      {
        label: 'Số thẻ BHYT trong nước',
        value: 'DN 4 01 01 200 8241',
      },
      {
        label: 'Người liên hệ khẩn cấp',
        value: 'Lê Thị Mai (Vợ) • 0912 345 678',
      },
      {
        label: 'Bác sĩ da liễu/gia đình',
        value: 'BS.CKI Trần Minh Thảo',
      },
    ],
    vitalSigns: [
      {
        id: 'vs-1',
        icon: 'heart-pulse',
        label: 'Huyết áp',
        value: '125/82',
        unit: 'mmHg',
        status: 'normal',
        statusLabel: 'Bình thường',
        trend: 'stable',
        trendData: [120, 122, 125, 123, 125],
        referenceRange: 'Ổn định',
      },
      {
        id: 'vs-2',
        icon: 'activity',
        label: 'Nhịp tim',
        value: '76',
        unit: 'bpm',
        status: 'normal',
        statusLabel: 'Nghỉ ngơi',
        trend: 'stable',
        trendData: [74, 75, 76, 75, 76],
        referenceRange: 'Bình xương',
      },
      {
        id: 'vs-3',
        icon: 'scale',
        label: 'Chỉ số BMI',
        value: '22.4',
        unit: 'kg/m²',
        status: 'normal',
        statusLabel: 'Chuẩn',
        trend: 'stable',
        trendData: [22.1, 22.3, 22.4, 22.3, 22.4],
        referenceRange: 'Cân đối (18.5 - 24.9)',
      },
      {
        id: 'vs-4',
        icon: 'droplets',
        label: 'Đường huyết',
        value: '5.4',
        unit: 'mmol/L',
        status: 'normal',
        statusLabel: 'Bình thường',
        trend: 'stable',
        trendData: [5.2, 5.3, 5.4, 5.3, 5.4],
        referenceRange: 'Lúc đói',
      },
    ],
    medicalTabs: [
      { key: 'history', label: 'Lịch sử khám & Chẩn đoán' },
      { key: 'prescriptions', label: 'Đơn thuốc điện tử', count: 4 },
      { key: 'tests', label: 'Xét nghiệm & CĐHA' },
      { key: 'timeline', label: 'Lịch tiêm chủng' },
    ],
    timeline: [
      {
        id: 'tl-1',
        type: 'examination',
        badgeLabel: 'Khám cấp cứu',
        badgeColor: 'teal',
        title: 'Viêm phổi quản cấp tính (J20.9)',
        date: '15/09/2023',
        time: '09:15',
        hitlBadge: 'HITL: Bác sĩ kê số bệnh/chụng',
        doctorName: 'BS.CKI Trần Minh Thảo',
        doctorDepartment: 'Khoa Nội Hô hấp • Chứng chỉ hành nghề: CCH 100419 GP-1',
        findings: [
          {
            title: 'Tóm tắt tiền sử & Khuyến nghị điều trị:',
            description:
              'Bệnh nhân sốt nhẹ, tức vùng dưới sườn phải vùng thượng vị ở vùng thượng vị kéo dài. Tiền sử viêm loét dạ dày tá tràng và hội chứng ruột kích thích. Xét nghiệm công thức máu cho thấy bạch cầu tăng nhẹ, CRP tăng. CT bụng phát hiện áp-xe gan phải kích thước 4x5cm. Đã hội chẩn với BS ngoại khoa, quyết định điều trị nội khoa kháng sinh phối hợp. Thuốc giảm đau hạ sốt và theo dõi qua siêu âm liên tục trong 7 ngày.',
          },
        ],
        prescription: {
          id: 'rx-1',
          code: 'Rx-20230915-01',
          detail: '3 loại thuốc × 7 ngày',
        },
        prescriptionNote: 'Tái khám theo dõi chỉ số đáp ứng điều trị, kiểm tra hồ sơ',
        summary:
          'Nhận tin tư vấn với BS. Thảo | Đặt lịch khám hồ hấp',
      },
      {
        id: 'tl-2',
        type: 'health-check',
        badgeLabel: 'Khám định kỳ',
        badgeColor: 'blue',
        title: 'Khám sức khoẻ tổng quát doanh nghiệp định kỳ 2023',
        date: '22/06/2023',
        time: '08:00',
        doctorName: 'Hội đồng Khám sức khoẻ • Chủ tịch Hội đồng: BSCKI. Lê Hoàng Nam',
        doctorDepartment: 'Phòng khám Medcare AI Clinic',
        resultType: 'Kết luận: Sức khoẻ Loại I (Tốt)',
        testResults: [
          {
            id: 'tr-1',
            title: 'X-quang ngực thẳng (PA View)',
            description: 'Kết quả: Bình thường, lớn trường nhỏ hai phổi\nMã số kết quả: XQXQ001-27176.3',
            hasImageLink: true,
            imageLinkLabel: 'Xem phim X-quang HD & AI Phân tích',
          },
          {
            id: 'tr-2',
            title: 'Tổng phân tích tế bào máu & Sinh hoá 18 chỉ số',
            description:
              'Tất cả ở vùng giới hạn bình thường (chức năng gan/thận trong tiêu chuẩn)\nMã số kết quả: XNTH-17160',
            hasImageLink: true,
            imageLinkLabel: 'Xem bảng đối chiếu chỉ số',
          },
        ],
        recommendation:
          'Lời khuyên của bác sĩ: Tiếp tục duy trì chế độ dinh dưỡng lành mạnh và vận động, luyện tập thể dục 30 phút/ngày, hẹn khám định kỳ tiếp theo vào tháng 05/2024.',
        additionalLinks: [
          {
            label: 'Tải toàn bộ 4 hồ sơ khám các năm trước (2020 – 2023)',
            url: '#',
          },
        ],
      },
    ],
    emergencyContact: {
      fullName: 'Lê Thị Mai',
      relationship: 'Vợ',
      phone: '0912 345 678',
      healthIdCode: 'Bệnh nhân BN.0841',
      currentMedications: 'Dị ứng Penicillin (Phù mạch nhẹ)',
      address: 'Căn hộ 12-02, Toà The Sun, Cầu Giấy, Hà Nội',
    },
  };
}
