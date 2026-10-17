import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import type { RootState } from '../../app/store'
import { fetchBookingServiceOptions, fetchPendingBookings, type BookingServiceOption, type StaffBookingPage } from '../../pages/AppointmentApproval/api'
import { loginUser, logout, logoutUser, sessionChanged } from '../auth/authSlice'

export const APPROVAL_TABS = ['all', 'pending_approval', 'confirmed', 'rejected'] as const
export type ApprovalTab = typeof APPROVAL_TABS[number]

export interface BookingApprovalFilters {
  q?: string
  serviceId?: string
  offset: number
  limit: number
}

export const approvalFilterKey = ({ q, serviceId, offset, limit }: BookingApprovalFilters) =>
  JSON.stringify([q ?? '', serviceId ?? '', offset, limit])
export const approvalPageKey = (filters: BookingApprovalFilters, tab: ApprovalTab) =>
  JSON.stringify([approvalFilterKey(filters), tab])

interface BookingApprovalsState {
  pages: Record<string, StaffBookingPage>
  services: BookingServiceOption[]
  servicesLoaded: boolean
  loading: Record<string, boolean>
  errors: Record<string, string>
  requests: Record<string, string>
}

const initialState: BookingApprovalsState = {
  pages: {},
  services: [],
  servicesLoaded: false,
  loading: {},
  errors: {},
  requests: {},
}

export const loadBookingApprovalViews = createAsyncThunk<
  { key: string; pages: Record<string, StaffBookingPage>; services?: BookingServiceOption[] },
  BookingApprovalFilters & { force?: boolean },
  { state: RootState; rejectValue: string }
>(
  'bookingApprovals/loadViews',
  async ({ force, ...filters }, { getState, rejectWithValue }) => {
    const state = getState().bookingApprovals
    try {
      const [all, pending, confirmed, rejected, services] = await Promise.all([
        fetchPendingBookings({ ...filters }),
        fetchPendingBookings({ ...filters, status: 'pending_approval' }),
        fetchPendingBookings({ ...filters, status: 'confirmed' }),
        fetchPendingBookings({ ...filters, status: 'rejected' }),
        state.servicesLoaded && !force ? Promise.resolve(undefined) : fetchBookingServiceOptions(),
      ])
      return {
        key: approvalFilterKey(filters),
        pages: { all, pending_approval: pending, confirmed, rejected },
        services,
      }
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Không thể tải danh sách lịch hẹn.')
    }
  },
  {
    condition: ({ force, ...filters }, { getState }) => {
      if (force) return true
      const state = getState().bookingApprovals
      return !state.servicesLoaded || APPROVAL_TABS.some(tab => !state.pages[approvalPageKey(filters, tab)])
    },
  },
)

const bookingApprovalsSlice = createSlice({
  name: 'bookingApprovals',
  initialState,
  reducers: {
    clearBookingApprovalPages(state) {
      state.pages = {}
      state.loading = {}
      state.errors = {}
      state.requests = {}
    },
  },
  extraReducers: builder => {
    builder
      .addCase(loadBookingApprovalViews.pending, (state, action) => {
        const key = approvalFilterKey(action.meta.arg)
        state.loading[key] = true
        state.errors[key] = ''
        state.requests[key] = action.meta.requestId
      })
      .addCase(loadBookingApprovalViews.fulfilled, (state, action) => {
        const { key, pages, services } = action.payload
        if (state.requests[key] !== action.meta.requestId) return
        for (const tab of APPROVAL_TABS) state.pages[approvalPageKey(action.meta.arg, tab)] = pages[tab]
        if (services) {
          state.services = services
          state.servicesLoaded = true
        }
        state.loading[key] = false
      })
      .addCase(loadBookingApprovalViews.rejected, (state, action) => {
        const key = approvalFilterKey(action.meta.arg)
        if (state.requests[key] !== action.meta.requestId) return
        state.loading[key] = false
        state.errors[key] = action.payload ?? 'Không thể tải danh sách lịch hẹn.'
      })
      .addCase(loginUser.fulfilled, () => initialState)
      .addCase(logout, () => initialState)
      .addCase(logoutUser.fulfilled, () => initialState)
      .addCase(sessionChanged, () => initialState)
  },
})

export const { clearBookingApprovalPages } = bookingApprovalsSlice.actions
export default bookingApprovalsSlice.reducer
