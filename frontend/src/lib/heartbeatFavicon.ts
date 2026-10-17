/** A slow ECG trace; installed app icons use the uploaded brand logo. */
export function startHeartbeatFavicon(): () => void {
  const icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (!icon) return () => {}

  const originalHref = icon.href
  const originalType = icon.type
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 64
  const ctx = canvas.getContext('2d')
  if (!ctx) return () => {}

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
  let frame = 0
  let lastPaint = 0
  let start = 0
  const points = [[0, 17], [11, 17], [14, 15], [17, 17], [20, 17], [22, 20], [25, 7], [28, 25], [31, 17], [35, 17], [39, 14], [43, 17], [48, 17]]

  const restore = () => {
    cancelAnimationFrame(frame)
    icon.href = originalHref
    icon.type = originalType
  }

  const paint = (time: number) => {
    if (!start) start = time
    if (time - lastPaint >= 125) {
      lastPaint = time
      const shift = ((time - start) / 4000 * 48) % 48
      ctx.setTransform(2, 0, 0, 2, 0, 0)
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, 32, 32)
      ctx.strokeStyle = '#dc2626'
      ctx.lineWidth = 2
      ctx.lineJoin = 'round'
      ctx.lineCap = 'round'
      ctx.beginPath()
      for (let cycle = -1; cycle <= 1; cycle++) {
        for (const [x, y] of points) {
          const px = x + cycle * 48 + shift
          if (cycle === -1 && x === 0) ctx.moveTo(px, y)
          else ctx.lineTo(px, y)
        }
      }
      ctx.stroke()
      icon.type = 'image/png'
      icon.href = canvas.toDataURL('image/png')
    }
    frame = requestAnimationFrame(paint)
  }

  const update = () => {
    restore()
    start = lastPaint = 0
    if (!document.hidden && !reducedMotion.matches) frame = requestAnimationFrame(paint)
  }
  document.addEventListener('visibilitychange', update)
  reducedMotion.addEventListener('change', update)
  update()
  return () => {
    restore()
    document.removeEventListener('visibilitychange', update)
    reducedMotion.removeEventListener('change', update)
  }
}
