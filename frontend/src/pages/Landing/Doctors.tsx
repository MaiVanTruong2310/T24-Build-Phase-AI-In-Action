import React from 'react'
import { Stethoscope, Star, ShieldCheck, Calendar, MessageSquare } from 'lucide-react'
import { Link } from 'react-router-dom'

export function Doctors() {
  const doctors = [
    {
      name: 'ThS.BS Vũ Thu Trang',
      specialty: 'Trưởng Kíp Điều Phối Y Tế & Lâm Sàng',
      hospital: 'Bệnh viện Đại học Y Dược',
      rating: '4.95',
      reviews: '240',
      exp: '14 năm kinh nghiệm tại Bệnh viện Đại học Y Dược. Chuyên sâu về cấp cứu nội khoa và điều phối chẩn đoán đa tầng.',
      img: 'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=400'
    },
    {
      name: 'BS. CKII Lê Hoàng Nam',
      specialty: 'Khoa Tim Mạch Can Thiệp',
      hospital: 'Viện Tim Mạch Quốc Gia',
      rating: '4.98',
      reviews: '312',
      exp: '18 năm kinh nghiệm chuyên sâu bệnh lý mạch vành, nhồi máu cơ tim, suy tim và can thiệp mạch máu lồng ngực.',
      img: 'https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&q=80&w=400'
    },
    {
      name: 'BS. CKI Trần Minh Thảo',
      specialty: 'Nội Hô Hấp & Miễn Dịch Dị Ứng',
      hospital: 'Bệnh viện Bạch Mai',
      rating: '4.91',
      reviews: '188',
      exp: '11 năm kinh nghiệm điều trị bệnh phổi tắc nghẽn mãn tính, hen suyễn và các bệnh lý nhiễm trùng đường hô hấp cấp.',
      img: 'https://images.unsplash.com/photo-1594824813589-9a74e5088236?auto=format&fit=crop&q=80&w=400'
    }
  ]

  return (
    <section className="bg-slate-50 dark:bg-[#070D1E] py-24 border-b border-slate-200 dark:border-slate-800/80 text-slate-900 dark:text-white relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-6 reveal-item">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-medium text-blue-700 dark:text-cyan-300 border border-blue-500/30 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-3.5 py-1.5 mb-4 rounded-full">
              <Stethoscope className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400" />
              <span>ĐỘI NGŨ CHUYÊN GIA Y TẾ ĐẦU NGÀNH</span>
            </div>
            <h2 className="text-3xl lg:text-4xl font-semibold text-slate-900 dark:text-slate-100 mb-3 tracking-tight">
              Bác Sĩ Giám Sát Lâm Sàng Trực Tuyến 24/7
            </h2>
            <p className="text-slate-600 dark:text-slate-400 text-sm lg:text-base max-w-2xl leading-relaxed">
              Các chuyên gia giàu kinh nghiệm luôn túc trực song hành cùng AI để trực tiếp kiểm chứng phác đồ và hỗ trợ người bệnh.
            </p>
          </div>
          
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 text-xs font-medium bg-emerald-50 dark:bg-emerald-950/40 px-4 py-2 rounded-xl border border-emerald-300 dark:border-emerald-500/30 shrink-0">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>12 Bác sĩ đang trực ban tiếp nhận</span>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {doctors.map((doc, i) => (
            <div
              key={i}
              className="bg-white dark:bg-slate-900/60 rounded-2xl border border-slate-200 dark:border-slate-800/80 overflow-hidden hover:border-cyan-500/40 shadow-xs dark:shadow-none transition-all duration-300 hover:-translate-y-1 reveal-item flex flex-col justify-between"
            >
              <div className="relative h-60 overflow-hidden bg-slate-100 dark:bg-slate-950">
                <img
                  src={doc.img}
                  alt={doc.name}
                  className="w-full h-full object-cover object-top opacity-95 dark:opacity-90 transition-transform duration-500 hover:scale-105"
                />
                <div className="absolute top-3 left-3 bg-white/90 dark:bg-slate-950/80 backdrop-blur-md text-slate-800 dark:text-slate-200 text-xs font-medium px-3 py-1 rounded-lg border border-slate-200 dark:border-slate-700/60 flex items-center gap-2 shadow-xs">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  <span>Đang trực tiếp nhận</span>
                </div>
              </div>

              <div className="p-6 flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between text-xs mb-3 border-b border-slate-100 dark:border-slate-800/80 pb-3">
                    <span className="text-slate-500 dark:text-slate-400 font-medium">{doc.hospital}</span>
                    <div className="flex items-center gap-1 text-amber-500 font-semibold">
                      <Star className="w-3.5 h-3.5 fill-current" />
                      <span>{doc.rating}</span>
                      <span className="text-slate-400 font-normal">({doc.reviews})</span>
                    </div>
                  </div>

                  <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    {doc.name}
                  </h3>
                  <p className="text-xs font-medium text-blue-600 dark:text-cyan-400 mb-4">
                    {doc.specialty}
                  </p>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-6">
                    {doc.exp}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-4 border-t border-slate-100 dark:border-slate-800/80">
                  <Link
                    to="/patient"
                    className="btn-clinical-primary py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Tư Vấn Ngay</span>
                  </Link>
                  <Link
                    to="/patient/appointments"
                    className="btn-clinical-ghost py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5"
                  >
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Đặt Lịch</span>
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
