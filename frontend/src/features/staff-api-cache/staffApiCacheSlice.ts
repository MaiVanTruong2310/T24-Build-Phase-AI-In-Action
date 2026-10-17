import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import type { CachedApiResponse } from '../../app/apiResponseCacheBridge'
import { loginUser, logout, logoutUser, sessionChanged } from '../auth/authSlice'

interface StaffApiCacheState {
  entries: Record<string, CachedApiResponse>
}

const initialState: StaffApiCacheState = { entries: {} }

const staffApiCacheSlice = createSlice({
  name: 'staffApiCache',
  initialState,
  reducers: {
    cacheApiResponse(state, action: PayloadAction<CachedApiResponse>) {
      state.entries[action.payload.key] = action.payload
      const keys = Object.keys(state.entries)
      if (keys.length > 150) delete state.entries[keys[0]]
    },
    removeCachedApiResponse(state, action: PayloadAction<string>) {
      delete state.entries[action.payload]
    },
    clearApiResponseCache() {
      return initialState
    },
  },
  extraReducers: builder => {
    builder
      .addCase(loginUser.fulfilled, () => initialState)
      .addCase(logout, () => initialState)
      .addCase(logoutUser.fulfilled, () => initialState)
      .addCase(sessionChanged, () => initialState)
  },
})

export const { cacheApiResponse, removeCachedApiResponse, clearApiResponseCache } = staffApiCacheSlice.actions
export default staffApiCacheSlice.reducer
