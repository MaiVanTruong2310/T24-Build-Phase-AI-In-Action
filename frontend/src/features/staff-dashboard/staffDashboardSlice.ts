import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { fetchWithAuth } from '../../app/apiClient'
import { loginUser, logout, logoutUser, sessionChanged } from '../auth/authSlice'

export type DashboardOption = { id: string; name: string }
export type DashboardMetrics = { cases_handled: number; chat_escalations: number; patients_total: number; chat_cases_ai_handled_without_escalation: number; cases_with_coordinator_intervention: number; bookings_created: number; bookings_approved: number; schedules_starting: number; reminders_delivered: number }
export type DashboardSummary = { range: { from: string; to: string }; metrics: DashboardMetrics }
export type DashboardFilters = { from: string; through: string; facility: string; doctor: string }

const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date())
const initialFilters = (): DashboardFilters => {
  const through = today()
  const fromDate = new Date(`${through}T00:00:00+07:00`)
  fromDate.setUTCDate(fromDate.getUTCDate() - 13)
  return { from: fromDate.toISOString().slice(0, 10), through, facility: '', doctor: '' }
}
const nextDate = (date: string) => {
  const value = new Date(`${date}T00:00:00+07:00`)
  value.setUTCDate(value.getUTCDate() + 1)
  return value.toISOString().slice(0, 10)
}
const TTL = 30_000
const summaryKey = (filters: DashboardFilters) => JSON.stringify([filters.from, filters.through, filters.facility, filters.doctor])
const readData = async <T>(path: string, signal: AbortSignal): Promise<T> => {
  const response = await fetchWithAuth(path, { signal })
  const body = await response.json()
  if (!response.ok) throw new Error(body.message || body.detail || 'Không thể tải dữ liệu tổng quan.')
  return body.data as T
}

interface State {
  filters: DashboardFilters
  facilities: DashboardOption[]
  facilityLoadedAt: number
  facilityLoading: boolean
  facilityError: string
  doctors: Record<string, DashboardOption[]>
  doctorsLoadedAt: Record<string, number>
  doctorsLoading: Record<string, boolean>
  doctorsError: Record<string, string>
  summaries: Record<string, DashboardSummary>
  summaryLoadedAt: Record<string, number>
  summaryLoading: Record<string, boolean>
  summaryError: Record<string, string>
  requests: Record<string, string>
}
const initialState = (): State => ({ filters: initialFilters(), facilities: [], facilityLoadedAt: 0, facilityLoading: false, facilityError: '', doctors: {}, doctorsLoadedAt: {}, doctorsLoading: {}, doctorsError: {}, summaries: {}, summaryLoadedAt: {}, summaryLoading: {}, summaryError: {}, requests: {} })
type DashboardRootState = { staffDashboard: State }

export const loadDashboardFacilities = createAsyncThunk<DashboardOption[], { force?: boolean } | undefined, { state: DashboardRootState; rejectValue: string }>(
  'staffDashboard/loadFacilities', async (_, { signal, rejectWithValue }) => {
    try { return await readData<DashboardOption[]>('/facilities?limit=100', signal) }
    catch (error) { return rejectWithValue(error instanceof Error ? error.message : 'Không thể tải danh sách cơ sở.') }
  }, { condition: (arg, { getState }) => arg?.force === true || (!getState().staffDashboard.facilityLoading && Date.now() - getState().staffDashboard.facilityLoadedAt >= TTL) },
)
export const loadDashboardDoctors = createAsyncThunk<DashboardOption[], { facility: string; force?: boolean }, { state: DashboardRootState; rejectValue: string }>(
  'staffDashboard/loadDoctors', async ({ facility }, { signal, rejectWithValue }) => {
    try {
      const params = new URLSearchParams({ limit: '100' })
      if (facility) params.set('facility_id', facility)
      const rows = await readData<Array<{ id: string; full_name: string }>>(`/staff/doctors?${params}`, signal)
      return rows.map(({ id, full_name }) => ({ id, name: full_name }))
    } catch (error) { return rejectWithValue(error instanceof Error ? error.message : 'Không thể tải danh sách bác sĩ.') }
  }, { condition: ({ facility, force }, { getState }) => force === true || (!(getState().staffDashboard.doctorsLoading[facility] ?? false) && Date.now() - (getState().staffDashboard.doctorsLoadedAt[facility] ?? 0) >= TTL) },
)
export const loadDashboardSummary = createAsyncThunk<DashboardSummary, { filters: DashboardFilters; force?: boolean }, { state: DashboardRootState; rejectValue: string }>(
  'staffDashboard/loadSummary', async ({ filters }, { signal, rejectWithValue }) => {
    const params = new URLSearchParams({ from: `${filters.from}T00:00:00+07:00`, to: `${nextDate(filters.through)}T00:00:00+07:00` })
    if (filters.facility) params.set('facility_id', filters.facility)
    if (filters.doctor) params.set('doctor_id', filters.doctor)
    try { return await readData<DashboardSummary>(`/staff/dashboard/summary?${params}`, signal) }
    catch (error) { return rejectWithValue(error instanceof Error ? error.message : 'Không thể tải tổng quan hệ thống.') }
  }, { condition: ({ filters, force }, { getState }) => force === true || (!(getState().staffDashboard.summaryLoading[summaryKey(filters)] ?? false) && Date.now() - (getState().staffDashboard.summaryLoadedAt[summaryKey(filters)] ?? 0) >= TTL) },
)

const staffDashboardSlice = createSlice({
  name: 'staffDashboard', initialState: initialState(),
  reducers: {
    setDashboardFilter(state, action: PayloadAction<{ key: keyof DashboardFilters; value: string }>) {
      state.filters[action.payload.key] = action.payload.value
      if (action.payload.key === 'facility') state.filters.doctor = ''
    },
  },
  extraReducers: builder => builder
    .addCase(loadDashboardFacilities.pending, state => { state.facilityLoading = true; state.facilityError = '' })
    .addCase(loadDashboardFacilities.fulfilled, (state, action) => { state.facilities = action.payload; state.facilityLoadedAt = Date.now(); state.facilityLoading = false })
    .addCase(loadDashboardFacilities.rejected, (state, action) => { state.facilityLoading = false; if (!action.meta.aborted) state.facilityError = action.payload ?? 'Không thể tải danh sách cơ sở.' })
    .addCase(loadDashboardDoctors.pending, (state, action) => { const key = action.meta.arg.facility; state.doctorsLoading[key] = true; state.doctorsError[key] = '' })
    .addCase(loadDashboardDoctors.fulfilled, (state, action) => { const key = action.meta.arg.facility; state.doctors[key] = action.payload; state.doctorsLoadedAt[key] = Date.now(); state.doctorsLoading[key] = false })
    .addCase(loadDashboardDoctors.rejected, (state, action) => { const key = action.meta.arg.facility; state.doctorsLoading[key] = false; if (!action.meta.aborted) state.doctorsError[key] = action.payload ?? 'Không thể tải danh sách bác sĩ.' })
    .addCase(loadDashboardSummary.pending, (state, action) => { const key = summaryKey(action.meta.arg.filters); state.summaryLoading[key] = true; state.summaryError[key] = ''; state.requests[key] = action.meta.requestId })
    .addCase(loadDashboardSummary.fulfilled, (state, action) => { const key = summaryKey(action.meta.arg.filters); if (state.requests[key] !== action.meta.requestId) return; state.summaries[key] = action.payload; state.summaryLoadedAt[key] = Date.now(); state.summaryLoading[key] = false })
    .addCase(loadDashboardSummary.rejected, (state, action) => { const key = summaryKey(action.meta.arg.filters); if (state.requests[key] !== action.meta.requestId) return; state.summaryLoading[key] = false; if (!action.meta.aborted) state.summaryError[key] = action.payload ?? 'Không thể tải tổng quan hệ thống.' })
    .addCase(loginUser.fulfilled, initialState)
    .addCase(logout, initialState)
    .addCase(logoutUser.fulfilled, initialState)
    .addCase(sessionChanged, initialState),
})

export const { setDashboardFilter } = staffDashboardSlice.actions
export const selectDashboardSummary = (state: DashboardRootState) => state.staffDashboard.summaries[summaryKey(state.staffDashboard.filters)]
export const selectDashboardSummaryLoading = (state: DashboardRootState) => state.staffDashboard.summaryLoading[summaryKey(state.staffDashboard.filters)] ?? false
export const selectDashboardSummaryError = (state: DashboardRootState) => state.staffDashboard.summaryError[summaryKey(state.staffDashboard.filters)] ?? ''
export default staffDashboardSlice.reducer
