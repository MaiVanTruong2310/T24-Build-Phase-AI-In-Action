import type { ConsultationData } from './types';

export const mockConsultationData: ConsultationData = {
  assessmentTitle: 'Hồ sơ Khám & Hội chẩn Bác sĩ Hôm nay',
  lastUpdated: 'Cập nhật lúc 10:15 AM bởi Hội đồng HITL MediCare',
  statusText: 'Tình trạng: Cần thăm khám sớm trong ngày',
  symptoms: {
    title: 'Triệu chứng ghi nhận qua AI Triage:',
    verifiedBadge: 'MedPaLM v3 Verified',
    description:
      'Đau tức ngực trái lan lên vai, ho khan 2 ngày, cảm giác khó thở khi đi lại. Huyết áp đo tại nhà: 135/85 mmHg.',
  },
  doctorReview: {
    doctorName: 'BS. Nguyễn Phương Linh',
    doctorTitle: 'Bác sĩ điều phối HITL',
    avatarUrl:
      'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=200',
    note:
      'Đã duyệt ưu tiên giữ chỗ khám Tim Mạch lúc 14:30. Bệnh nhân có thể mở hộp thoại chat nổi ở góc phải để tiếp tục trao đổi thêm với trợ lý AI hoặc đội ngũ y tế trực ban 24/7.',
  },
  matchedDoctors: [
    {
      id: 'doc-1',
      name: 'Lê Hoàng Nam',
      title: 'BS. CKII',
      specialty: 'Tim Mạch & Can Thiệp Lồng Ngực',
      rating: 4.9,
      reviewsCount: 184,
      avatarUrl:
        'https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&q=80&w=200',
      nextSlot: 'Slot hôm nay: 14:30 (Ưu tiên)',
      isPriority: true,
    },
    {
      id: 'doc-2',
      name: 'Trần Minh Thảo',
      title: 'ThS. BS',
      specialty: 'Nội Hô Hấp & Dị Ứng',
      rating: 4.8,
      reviewsCount: 126,
      avatarUrl:
        'https://images.unsplash.com/photo-1594824813524-c188b39a7b97?auto=format&fit=crop&q=80&w=200',
      nextSlot: 'Slot ngày mai: 08:30 & 10:00',
      isPriority: false,
    },
  ],
  proposedAppointment: {
    doctorName: 'BS. CKII Lê Hoàng Nam',
    doctorAvatarUrl:
      'https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&q=80&w=200',
    specialty: 'Khoa Tim Mạch Can Thiệp',
    timeSlot: '14:30 Hôm nay (25/10/2024)',
    location: 'P.302, MediCare Tân Bình',
    serviceType: 'Khám lâm sàng trực tiếp',
    fee: '450.000 đ',
    insuranceNote: '(Có BHYT)',
    priorityLabel: 'Ưu tiên cao',
  },
  vitals: [
    {
      id: 'bp',
      label: 'Huyết áp (BP)',
      value: '135/85',
      status: '↑ Tiền tăng HA',
      statusType: 'warning',
    },
    {
      id: 'hr',
      label: 'Nhịp tim (HR)',
      value: '88',
      unit: 'bpm',
      status: '✓ Xoang đều',
      statusType: 'normal',
    },
  ],
};
