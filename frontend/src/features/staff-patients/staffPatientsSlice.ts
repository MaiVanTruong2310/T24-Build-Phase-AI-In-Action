import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../../app/store'
import { fetchStaffPatient, fetchStaffPatients, type StaffPatientDetail, type StaffPatientPage } from '../../pages/StaffPatients/api'
import { loginUser, logout, logoutUser, sessionChanged } from '../auth/authSlice'

export interface PatientFilters {
  q: string
  status: string
  gender: string
  created_from: string
  created_to: string
}

const emptyFilters: PatientFilters = { q: '', status: '', gender: '', created_from: '', created_to: '' }
const pageKey = (filters: PatientFilters, offset: number) => JSON.stringify([filters, offset])
const CACHE_TTL_MS = 30_000

interface StaffPatientsState {
  draft: PatientFilters
  filters: PatientFilters
  offset: number
  views: Record<string, StaffPatientPage>
  loadedAt: Record<string, number>
  loading: Record<string, boolean>
  errors: Record<string, string>
  requests: Record<string, string>
  selected: string | null
  details: Record<string, StaffPatientDetail>
  detailLoadedAt: Record<string, number>
  detailLoading: Record<string, boolean>
  detailErrors: Record<string, string>
  detailRequests: Record<string, string>
}

const initialState: StaffPatientsState = {
  draft: { ...emptyFilters }, filters: { ...emptyFilters }, offset: 0,
  views: {}, loadedAt: {}, loading: {}, errors: {}, requests: {}, selected: null,
  details: {}, detailLoadedAt: {}, detailLoading: {}, detailErrors: {}, detailRequests: {},
}

export const loadStaffPatients = createAsyncThunk<StaffPatientPage, { filters: PatientFilters; offset: number; force?: boolean }, { state: RootState; rejectValue: string }>(
  'staffPatients/loadList',
  async ({ filters, offset }, { signal, rejectWithValue }) => {
    const params = new URLSearchParams({ offset: String(offset), limit: '20' })
    Object.entries(filters).forEach(([key, value]) => { if (value.trim()) params.set(key, value.trim()) })
    try { return await fetchStaffPatients(params, signal) }
    catch (error) { return rejectWithValue(error instanceof Error ? error.message : 'Không thể tải danh sách bệnh nhân.') }
  },
  { condition: ({ filters, offset, force }, { getState }) => force === true || Date.now() - (getState().staffPatients.loadedAt[pageKey(filters, offset)] ?? 0) >= CACHE_TTL_MS },
)

export const loadStaffPatientDetail = createAsyncThunk<StaffPatientDetail, { id: string; force?: boolean }, { state: RootState; rejectValue: string }>(
  'staffPatients/loadDetail',
  async ({ id }, { signal, rejectWithValue }) => {
    try { return await fetchStaffPatient(id, signal) }
    catch (error) { return rejectWithValue(error instanceof Error ? error.message : 'Không thể tải hồ sơ bệnh nhân.') }
  },
  { condition: ({ id, force }, { getState }) => force === true || Date.now() - (getState().staffPatients.detailLoadedAt[id] ?? 0) >= CACHE_TTL_MS },
)

const staffPatientsSlice = createSlice({
  name: 'staffPatients', initialState,
  reducers: {
    setPatientDraft(state, action: PayloadAction<{ key: keyof PatientFilters; value: string }>) { state.draft[action.payload.key] = action.payload.value },
    applyPatientFilters(state) { state.filters = { ...state.draft, q: state.draft.q.trim() }; state.offset = 0; state.selected = null },
    resetPatientFilters(state) { state.draft = { ...emptyFilters }; state.filters = { ...emptyFilters }; state.offset = 0; state.selected = null },
    setPatientOffset(state, action: PayloadAction<number>) { state.offset = Math.max(0, action.payload) },
    selectPatient(state, action: PayloadAction<string | null>) { state.selected = action.payload },
  },
  extraReducers: builder => {
    builder
      .addCase(loadStaffPatients.pending, (state, action) => {
        const key = pageKey(action.meta.arg.filters, action.meta.arg.offset)
        state.loading[key] = true; state.errors[key] = ''; state.requests[key] = action.meta.requestId
      })
      .addCase(loadStaffPatients.fulfilled, (state, action) => {
        const key = pageKey(action.meta.arg.filters, action.meta.arg.offset)
        if (state.requests[key] !== action.meta.requestId) return
        state.views[key] = action.payload; state.loading[key] = false; state.loadedAt[key] = Date.now()
      })
      .addCase(loadStaffPatients.rejected, (state, action) => {
        const key = pageKey(action.meta.arg.filters, action.meta.arg.offset)
        if (state.requests[key] !== action.meta.requestId) return
        state.loading[key] = false
        if (!action.meta.aborted) state.errors[key] = action.payload ?? 'Không thể tải danh sách bệnh nhân.'
      })
      .addCase(loadStaffPatientDetail.pending, (state, action) => {
        const id = action.meta.arg.id
        state.detailLoading[id] = true; state.detailErrors[id] = ''; state.detailRequests[id] = action.meta.requestId
      })
      .addCase(loadStaffPatientDetail.fulfilled, (state, action) => {
        const id = action.meta.arg.id
        if (state.detailRequests[id] !== action.meta.requestId) return
        state.details[id] = action.payload; state.detailLoading[id] = false; state.detailLoadedAt[id] = Date.now()
      })
      .addCase(loadStaffPatientDetail.rejected, (state, action) => {
        const id = action.meta.arg.id
        if (state.detailRequests[id] !== action.meta.requestId) return
        state.detailLoading[id] = false
        if (!action.meta.aborted) state.detailErrors[id] = action.payload ?? 'Không thể tải hồ sơ bệnh nhân.'
      })
      .addCase(loginUser.fulfilled, () => initialState)
      .addCase(logout, () => initialState)
      .addCase(logoutUser.fulfilled, () => initialState)
      .addCase(sessionChanged, () => initialState)
  },
})

export const { setPatientDraft, applyPatientFilters, resetPatientFilters, setPatientOffset, selectPatient } = staffPatientsSlice.actions
export const selectStaffPatientPage = (state: RootState) => state.staffPatients.views[pageKey(state.staffPatients.filters, state.staffPatients.offset)]
export const selectStaffPatientLoading = (state: RootState) => state.staffPatients.loading[pageKey(state.staffPatients.filters, state.staffPatients.offset)] ?? false
export const selectStaffPatientError = (state: RootState) => state.staffPatients.errors[pageKey(state.staffPatients.filters, state.staffPatients.offset)] ?? ''
export const selectSelectedPatient = (state: RootState) => state.staffPatients.selected ? state.staffPatients.details[state.staffPatients.selected] : undefined
export const selectSelectedPatientLoading = (state: RootState) => state.staffPatients.selected ? state.staffPatients.detailLoading[state.staffPatients.selected] ?? false : false
export const selectSelectedPatientError = (state: RootState) => state.staffPatients.selected ? state.staffPatients.detailErrors[state.staffPatients.selected] ?? '' : ''
export default staffPatientsSlice.reducer
