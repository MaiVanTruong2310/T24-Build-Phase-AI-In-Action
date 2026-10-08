import React, { useState, useEffect, useRef } from 'react'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
import { formatDateVN, parseVNToIsoDate } from '../features/appointment-booking/dateValidation'

export interface DateInputVNProps {
  id?: string
  name?: string
  value?: string // YYYY-MM-DD or DD/MM/YYYY or empty
  onChange?: (e: { target: { name: string; value: string } }) => void
  onBlur?: () => void
  placeholder?: string
  disabled?: boolean
  hasError?: boolean
  min?: string // YYYY-MM-DD
  max?: string // YYYY-MM-DD
  className?: string
  required?: boolean
}

const MONTH_NAMES = [
  'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4',
  'Tháng 5', 'Tháng 6', 'Tháng 7', 'Tháng 8',
  'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'
]

const WEEK_DAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

function getDaysInMonth(year: number, monthIndex: number): number {
  return new Date(year, monthIndex + 1, 0).getDate()
}

function getFirstDayOfWeek(year: number, monthIndex: number): number {
  // 0 is Sunday in JS Date, convert so Monday is 0 and Sunday is 6
  const day = new Date(year, monthIndex, 1).getDay()
  return (day + 6) % 7
}

function toIsoString(year: number, monthIndex: number, day: number): string {
  const y = String(year).padStart(4, '0')
  const m = String(monthIndex + 1).padStart(2, '0')
  const d = String(day).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function toVnString(year: number, monthIndex: number, day: number): string {
  const y = String(year).padStart(4, '0')
  const m = String(monthIndex + 1).padStart(2, '0')
  const d = String(day).padStart(2, '0')
  return `${d}/${m}/${y}`
}

export function DateInputVN({
  id,
  name = '',
  value = '',
  onChange,
  onBlur,
  placeholder = 'dd/mm/yyyy',
  disabled = false,
  hasError = false,
  min,
  max,
  className = '',
  required = false,
}: DateInputVNProps) {
  // Display text in input box (strictly dd/mm/yyyy)
  const [displayText, setDisplayText] = useState(() => formatDateVN(value))
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Current calendar view state (month: 0-11, year)
  const today = new Date()
  const initialYear = today.getFullYear()
  const initialMonth = today.getMonth()

  const [viewYear, setViewYear] = useState(initialYear)
  const [viewMonth, setViewMonth] = useState(initialMonth)

  // Sync internal display text when external value changes
  useEffect(() => {
    const formatted = formatDateVN(value)
    setDisplayText(formatted)

    if (value) {
      const iso = parseVNToIsoDate(value)
      if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
        const [y, m] = iso.split('-').map(Number)
        setViewYear(y)
        setViewMonth(m - 1)
      }
    }
  }, [value])

  // Close calendar popover on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Emit standardized YYYY-MM-DD value
  const emitChange = (isoDate: string) => {
    if (onChange) {
      onChange({
        target: {
          name,
          value: isoDate,
        },
      })
    }
  }

  // Handle typing with smart dd/mm/yyyy auto-masking
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let raw = e.target.value.replace(/[^\d/]/g, '')

    // Remove extra slashes
    const parts = raw.split('/')
    if (parts.length > 3) {
      raw = parts.slice(0, 3).join('/')
    }

    // Auto format numbers into dd/mm/yyyy
    const digits = raw.replace(/\D/g, '')
    let formatted = ''
    if (digits.length <= 2) {
      formatted = digits
    } else if (digits.length <= 4) {
      formatted = `${digits.slice(0, 2)}/${digits.slice(2)}`
    } else {
      formatted = `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4, 8)}`
    }

    setDisplayText(formatted)

    // If complete dd/mm/yyyy (10 characters)
    if (formatted.length === 10 && /^\d{2}\/\d{2}\/\d{4}$/.test(formatted)) {
      const [d, m, y] = formatted.split('/').map(Number)
      if (m >= 1 && m <= 12 && d >= 1 && d <= getDaysInMonth(y, m - 1)) {
        const iso = toIsoString(y, m - 1, d)
        emitChange(iso)
        setViewYear(y)
        setViewMonth(m - 1)
        return
      }
    }

    // If cleared or incomplete
    if (formatted === '') {
      emitChange('')
    }
  }

  // Handle picking a day from calendar
  const handleSelectDay = (day: number) => {
    const iso = toIsoString(viewYear, viewMonth, day)
    const vn = toVnString(viewYear, viewMonth, day)
    setDisplayText(vn)
    emitChange(iso)
    setIsOpen(false)
  }

  // Quick navigation
  const prevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11)
      setViewYear(y => y - 1)
    } else {
      setViewMonth(m => m - 1)
    }
  }

  const nextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0)
      setViewYear(y => y + 1)
    } else {
      setViewMonth(m => m + 1)
    }
  }

  const handleClear = () => {
    setDisplayText('')
    emitChange('')
    setIsOpen(false)
  }

  const handleSelectToday = () => {
    const y = today.getFullYear()
    const m = today.getMonth()
    const d = today.getDate()
    handleSelectDay(d)
    setViewYear(y)
    setViewMonth(m)
  }

  // Calendar matrix calculation
  const totalDays = getDaysInMonth(viewYear, viewMonth)
  const firstDay = getFirstDayOfWeek(viewYear, viewMonth)
  const selectedIso = value ? parseVNToIsoDate(value) : ''
  const todayIso = toIsoString(today.getFullYear(), today.getMonth(), today.getDate())

  // Year range for selector (1900 to current year + 10)
  const minYear = 1900
  const maxYear = today.getFullYear() + 5
  const yearOptions: number[] = []
  for (let y = maxYear; y >= minYear; y--) {
    yearOptions.push(y)
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative flex items-center">
        <input
          type="text"
          id={id}
          name={name}
          value={displayText}
          onChange={handleInputChange}
          onBlur={onBlur}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          maxLength={10}
          className={className || `w-full px-4 py-3 pr-10 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
            hasError
              ? 'border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20'
              : 'border-slate-200 light:border-app-border dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:ring-blue-500/20 focus:border-blue-500'
          }`}
        />
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          aria-label="Mở lịch chọn ngày"
          className="absolute right-2.5 p-1.5 text-slate-400 hover:text-blue-600 dark:text-slate-500 dark:hover:text-blue-400 rounded-lg transition-colors focus:outline-none"
        >
          <Calendar className="w-4 h-4" />
        </button>
      </div>

      {/* Calendar Dropdown Popover */}
      {isOpen && (
        <div className="absolute z-50 mt-1.5 p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-xl w-72 sm:w-80 select-none animate-in fade-in zoom-in-95 duration-100">
          {/* Calendar Header with Quick Month/Year Dropdown */}
          <div className="flex items-center justify-between gap-1 mb-3">
            <button
              type="button"
              onClick={prevMonth}
              className="p-1 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Tháng trước"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-1.5 font-medium text-xs sm:text-sm">
              <select
                value={viewMonth}
                onChange={e => setViewMonth(Number(e.target.value))}
                className="bg-slate-100 dark:bg-slate-800 border-0 rounded-lg px-2 py-1 text-slate-800 dark:text-slate-200 font-semibold text-xs cursor-pointer focus:ring-1 focus:ring-blue-500 outline-none"
              >
                {MONTH_NAMES.map((name, idx) => (
                  <option key={idx} value={idx}>{name}</option>
                ))}
              </select>

              <select
                value={viewYear}
                onChange={e => setViewYear(Number(e.target.value))}
                className="bg-slate-100 dark:bg-slate-800 border-0 rounded-lg px-2 py-1 text-slate-800 dark:text-slate-200 font-semibold text-xs cursor-pointer focus:ring-1 focus:ring-blue-500 outline-none"
              >
                {yearOptions.map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={nextMonth}
              className="p-1 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Tháng sau"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Weekday headers */}
          <div className="grid grid-cols-7 gap-1 text-center mb-1">
            {WEEK_DAYS.map(w => (
              <span key={w} className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 py-1">
                {w}
              </span>
            ))}
          </div>

          {/* Day Grid */}
          <div className="grid grid-cols-7 gap-1 text-center">
            {/* Empty slots before first day */}
            {Array.from({ length: firstDay }).map((_, i) => (
              <div key={`empty-${i}`} className="h-8" />
            ))}

            {/* Days of month */}
            {Array.from({ length: totalDays }).map((_, i) => {
              const day = i + 1
              const iso = toIsoString(viewYear, viewMonth, day)
              const isSelected = selectedIso === iso
              const isToday = todayIso === iso

              // Min / Max restrictions
              const isBeforeMin = min ? iso < min : false
              const isAfterMax = max ? iso > max : false
              const isDisabled = isBeforeMin || isAfterMax

              return (
                <button
                  key={day}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => handleSelectDay(day)}
                  className={`h-8 w-8 mx-auto text-xs font-medium rounded-lg flex items-center justify-center transition-all ${
                    isDisabled
                      ? 'text-slate-300 dark:text-slate-700 cursor-not-allowed opacity-40'
                      : isSelected
                      ? 'bg-blue-600 text-white font-bold shadow-sm shadow-blue-500/30'
                      : isToday
                      ? 'border border-blue-500 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {day}
                </button>
              )
            })}
          </div>

          {/* Footer quick action buttons */}
          <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={handleSelectToday}
              className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
            >
              Hôm nay
            </button>
            <button
              type="button"
              onClick={handleClear}
              className="text-slate-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
            >
              Xóa chọn
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
