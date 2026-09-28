import { History, Bot, User, UserCog } from 'lucide-react';

export function AuditTrail() {
  const events = [
    {
      time: "10:14:22",
      actor: "MediCare AI Agent",
      action: "Tiếp nhận triệu chứng đau tức ngực qua chat, khởi tạo hồ sơ và đề xuất chuyên khoa Tim mạch.",
      icon: <Bot size={14} className="text-sky-600" />,
      bg: "bg-sky-100"
    },
    {
      time: "10:16:05",
      actor: "Bệnh nhân Nguyễn Văn An",
      action: "Chọn khung giờ 14:15 ngày 24/10 với BS. Lê Hoàng Nam và gửi yêu cầu thẩm duyệt.",
      icon: <User size={14} className="text-emerald-600" />,
      bg: "bg-emerald-100"
    },
    {
      time: "10:17:00",
      actor: "Trực ban HITL Điều Phối",
      action: "Hồ sơ đã tự động đẩy vào danh sách chờ duyệt của BS. Nguyễn Phương Linh.",
      icon: <UserCog size={14} className="text-amber-600" />,
      bg: "bg-amber-100"
    }
  ];

  return (
    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-600">
          <History size={16} />
        </div>
        <h2 className="text-base font-bold text-slate-800">Nhật Ký Vết Hệ Thống (Audit Trail)</h2>
      </div>

      <div className="relative border-l border-slate-200 ml-4 space-y-6">
        {events.map((evt, idx) => (
          <div key={idx} className="relative pl-6">
            <div className={`absolute -left-3.5 top-0 w-7 h-7 rounded-full flex items-center justify-center ${evt.bg} border-4 border-slate-50`}>
              {evt.icon}
            </div>
            <div>
              <p className="text-xs font-bold text-slate-800 mb-1">
                {evt.time} • {evt.actor}
              </p>
              <p className="text-sm text-slate-600 leading-relaxed">
                {evt.action}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
