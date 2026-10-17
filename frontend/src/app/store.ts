import { configureStore, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import authReducer from '../features/auth/authSlice'
import staffAppointmentsReducer from '../features/staff-appointments/staffAppointmentsSlice'
import bookingApprovalsReducer from '../features/booking-approvals/bookingApprovalsSlice'
import staffPatientsReducer from '../features/staff-patients/staffPatientsSlice'
import staffDashboardReducer from '../features/staff-dashboard/staffDashboardSlice'
import staffApiCacheReducer, { cacheApiResponse, clearApiResponseCache, removeCachedApiResponse } from '../features/staff-api-cache/staffApiCacheSlice'
import { configureApiResponseCache } from './apiResponseCacheBridge'
import { readPublishedSession } from '../features/auth/session'

const getInitialTheme = (): 'dark' | 'light' => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('vcare_theme') || localStorage.getItem('medicare_theme')
    if (saved === 'light' || saved === 'dark') {
      return saved
    }
  }
  return 'light' // mặc định sáng; người dùng tự bật chế độ tối bằng công tắc
}

const initialTheme = getInitialTheme()

// Apply theme to document element immediately
if (typeof document !== 'undefined') {
  if (initialTheme === 'dark') {
    document.documentElement.classList.add('dark')
    document.documentElement.setAttribute('data-theme', 'dark')
  } else {
    document.documentElement.classList.remove('dark')
    document.documentElement.setAttribute('data-theme', 'light')
  }
}

interface LayoutState {
  isChatOpen: boolean
  theme: 'dark' | 'light'
}

const layoutSlice = createSlice({
  name: 'layout',
  initialState: {
    isChatOpen: false,
    theme: initialTheme
  } as LayoutState,
  reducers: {
    toggleChat: (state) => {
      state.isChatOpen = !state.isChatOpen
    },
    openChat: (state) => {
      state.isChatOpen = true
    },
    closeChat: (state) => {
      state.isChatOpen = false
    },
    toggleTheme: (state) => {
      state.theme = state.theme === 'dark' ? 'light' : 'dark'
      if (typeof window !== 'undefined') {
        localStorage.setItem('vcare_theme', state.theme)
      }
      if (typeof document !== 'undefined') {
        if (state.theme === 'dark') {
          document.documentElement.classList.add('dark')
          document.documentElement.setAttribute('data-theme', 'dark')
        } else {
          document.documentElement.classList.remove('dark')
          document.documentElement.setAttribute('data-theme', 'light')
        }
      }
    },
    setTheme: (state, action: PayloadAction<'dark' | 'light'>) => {
      state.theme = action.payload
      if (typeof window !== 'undefined') {
        localStorage.setItem('vcare_theme', state.theme)
      }
      if (typeof document !== 'undefined') {
        if (state.theme === 'dark') {
          document.documentElement.classList.add('dark')
          document.documentElement.setAttribute('data-theme', 'dark')
        } else {
          document.documentElement.classList.remove('dark')
          document.documentElement.setAttribute('data-theme', 'light')
        }
      }
    }
  }
})

export const { toggleChat, openChat, closeChat, toggleTheme, setTheme } = layoutSlice.actions

export const store = configureStore({
  reducer: {
    layout: layoutSlice.reducer,
    auth: authReducer,
    staffAppointments: staffAppointmentsReducer,
    bookingApprovals: bookingApprovalsReducer,
    staffPatients: staffPatientsReducer,
    staffDashboard: staffDashboardReducer,
    staffApiCache: staffApiCacheReducer
  }
})

configureApiResponseCache({
  get: key => store.getState().staffApiCache.entries[key],
  set: entry => { store.dispatch(cacheApiResponse(entry)) },
  remove: key => { store.dispatch(removeCachedApiResponse(key)) },
  clear: () => { store.dispatch(clearApiResponseCache()) },
  ownerId: () => readPublishedSession()?.id ?? null,
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
