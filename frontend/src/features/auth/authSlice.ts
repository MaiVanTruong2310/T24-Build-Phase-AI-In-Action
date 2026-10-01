import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../../app/store'
import { fetchWithAuth } from '../../app/apiClient'
import {
  clearSession,
  publishSession,
  readAccessToken,
  readRefreshToken,
  saveTokens,
  type SessionUser,
} from './session'

export interface User {
  id: string;
  email?: string | null;
  phone?: string | null;
  full_name: string;
  role: 'patient' | 'staff';
  token?: string;
  refresh_token?: string;
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

function toUser(profile: SessionUser, accessToken = readAccessToken(), refreshToken = readRefreshToken()): User {
  return {
    ...profile,
    token: accessToken || undefined,
    refresh_token: refreshToken || undefined,
  };
}

function toSessionUser(profile: User): SessionUser {
  return {
    id: profile.id,
    email: profile.email,
    phone: profile.phone,
    full_name: profile.full_name,
    role: profile.role,
  };
}

export const initializeAuth = createAsyncThunk(
  'auth/initializeAuth',
  async (_, { rejectWithValue }) => {
    if (!readAccessToken() && !readRefreshToken()) {
      return null;
    }

    try {
      const response = await fetchWithAuth('/users/me');
      if (!response.ok) {
        return rejectWithValue('Session expired');
      }

      const payload = await response.json();
      const profile = payload?.data as SessionUser | undefined;
      if (!profile?.id || !profile.role) {
        return rejectWithValue('Invalid session profile');
      }

      const user = toUser(profile);
      publishSession(toSessionUser(user));
      return user;
    } catch {
      return rejectWithValue('Unable to restore session');
    }
  },
);

export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials: { username: string; password?: string; otp_code?: string }, { rejectWithValue }) => {
    let tokensSaved = false;
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

      const response = await fetchWithAuth('/auth/login', {
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

      const token = data?.data?.access_token;
      const refresh_token = data?.data?.refresh_token;
      if (typeof token !== 'string' || typeof refresh_token !== 'string') {
        throw new Error('Login response did not contain valid tokens');
      }

      // Save the new pair before fetching the profile so subsequent requests
      // cannot use a stale access token from localStorage.
      saveTokens(token, refresh_token);
      tokensSaved = true;

      const userRes = await fetchWithAuth('/users/me');
      const userData = await userRes.json();
      
      if (!userRes.ok) {
        throw new Error(translateError(userData.message) || 'Không thể lấy thông tin người dùng');
      }

      const user = {
        id: userData.data.id,
        email: userData.data.email,
        phone: userData.data.phone,
        full_name: userData.data.full_name || 'Người dùng',
        role: userData.data.role,
        token: token,
        refresh_token: refresh_token
      } as User;
      publishSession(toSessionUser(user));
      return user;
    } catch (err: unknown) {
      if (tokensSaved) {
        clearSession();
      }
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
      const refresh_token = readRefreshToken() || state.auth.user?.refresh_token;
      
      if (!refresh_token) {
        clearSession();
        return true; // nothing to logout
      }

      const response = await fetchWithAuth('/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token })
      });
      
      if (!response.ok) {
        // Even if it fails, we should clear the local state
        console.warn('Logout API failed');
      }
      clearSession();
      return true;
    } catch (err: unknown) {
      console.warn(getErrorMessage(err, 'Logout request failed'));
      clearSession();
      return true;
    }
  }
)

export const registerUser = createAsyncThunk(
  'auth/registerUser',
  async (userData: RegistrationPayload, { rejectWithValue }) => {
    try {
      const response = await fetchWithAuth('/auth/register', {
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

export const sendOtp = createAsyncThunk(
  'auth/sendOtp',
  async (
    data: { email?: string; phone?: string; purpose?: 'register' | 'login' | 'reset_password' },
    { rejectWithValue },
  ) => {
    try {
      const payload: Record<string, string> = { purpose: data.purpose || 'register' };
      if (data.email) payload.email = data.email;
      if (data.phone) payload.phone = data.phone;

      const response = await fetchWithAuth('/auth/otp/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const responseData = await response.json();
      if (!response.ok) {
        throw new Error(translateError(responseData.message) || 'Không thể lấy mã OTP');
      }

      return responseData.data as { otp?: string | null };
    } catch (err: unknown) {
      return rejectWithValue(getErrorMessage(err, 'Không thể lấy mã OTP'));
    }
  },
);

export const verifyOtp = createAsyncThunk(
  'auth/verifyOtp',
  async (data: { email?: string; phone?: string; code: string }, { rejectWithValue }) => {
    try {
      const payload: Record<string, string> = { purpose: 'register', code: data.code };
      if (data.email) payload.email = data.email;
      if (data.phone) payload.phone = data.phone;
      
      const response = await fetchWithAuth('/auth/otp/verify', {
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
      const response = await fetchWithAuth('/auth/forgot-password', {
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

      const response = await fetchWithAuth('/auth/reset-password', {
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
    sessionChanged: (state, action: PayloadAction<SessionUser | null>) => {
      state.user = action.payload ? toUser(action.payload) : null
      state.error = null
    },
    resetRegisterSuccess: (state) => {
      state.registerSuccess = false
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(initializeAuth.pending, (state) => {
        state.loading = true
      })
      .addCase(initializeAuth.fulfilled, (state, action) => {
        state.loading = false
        state.user = action.payload
      })
      .addCase(initializeAuth.rejected, (state) => {
        state.loading = false
        state.user = null
      })
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

export const { logout, sessionChanged, resetRegisterSuccess } = authSlice.actions
export default authSlice.reducer
