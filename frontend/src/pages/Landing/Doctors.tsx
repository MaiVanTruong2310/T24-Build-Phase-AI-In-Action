import { Link } from 'react-router-dom'
import { featuredDoctors } from './featuredDoctors'
import './Doctors.css'

export function Doctors() {
  return (
    <section className="bg-slate-50 light:bg-app-page dark:bg-[#070D1E] py-16 sm:py-24 border-b border-slate-200 light:border-app-border dark:border-slate-800/80 text-slate-900 light:text-app-text dark:text-white relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-10 gap-5 reveal-item">
          <div>
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-semibold mb-3 tracking-tight">Đội ngũ bác sĩ chuyên khoa</h2>
            <p className="text-slate-600 light:text-app-secondary dark:text-slate-400 text-sm lg:text-base max-w-2xl leading-relaxed">Tìm hiểu chuyên môn và nơi công tác của các bác sĩ để lựa chọn người phù hợp với nhu cầu khám.</p>
          </div>
          <Link to="/patient/doctors" className="shrink-0 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline underline-offset-4">Xem danh mục bác sĩ →</Link>
        </div>

        <div className="home-doctors-carousel" aria-label="Danh sách bác sĩ chuyên khoa">
          <div className="home-doctors-track">
          {[false, true].map(duplicate => (
            <div key={String(duplicate)} className="home-doctors-group" aria-hidden={duplicate || undefined}>
            {featuredDoctors.map(doctor => (
            <article key={doctor.id} className="home-doctor-card">
              <div className="home-doctor-photo">
                <img src={doctor.image} alt={doctor.name} loading="lazy" decoding="async" referrerPolicy="no-referrer" />
              </div>
              <div className="home-doctor-info">
                <p className="home-doctor-credentials">{doctor.credentials}</p>
                <h3>{doctor.name}</h3>
                <p className="home-doctor-specialty">{doctor.specialty}</p>
                {doctor.facility && <p className="home-doctor-facility">{doctor.facility}</p>}
              </div>
              <a className="home-doctor-profile" href={doctor.profileUrl} target="_blank" rel="noopener noreferrer" tabIndex={duplicate ? -1 : undefined} aria-label={`Xem hồ sơ bác sĩ ${doctor.name} trên Vinmec`}>Xem hồ sơ <span aria-hidden="true">↗</span></a>
            </article>
            ))}
            </div>
          ))}
          </div>
        </div>
        <p className="mt-6 text-xs text-slate-500 light:text-app-secondary dark:text-slate-400">Thông tin và ảnh bác sĩ từ danh mục Vinmec.</p>
      </div>
    </section>
  )
}
