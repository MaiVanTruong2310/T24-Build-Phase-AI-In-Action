import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

export interface User {
  id: string;
  name: string;
  role: 'patient' | 'staff';
  token: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  loading: false,
  error: null,
}

// Mock API Call
export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials: { username: string; password: string }, { rejectWithValue }) => {
    try {
      // Simulate network request latency
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      // Basic validation mock
      if (!credentials.username || !credentials.password) {
        throw new Error('Vui lòng nhập đầy đủ thông tin')
      }
      
      if (credentials.password !== '123456') { // Mock failure condition
        throw new Error('Tài khoản hoặc mật khẩu không chính xác (Thử mật khẩu: 123456)')
      }

      return {
        id: 'user-1',
        name: 'Nguyễn Văn A',
        role: 'patient',
        token: 'mock-jwt-token'
      } as User
    } catch (err: any) {
      return rejectWithValue(err.message || 'Đăng nhập thất bại')
    }
  }
)

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      state.user = null
      state.error = null
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false
        state.user = action.payload
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
  },
})

export const { logout } = authSlice.actions
export default authSlice.reducer
