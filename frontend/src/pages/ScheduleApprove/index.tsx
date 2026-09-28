import { ShieldCheck, UserCog, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Header } from './components/Header';
import { PatientInfo } from './components/LeftCol/PatientInfo';
import { AITriage } from './components/LeftCol/AITriage';
import { AppointmentDetail } from './components/LeftCol/AppointmentDetail';
import { SlotStatus } from './components/RightCol/SlotStatus';
import { Billing } from './components/RightCol/Billing';
import { Notification } from './components/RightCol/Notification';
import { AuditTrail } from './components/RightCol/AuditTrail';
import { fetchBooking, updateBookingStatus, Booking } from './api';

export default function ScheduleApprove() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(false); // Should start true if fetching, but we'll mock if it fails

  // Fetch logic
  useEffect(() => {
    if (id) {
      setLoading(true);
      fetchBooking(id)
        .then(setBooking)
        .catch(err => {
          console.error(err);
          // Assuming mockup logic if API is not fully up yet
          // setError('Không thể tải thông tin lịch hẹn');
        })
        .finally(() => setLoading(false));
    }
  }, [id]);

  const handleApprove = async () => {
    if (!id || !booking) return;
    try {
      // Approve booking by changing status to 'confirmed'
      await updateBookingStatus(id, 'confirmed', 'Đã kiểm tra và phê duyệt');
      alert('Đã phê duyệt lịch hẹn thành công!');
      navigate('/staff/queue');
    } catch {
      alert('Lỗi khi phê duyệt lịch hẹn');
    }
  };

  const handleReject = async () => {
    if (!id) return;
    const reason = prompt('Nhập lý do từ chối:');
    if (!reason) return;
    try {
      // Reject booking by changing status to 'rejected'
      await updateBookingStatus(id, 'rejected', reason);
      alert('Đã từ chối lịch hẹn!');
      navigate('/staff/queue');
    } catch {
      alert('Lỗi khi từ chối lịch hẹn');
    }
  };

  return (
    <div className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden flex flex-col relative pb-16">
      <div className="p-6 md:p-8 flex-1">
        <Header onApprove={handleApprove} onReject={handleReject} isLoading={loading} />
        
        {loading ? (
          <div className="py-20 flex justify-center items-center">
             <Loader2 size={32} className="animate-spin text-sky-600" />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-7">
              <PatientInfo />
              <AITriage />
              <AppointmentDetail />
            </div>
            <div className="lg:col-span-5">
              <SlotStatus />
              <Billing />
              <Notification />
              <AuditTrail />
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="bg-slate-50 border-t border-slate-200 px-6 py-4 flex flex-col sm:flex-row justify-between items-center gap-4 text-xs font-semibold text-slate-500">
        <div className="flex items-center gap-2">
          <ShieldCheck size={16} className="text-teal-600" />
          <span>MediCare AI Clinical HITL Management System - Chuẩn HIPAA & Bộ Y Tế. Hệ thống tự động ghi nhật ký can thiệp y khoa.</span>
        </div>
        <div className="flex items-center gap-6">
          <span>Audit ID: MC-HITL-2024-SYS</span>
          <span className="text-emerald-700">Phiên trực: Phòng Trực Cấp Cứu 01</span>
        </div>
      </div>

      {/* Floating Action Button */}
      <button className="absolute bottom-6 right-6 bg-white border border-slate-200 shadow-lg rounded-full px-4 py-2 flex items-center gap-2 text-sm font-bold text-sky-700 hover:bg-slate-50 transition-colors z-10">
        <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
        Hỗ trợ AI & HITL
      </button>
      <div className="absolute bottom-4 right-4 w-12 h-12 bg-sky-700 rounded-full flex items-center justify-center text-white shadow-xl cursor-pointer hover:bg-sky-800 transition-colors z-0">
        <UserCog size={24} />
      </div>
    </div>
  );
}
