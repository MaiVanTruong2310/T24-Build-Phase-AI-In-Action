import './AIIdentity.css'

export function AIIdentity({ avatarOnly = false, size = 'sm' }: { avatarOnly?: boolean; size?: 'sm' | 'md' }) {
  if (avatarOnly) return <span className={`vgreen-ai-avatar vgreen-ai-avatar--${size}`} role="img" aria-label="VgreenAI"><span className="vgreen-ai-card-photo" aria-hidden="true" /></span>
  return (
    <span className="vgreen-ai-card" aria-label="VgreenAI · AI Vip Pro Max">
      <svg className="vgreen-ai-doodle star" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2L15 9L22 10L17 15L18.5 22L12 18.5L5.5 22L7 15L2 10L9 9L12 2Z" /></svg>
      <svg className="vgreen-ai-doodle sparkle" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 0C12 6.6 17.4 12 24 12C17.4 12 12 17.4 12 24C12 17.4 6.6 12 0 12C6.6 12 12 6.6 12 0Z" /></svg>
      <svg className="vgreen-ai-doodle swirl" viewBox="0 0 100 100" aria-hidden="true"><path d="M50 10C27.9 10 10 27.9 10 50C10 72.1 27.9 90 50 90C72.1 90 90 72.1 90 50C90 32.3 75.7 18 58 18C44.3 18 33 29.3 33 43C33 53.5 41.5 62 52 62C59.7 62 66 55.7 66 48" /></svg>
      <span className="vgreen-ai-card-photo" aria-hidden="true" />
      <span className="vgreen-ai-card-title">VgreenAI<br /><span>AI Vip Pro Max</span></span>
    </span>
  )
}
