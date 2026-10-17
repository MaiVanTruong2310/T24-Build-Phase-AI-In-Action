import './ZaloBotButton.css'

const ZALO_BOT_URL = 'https://bot.zaloplatforms.com/groups/invite/bot.jhKJipBw'

/** Nút nổi mở Zalo Bot của VCare+ trong tab mới. `lifted`: nâng lên trên thanh nhập chat ở màn hình nhỏ. */
export function ZaloBotButton({ lifted = false }: { lifted?: boolean }) {
  return (
    <a
      href={ZALO_BOT_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={`zbot${lifted ? ' zbot--lifted' : ''}`}
      aria-label="Mở Zalo Bot của VCare+ (mở tab mới)"
    >
      <span className="zbot__badge" aria-hidden="true">Z</span>
      <span className="zbot__label">
        <span className="zbot__title">Zalo Bot</span>
        <span className="zbot__sub">Mở trong Zalo</span>
      </span>
    </a>
  )
}
