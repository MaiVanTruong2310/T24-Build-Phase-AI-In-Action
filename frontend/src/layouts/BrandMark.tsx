
export function BrandMark() {
  return (
    <div className="flex items-center gap-3" aria-label="VCare+">
      <img
        src="/vcare-logo.png"
        alt="VCare+"
        className="size-10 rounded-xl object-contain bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm shrink-0 p-0.5"
      />
      <div className="leading-tight">
        <div className="text-lg font-bold tracking-tight text-slate-900">
          VCare<span className="text-sky-600">+</span>
        </div>
        <div className="text-[10px] font-medium text-slate-500">
          Hệ Thống Y Tế Số Đa Tầng Bác Sĩ Giám Sát
        </div>
      </div>
    </div>
  )
}
