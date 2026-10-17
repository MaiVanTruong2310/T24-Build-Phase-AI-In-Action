import { TypewriterLoader } from './TypewriterLoader'

export function DataLoadingState({
  className = 'py-20 flex flex-col items-center justify-center text-slate-400',
  label = 'Đang tải dữ liệu mới nhất...',
}: {
  className?: string
  label?: string
}) {
  return (
    <div className={className} role="status" aria-live="polite">
      <TypewriterLoader />
      <p className="text-sm font-semibold">{label}</p>
    </div>
  )
}
