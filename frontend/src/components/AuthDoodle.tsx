import type { ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import type { RootState } from '../app/store'
import './AuthDoodle.css'
import './AuthDoodleOverrides.css'

/** Presentation shell only: the routed forms own validation and authentication. */
export function AuthDoodle({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const loading = useSelector((state: RootState) => state.auth.loading)
  const signup = location.pathname === '/register'
  const destination = `${signup ? '/login' : '/register'}${location.search}`

  return (
    <div className={`auth-doodle-wrapper ${signup ? 'auth-doodle-signup' : 'auth-doodle-login'}`}>
      <div className="auth-doodle-header">
        <Link className={`auth-doodle-mode-text ${!signup ? 'is-active' : ''}`} to={`/login${location.search}`}>Đăng nhập</Link>
        <label className="auth-doodle-switch-label">
          <input
            type="checkbox"
            role="switch"
            className="auth-doodle-toggle"
            checked={signup}
            disabled={loading}
            onChange={() => navigate(destination)}
            aria-label="Chuyển giữa đăng nhập và đăng ký"
          />
          <span className="auth-doodle-switch-handle" aria-hidden="true" />
        </label>
        <Link className={`auth-doodle-mode-text ${signup ? 'is-active' : ''}`} to={`/register${location.search}`}>Đăng ký</Link>
      </div>

      <div className="auth-doodle-card-scene">
        <svg className="auth-doodle-svg auth-doodle-star" viewBox="0 0 24 24" fill="#ffd166" stroke="var(--ink)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>
        <svg className="auth-doodle-svg auth-doodle-sparkle" viewBox="0 0 24 24" fill="#06d6a0" stroke="var(--ink)" strokeWidth="1.5" aria-hidden="true"><path d="M12 2 Q12 12 22 12 Q12 12 12 22 Q12 12 2 12 Q12 12 12 2 Z" /></svg>
        <svg className="auth-doodle-svg auth-doodle-swirl" viewBox="0 0 24 24" fill="none" stroke="var(--ink)" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true"><path d="M3 12 C 3 5 10 5 16 5 C 20 5 21 9 18 12 C 15 15 10 13 12 9 C 14 5 22 9 21 16" /></svg>
        <div key={location.pathname} className={`auth-doodle-card-inner ${signup ? 'is-signup' : 'is-login'}`}>
          <div className={`auth-doodle-placeholder ${signup ? 'auth-doodle-card-front' : 'auth-doodle-card-back'}`} aria-hidden="true">
            <img src="/vcare-logo.png" alt="" />
            <span>VCare+</span>
          </div>
          <div className={`auth-doodle-active-face ${signup ? 'auth-doodle-card-back' : 'auth-doodle-card-front'}`}>
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}
