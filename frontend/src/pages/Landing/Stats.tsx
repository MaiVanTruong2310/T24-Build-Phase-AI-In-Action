export function Stats() {
  const stats = [
    { value: '99.8%', label: 'Độ nhạy sàng lọc lâm sàng AI', desc: 'Dựa trên mô hình MedPaLM & BioGPT' },
    { value: '< 90s', label: 'Phản hồi & Phê duyệt Bác sĩ', desc: 'Trực ban lâm sàng liên tục không gián đoạn' },
    { value: '120+', label: 'Bác sĩ chuyên khoa đầu ngành', desc: 'Từ BV Bạch Mai, Chợ Rẫy, ĐHYD' },
    { value: '50.000+', label: 'Bệnh nhân tin dùng', desc: 'Đánh giá trung bình 4.9/5 sao' }
  ]
  return (
    <div className="bg-white max-w-7xl mx-auto px-6 py-16">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:divide-x divide-slate-100">
        {stats.map((s, i) => (
          <div key={i} className="text-center px-4">
            <div className="text-4xl font-bold text-sky-700 mb-3">{s.value}</div>
            <div className="text-sm font-bold text-slate-900 mb-1.5">{s.label}</div>
            <div className="text-xs text-slate-500">{s.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
