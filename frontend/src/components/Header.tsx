import { memo } from 'react'
import { Link } from 'react-router-dom'
import { ThemeToggle } from './ThemeToggle'
import { SimpleModeToggle } from './SimpleModeToggle'
import './AuthHeader.css'

/** Header của nhóm trang đăng nhập / đăng ký / quên mật khẩu: cùng ngôn ngữ vẽ tay với header trang chủ. */
export const Header = memo(function Header() {
  return (
    <header className="auth-hd">
      <Link to="/" className="auth-hd__brand" aria-label="VCare+ · Hệ Thống Khám Bệnh Đa Tầng Bác Sĩ Giám Sát · Trang chủ">
        <svg viewBox="0 0 64 64" aria-hidden="true">
          <path d="M18 10h20v16h16v18H38v16H18V44H4V26h14z" fill="var(--app-accent, #bd5f57)" />
          <path d="M23 5l18 1 1 17 17-1-1 19-15 1-1 17-21-1 1-15-17-1 1-21 15 1z" fill="none" stroke="var(--hd-ink, #1f2d26)" strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
          <path d="M22 6.5l19.5-.5-.5 17.5 17 .5-.5 18-16.5.5.5 17-19 .5-.5-16.5-16-.5.5-19 16 .5z" fill="none" stroke="var(--hd-ink, #1f2d26)" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />
        </svg>
        <span className="auth-hd__text">
          <span className="auth-hd__wordmark">VCare<span>+</span></span>
          <span className="auth-hd__slogan">Hệ Thống Khám Bệnh Đa Tầng Bác Sĩ Giám Sát</span>
        </span>
      </Link>

      <div className="auth-hd__actions">
        <Link to="/" className="auth-hd__home">Về trang chủ</Link>
        <SimpleModeToggle />
        <ThemeToggle />
      </div>

      {/* Nét mực gợn sóng thay cho đường kẻ thẳng */}
      <svg className="auth-hd__wave" aria-hidden="true" viewBox="0 0 1440 10" preserveAspectRatio="none">
        <path d="M0 5 C 120 2, 200 8, 340 4 S 560 1, 700 5 S 940 8, 1080 4 S 1320 2, 1440 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      </svg>
    </header>
  )
})
