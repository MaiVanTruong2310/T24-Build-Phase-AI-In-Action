import { configureStore, createSlice } from '@reduxjs/toolkit'
import authReducer from '../features/auth/authSlice'

const layoutSlice = createSlice({
  name: 'layout',
  initialState: {
    isChatOpen: false
  },
  reducers: {
    toggleChat: (state) => {
      state.isChatOpen = !state.isChatOpen
    },
    closeChat: (state) => {
      state.isChatOpen = false
    }
  }
})

export const { toggleChat, closeChat } = layoutSlice.actions

export const store = configureStore({
  reducer: {
    layout: layoutSlice.reducer,
    auth: authReducer
  }
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
