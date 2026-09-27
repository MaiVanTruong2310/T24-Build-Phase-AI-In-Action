export function Testimonials() {
  const reviews = [
    {
      text: '"Tôi bị đau tức ngực lúc nửa đêm, khai báo qua app chỉ 1 phút là AI phát hiện dấu hiệu tim mạch nguy hiểm và bác sĩ trực ban gọi điện xử lý ngay. Tôi kịp thời can thiệp đặt stent đúng khung giờ vàng!"',
      name: 'Vũ Thành Long',
      desc: '54 tuổi, Hà Nội',
      img: 'https://i.pravatar.cc/150?img=11'
    },
    {
      text: '"Trước đây đi khám bệnh mất cả buổi sáng xếp hàng lấy số. Nay có MediCare AI, tôi chỉ cần trao đổi trước, đến bệnh viện là vào thẳng phòng bác sĩ Nam đúng giờ hẹn, toa thuốc gửi thẳng về điện thoại."',
      name: 'Phạm Thu Hương',
      desc: '38 tuổi, TP. Hồ Chí Minh',
      img: 'https://i.pravatar.cc/150?img=5'
    },
    {
      text: '"Gia đình tôi có con nhỏ hay bị sốt đêm. Tính năng tư vấn AI có bác sĩ trực ban duyệt khiến tôi hoàn toàn yên tâm, không bị hoang mang bởi các lời khuyên trôi nổi trên mạng."',
      name: 'Lê Minh Khoa',
      desc: '42 tuổi, Đà Nẵng',
      img: 'https://i.pravatar.cc/150?img=68'
    }
  ]

  return (
    <div className="bg-slate-50 py-20 border-t border-slate-100">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="inline-block bg-sky-100 text-sky-800 text-xs font-bold px-3 py-1.5 rounded-full mb-6 uppercase tracking-wider">
            Đánh Giá Thực Tế
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-4">Cảm Nhận Từ Bệnh Nhân Tin Dùng MediCare AI</h2>
          <p className="text-slate-500 max-w-2xl mx-auto">
            Sự an tâm và sức khỏe của bệnh nhân là thước đo quý giá nhất cho chất lượng y khoa của chúng tôi.
          </p>
        </div>
        
        <div className="grid md:grid-cols-3 gap-6">
          {reviews.map((r, i) => (
            <div key={i} className="bg-white rounded-3xl p-8 shadow-sm border border-slate-100 flex flex-col h-full hover:shadow-md transition-shadow">
              <div className="flex text-amber-400 text-lg mb-6">
                {'★★★★★'.split('').map((star, j) => <span key={j}>{star}</span>)}
              </div>
              <p className="text-sm text-slate-700 italic leading-relaxed mb-8 flex-1">
                {r.text}
              </p>
              <div className="flex items-center gap-3 mt-auto">
                <img src={r.img} alt={r.name} className="w-12 h-12 rounded-full border-2 border-slate-50" />
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">{r.name}</h4>
                  <p className="text-xs text-slate-500">{r.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
