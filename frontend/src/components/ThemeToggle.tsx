import { memo } from 'react'
import { Sun, Moon } from 'lucide-react'
import { useSelector, useDispatch } from 'react-redux'
import type { RootState, AppDispatch } from '../app/store'
import { toggleTheme } from '../app/store'

export const ThemeToggle = memo(function ThemeToggle({ className = '' }: { className?: string }) {
  const dispatch = useDispatch<AppDispatch>()
  const theme = useSelector((state: RootState) => state.layout.theme)
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={() => dispatch(toggleTheme())}
      className={`relative inline-flex items-center justify-center w-9 h-9 rounded-xl transition-all duration-300 border ${
        isDark
          ? 'bg-slate-800/80 border-slate-700 text-amber-300 hover:bg-slate-700 hover:text-amber-200 shadow-sm'
          : 'bg-slate-100 border-slate-300 text-blue-600 hover:bg-slate-200 hover:text-blue-700 shadow-sm'
      } ${className}`}
      title={isDark ? 'Chuyển sang Giao diện Sáng (Clean Light Slate)' : 'Chuyển sang Giao diện Tối (Deep Medical Navy)'}
      aria-label="Toggle theme"
    >
      {isDark ? (
        <Sun className="w-4 h-4 transition-transform duration-300 hover:rotate-45" />
      ) : (
        <Moon className="w-4 h-4 transition-transform duration-300 hover:-rotate-12" />
      )}
    </button>
  )
})
