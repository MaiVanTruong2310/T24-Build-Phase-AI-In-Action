import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import type { PendingBooking } from '../../pages/AppointmentApproval/api'
import { loginUser, logout, logoutUser, sessionChanged } from '../auth/authSlice'

export const staffAppointmentsKey = (query: string, date: string, offset: number) => JSON.stringify([query, date, offset])

interface AppointmentSnapshot {
  items: PendingBooking[]
  total: number
}

interface StaffAppointmentsState {
  views: Record<string, AppointmentSnapshot>
  query: string
  date: string
  appliedQuery: string
  appliedDate: string
  offset: number
  filtersVersion: number
  generation: number
  loadingKeys: Record<string, boolean>
  error: string
  errorKey: string | null
}

const initialState: StaffAppointmentsState = {
  views: {},
  query: '',
  date: '',
  appliedQuery: '',
  appliedDate: '',
  offset: 0,
  filtersVersion: 0,
  generation: 0,
  loadingKeys: {},
  error: '',
  errorKey: null,
}

const staffAppointmentsSlice = createSlice({
  name: 'staffAppointments',
  initialState,
  reducers: {
    setSearchDraft(state, action: PayloadAction<string>) {
      state.query = action.payload
    },
    setDateDraft(state, action: PayloadAction<string>) {
      state.date = action.payload
    },
    applyAppointmentFilters(state) {
      state.appliedQuery = state.query.trim()
      state.appliedDate = state.date
      state.offset = 0
      state.error = ''
      state.errorKey = null
      state.filtersVersion += 1
    },
    clearAppointmentFilters(state) {
      state.query = ''
      state.date = ''
      state.appliedQuery = ''
      state.appliedDate = ''
      state.offset = 0
      state.error = ''
      state.errorKey = null
      state.filtersVersion += 1
    },
    setAppointmentOffset(state, action: PayloadAction<number>) {
      state.offset = action.payload
    },
    loadAppointmentsStarted(state, action: PayloadAction<{ key: string; generation: number }>) {
      if (action.payload.generation !== state.generation) return
      state.loadingKeys[action.payload.key] = true
      state.error = ''
      state.errorKey = null
    },
    loadAppointmentsSucceeded(state, action: PayloadAction<{ key: string; generation: number; items: PendingBooking[]; total: number }>) {
      if (action.payload.generation !== state.generation) return
      state.views[action.payload.key] = { items: action.payload.items, total: action.payload.total }
      delete state.loadingKeys[action.payload.key]
      if (state.errorKey === action.payload.key) {
        state.error = ''
        state.errorKey = null
      }
    },
    loadAppointmentsFailed(state, action: PayloadAction<{ key: string; generation: number; error: string }>) {
      if (action.payload.generation !== state.generation) return
      delete state.loadingKeys[action.payload.key]
      state.error = action.payload.error
      state.errorKey = action.payload.key
    },
    clearAppointmentViews(state) {
      state.views = {}
      state.generation += 1
      state.loadingKeys = {}
      state.error = ''
      state.errorKey = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.fulfilled, () => initialState)
      .addCase(logout, () => initialState)
      .addCase(logoutUser.fulfilled, () => initialState)
      .addCase(sessionChanged, () => initialState)
  },
})

export const {
  setSearchDraft,
  setDateDraft,
  applyAppointmentFilters,
  clearAppointmentFilters,
  setAppointmentOffset,
  loadAppointmentsStarted,
  loadAppointmentsSucceeded,
  loadAppointmentsFailed,
  clearAppointmentViews,
} = staffAppointmentsSlice.actions

export default staffAppointmentsSlice.reducer
