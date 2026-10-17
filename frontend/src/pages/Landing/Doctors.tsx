import { Link } from 'react-router-dom'
import { featuredDoctors } from './featuredDoctors'
import './Doctors.css'
import './Sections.css'

export function Doctors() {
  return (
    <section className="lp-section" aria-labelledby="doctors-title">
      <div className="lp-wrap">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-10 gap-5 reveal-item">
          <div className="max-w-2xl">
            <p className="lp-kicker">Danh mục bác sĩ</p>
            <h2 id="doctors-title" className="lp-title mb-3">Chọn bác sĩ theo chuyên môn</h2>
            <p className="text-app-secondary text-sm lg:text-base leading-relaxed">Tra cứu chuyên môn và nơi công tác để chọn người phù hợp với nhu cầu khám. Dữ liệu tham khảo từ danh mục Vinmec.</p>
          </div>
          <Link to="/patient/doctors" className="hero-btn hero-btn--ghost shrink-0">Xem danh mục bác sĩ <span aria-hidden="true">→</span></Link>
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
        <p className="mt-6 text-xs text-app-secondary">Thông tin và ảnh bác sĩ lấy từ danh mục công khai của Vinmec, chỉ nhằm minh họa.</p>
      </div>
    </section>
  )
}
