import { memo } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import type { RootState, AppDispatch } from '../app/store'
import { toggleTheme } from '../app/store'
import './ThemeToggle.css'

const stars = [[133, 0], [31, 19], [0, 32], [54, 21], [81, 21], [136, 32], [99, 46]]

export const ThemeToggle = memo(function ThemeToggle({ className = '' }: { className?: string }) {
  const dispatch = useDispatch<AppDispatch>()
  const theme = useSelector((state: RootState) => state.layout.theme)
  const isDark = theme === 'dark'

  return (
    <label
      className={`theme-switch ${className}`}
      title={isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
    >
      <input
        type="checkbox"
        role="switch"
        className="theme-switch__checkbox"
        checked={isDark}
        onChange={() => dispatch(toggleTheme())}
        aria-label="Giao diện tối"
      />
      <div className="theme-switch__container" aria-hidden="true">
        <div className="theme-switch__clouds" />
        <div className="theme-switch__stars-container">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 144 55" fill="none">
            {stars.map(([x, y]) => (
              <path
                key={`${x}-${y}`}
                transform={`translate(${x} ${y})`}
                d="M4 0C4 2.6 2.4 4.2 0 4.35C2.4 4.5 4 6.1 4 8.73C4 6.1 5.6 4.5 8 4.35C5.6 4.2 4 2.6 4 0Z"
                fill="currentColor"
              />
            ))}
          </svg>
        </div>
        <div className="theme-switch__circle-container">
          <div className="theme-switch__sun-moon-container">
            <div className="theme-switch__moon">
              <div className="theme-switch__spot" />
              <div className="theme-switch__spot" />
              <div className="theme-switch__spot" />
            </div>
          </div>
        </div>
      </div>
    </label>
  )
})
