import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import type { RootState } from '../../app/store'

export interface User {
  id: string;
  email?: string;
  phone?: string;
  full_name: string;
  role: 'patient' | 'staff';
  token: string;
  refresh_token: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  registerSuccess: boolean;
}

const initialState: AuthState = {
  user: null,
  loading: false,
  error: null,
  registerSuccess: false,
}

const API_BASE = '/api/v1';
type RegistrationPayload = Record<string, string | boolean | null | undefined>;

const getErrorMessage = (error: unknown, fallback: string): string =>
  error instanceof Error ? error.message : fallback;

const translateError = (msg: string | undefined | null): string => {
  if (!msg) return 'Đã xảy ra lỗi.';
  const lower = msg.toLowerCase();
  if (lower.includes('invalid login credentials')) return 'Sai tài khoản hoặc mật khẩu.';
  if (lower.includes('invalid or expired otp')) return 'Mã OTP không hợp lệ hoặc đã hết hạn.';
  if (lower.includes('account already exists')) return 'Tài khoản đã tồn tại.';
  if (lower.includes('account is not active')) return 'Tài khoản chưa được kích hoạt.';
  return msg;
};

export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials: { username: string; password?: string; otp_code?: string }, { rejectWithValue }) => {
    try {
      const isEmail = credentials.username.includes('@');
      
      const payload: Record<string, string> = {
        [isEmail ? 'email' : 'phone']: credentials.username,
      };

      if (credentials.password) {
        payload.password = credentials.password;
      } else if (credentials.otp_code) {
        payload.otp_code = credentials.otp_code;
      }

      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(translateError(data.message) || 'Đăng nhập thất bại');
      }

      const token = data.data.access_token;
      const refresh_token = data.data.refresh_token;
      
      const userRes = await fetch(`${API_BASE}/users/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const userData = await userRes.json();
      
      if (!userRes.ok) {
        throw new Error(translateError(userData.message) || 'Không thể lấy thông tin người dùng');
      }

      // Lưu token vào localStorage
      localStorage.setItem('access_token', token);
      localStorage.setItem('refresh_token', refresh_token);

      return {
        id: userData.data.id,
        email: userData.data.email,
        phone: userData.data.phone,
        full_name: userData.data.full_name || 'Người dùng',
        role: userData.data.role,
        token: token,
        refresh_token: refresh_token
      } as User;
    } catch (err: unknown) {
      return rejectWithValue(getErrorMessage(err, 'Đăng nhập thất bại'));
    }
  }
)

export const logoutUser = createAsyncThunk(
  'auth/logoutUser',
  async (_, { getState }) => {
    try {
      const state = getState() as RootState;
      // Refresh tokens rotate after every successful refresh. Redux may still
      // contain the old value, so prefer the current persisted token.
      const refresh_token = localStorage.getItem('refresh_token') || state.auth.user?.refresh_token;
      
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');

      if (!refresh_token) {
        return true; // nothing to logout
      }

      const response = await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token })
      });
      
      if (!response.ok) {
        // Even if it fails, we should clear the local state
        console.warn('Logout API failed');
      }
      return true;
    } catch (err: unknown) {
      console.warn(getErrorMessage(err, 'Logout request failed'));
      return true;
    }
  }
)

export const registerUser = createAsyncThunk(
  'auth/registerUser',
  async (userData: RegistrationPayload, { rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData)
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(translateError(data.message) || 'Đăng ký thất bại');
      }

      return data.data;
    } catch (err: unknown) {
      return rejectWithValue(getErrorMessage(err, 'Đăng ký thất bại'));
    }
  }
)

export const verifyOtp = createAsyncThunk(
  'auth/verifyOtp',
  async (data: { email?: string; phone?: string; code: string }, { rejectWithValue }) => {
    try {
      const payload: Record<string, string> = { purpose: 'register', code: data.code };
      if (data.email) payload.email = data.email;
      if (data.phone) payload.phone = data.phone;
      
      const response = await fetch(`${API_BASE}/auth/otp/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const resData = await response.json();
      if (!response.ok) {
        throw new Error(translateError(resData.message) || 'Xác thực OTP thất bại');
      }
      return resData.data;
    } catch (err: unknown) {
      return rejectWithValue(getErrorMessage(err, 'Xác thực OTP thất bại'));
    }
  }
)

export const requestPasswordReset = createAsyncThunk(
  'auth/requestPasswordReset',
  async (username: string, { rejectWithValue }) => {
    try {
      const isEmail = username.includes('@');
      const payload = isEmail ? { email: username } : { phone: username };
      const response = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(translateError(data.message) || 'Yêu cầu thất bại');
      return data.data;
    } catch (err: unknown) {
      return rejectWithValue(getErrorMessage(err, 'Yêu cầu thất bại'));
    }
  }
)

export const resetPassword = createAsyncThunk(
  'auth/resetPassword',
  async (data: { username: string; code: string; new_password: string }, { rejectWithValue }) => {
    try {
      const isEmail = data.username.includes('@');
      const payload: Record<string, string> = { code: data.code, new_password: data.new_password };
      if (isEmail) payload.email = data.username;
      else payload.phone = data.username;

      const response = await fetch(`${API_BASE}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const resData = await response.json();
      if (!response.ok) throw new Error(translateError(resData.message) || 'Đặt lại mật khẩu thất bại');
      return resData.data;
    } catch (err: unknown) {
      return rejectWithValue(getErrorMessage(err, 'Đặt lại mật khẩu thất bại'));
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
      state.registerSuccess = false
    },
    resetRegisterSuccess: (state) => {
      state.registerSuccess = false
    }
  },
  extraReducers: (builder) => {
    builder
      // Login
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
      // Logout
      .addCase(logoutUser.fulfilled, (state) => {
        state.user = null
        state.error = null
        state.registerSuccess = false
      })
      // Register
      .addCase(registerUser.pending, (state) => {
        state.loading = true
        state.error = null
        state.registerSuccess = false
      })
      .addCase(registerUser.fulfilled, (state) => {
        state.loading = false
        state.registerSuccess = true
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      // Verify OTP
      .addCase(verifyOtp.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(verifyOtp.fulfilled, (state) => {
        state.loading = false
      })
      .addCase(verifyOtp.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      // Request Password Reset
      .addCase(requestPasswordReset.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(requestPasswordReset.fulfilled, (state) => {
        state.loading = false
      })
      .addCase(requestPasswordReset.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      // Reset Password
      .addCase(resetPassword.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(resetPassword.fulfilled, (state) => {
        state.loading = false
      })
      .addCase(resetPassword.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
  },
})

export const { logout, resetRegisterSuccess } = authSlice.actions
export default authSlice.reducer
