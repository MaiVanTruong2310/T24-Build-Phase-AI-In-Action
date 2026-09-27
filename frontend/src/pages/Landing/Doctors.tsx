export function Doctors() {
  const doctors = [
    {
      name: 'ThS.BS Vũ Thu Trang',
      specialty: 'Trưởng Kíp Điều Phối Y Tế & Lâm Sàng',
      rating: '4.95',
      reviews: '240',
      exp: '14 năm kinh nghiệm tại Bệnh viện Đại học Y Dược. Chuyên sâu về cấp cứu nội khoa và điều phối chẩn đoán đa tầng.',
      img: 'https://i.pravatar.cc/300?img=1'
    },
    {
      name: 'BS. CKII Lê Hoàng Nam',
      specialty: 'Khoa Tim Mạch Can Thiệp',
      rating: '4.92',
      reviews: '184',
      exp: '18 năm kinh nghiệm chuyên sâu bệnh lý mạch vành, nhồi máu cơ tim, suy tim và can thiệp mạch máu lồng ngực.',
      img: 'https://i.pravatar.cc/300?img=11'
    },
    {
      name: 'BS. CKI Trần Minh Thảo',
      specialty: 'Nội Tổng Quát & Hô Hấp',
      rating: '4.88',
      reviews: '126',
      exp: '11 năm kinh nghiệm điều trị bệnh phổi tắc nghẽn, hen suyễn, viêm phế quản và các bệnh lý nhiễm trùng đường hô hấp.',
      img: 'https://i.pravatar.cc/300?img=5'
    }
  ]

  return (
    <div className="bg-slate-50 py-20 border-t border-slate-100">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
          <div>
            <div className="inline-block bg-sky-100 text-sky-800 text-xs font-bold px-3 py-1.5 rounded-full mb-4 uppercase tracking-wider">
              Đội Ngũ Bác Sĩ Chuyên Khoa
            </div>
            <h2 className="text-3xl font-bold text-slate-900 mb-2">Bác Sĩ Trực Ban Lâm Sàng Giám Sát</h2>
            <p className="text-slate-500 max-w-2xl">
              Các chuyên gia giàu kinh nghiệm đang trực tuyến để thẩm định và tiếp nhận bệnh nhân.
            </p>
          </div>
          <div className="flex items-center gap-2 text-emerald-700 font-semibold text-sm bg-emerald-50 px-4 py-2 rounded-full border border-emerald-100 shrink-0">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            12 Bác sĩ đang trực ban tiếp nhận
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {doctors.map((doc, i) => (
            <div key={i} className="bg-white rounded-3xl overflow-hidden shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 hover:-translate-y-1 transition-transform flex flex-col">
              <div className="relative h-56">
                <img src={doc.img} alt={doc.name} className="w-full h-full object-cover" />
                <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm text-sky-700 text-xs font-bold px-3 py-1.5 rounded-full flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 bg-sky-500 rounded-full animate-pulse"></div>
                  Đang trực ban tư vấn
                </div>
              </div>
              <div className="p-6 flex-1 flex flex-col">
                <div className="flex items-center gap-2 text-sm mb-3">
                  <span className="text-amber-400">★</span>
                  <span className="font-bold text-slate-900">{doc.rating}</span>
                  <span className="text-slate-500">({doc.reviews} đánh giá)</span>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-1">{doc.name}</h3>
                <p className="text-sm font-semibold text-sky-700 mb-4">{doc.specialty}</p>
                <p className="text-sm text-slate-500 leading-relaxed mb-6 flex-1">
                  {doc.exp}
                </p>
                <div className="grid grid-cols-2 gap-3 mt-auto">
                  <button className="bg-sky-700 hover:bg-sky-800 text-white font-semibold py-2.5 rounded-xl transition-colors text-sm">
                    Tư Vấn Ngay
                  </button>
                  <button className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-2.5 rounded-xl transition-colors text-sm">
                    Đặt Lịch
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
