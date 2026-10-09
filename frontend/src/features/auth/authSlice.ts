import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../../app/store'
import { fetchWithAuth, fetchPublicApi, migrateLegacySession } from '../../app/apiClient'
import {
  clearSession,
  publishSession,
  readPublishedSession,
  markCookieSession,
  type SessionUser,
} from './session'

export interface User {
  id: string;
  email?: string | null;
  phone?: string | null;
  full_name: string;
  role: 'patient' | 'staff';
  date_of_birth?: string | null;
  gender?: string | null;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  registerSuccess: boolean;
  initialized: boolean;
  restoreError: string | null;
  restoreRequestId: string | null;
}

const cachedSession = readPublishedSession();

const initialState: AuthState = {
  user: cachedSession,
  initialized: false,
  restoreError: null,
  restoreRequestId: null,
  loading: false,
  error: null,
  registerSuccess: false,
}

type RegistrationPayload = Record<string, string | boolean | null | undefined>;

const getErrorMessage = (error: unknown, fallback: string): string =>
  error instanceof TypeError && /fetch|network/i.test(error.message)
    ? 'Không thể kết nối tới máy chủ. Vui lòng thử lại sau.'
    : error instanceof Error ? error.message : fallback;

const translateError = (msg: string | undefined | null): string => {
  if (!msg) return 'Đã xảy ra lỗi.';
  const lower = msg.toLowerCase();
  if (lower.includes('invalid login credentials')) return 'Sai tài khoản hoặc mật khẩu.';
  if (lower.includes('invalid or expired otp')) return 'Mã OTP không hợp lệ hoặc đã hết hạn.';
  if (lower.includes('account already exists')) return 'Tài khoản đã tồn tại trong hệ thống.';
  if (lower.includes('account is not active')) return 'Tài khoản chưa được kích hoạt.';
  if (lower.includes('citizen_id') || lower.includes('cccd')) return 'Số CCCD đã thuộc một hồ sơ khác trong hệ thống.';
  if (lower.includes('health_insurance') || lower.includes('bảo hiểm y tế')) return 'Số thẻ bảo hiểm y tế đã thuộc một hồ sơ khác trong hệ thống.';
  if (lower.includes('phone_exists') || lower.includes('số điện thoại đã thuộc')) return 'Số điện thoại đã thuộc một hồ sơ khác.';
  return msg;
};

function toUser(profile: SessionUser): User {
  return { ...profile };
}

function toSessionUser(profile: User): SessionUser {
  return {
    id: profile.id,
    email: profile.email,
    phone: profile.phone,
    full_name: profile.full_name,
    role: profile.role,
    date_of_birth: profile.date_of_birth,
    gender: profile.gender,
  };
}

export const initializeAuth = createAsyncThunk(
  'auth/initializeAuth',
  async (_, { rejectWithValue }) => {
    const originalUserId = readPublishedSession()?.id;
    try {
      await migrateLegacySession();
      const response = await fetchWithAuth('/users/me');
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          const currentUserId = readPublishedSession()?.id;
          if (currentUserId && currentUserId !== originalUserId) return rejectWithValue({ kind: 'unavailable' });
          clearSession();
          return null;
        }
        return rejectWithValue({ kind: 'unavailable' });
      }
      const payload = await response.json();
      const profile = payload?.data as SessionUser | undefined;
      if (!profile?.id || !profile.role) return rejectWithValue({ kind: 'unavailable' });
      // A response received after logout must not resurrect the old session.
      if (readPublishedSession()?.id !== originalUserId) return rejectWithValue({ kind: 'unavailable' });
      const user = toUser(profile);
      publishSession(toSessionUser(user));
      return user;
    } catch {
      return rejectWithValue({ kind: 'unavailable' });
    }
  },
  { condition: (_, { getState }) => !(getState() as RootState).auth.restoreRequestId },
);

export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials: { username: string; password?: string }, { rejectWithValue }) => {
    let tokensSaved = false;
    try {
      // Supabase Auth owns credentials, so email is the only supported login
      // identity. Phone numbers and coordinator usernames are no longer logins.
      const identity = credentials.username.trim();
      if (!identity.includes('@')) {
        return rejectWithValue('Vui lòng đăng nhập bằng email.')
      }

      const payload: Record<string, string> = { email: identity };

      if (credentials.password) {
        payload.password = credentials.password;
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

      if (data?.data?.authenticated !== true) throw new Error('Không thể tạo phiên đăng nhập.');
      markCookieSession();
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
        date_of_birth: userData.data.date_of_birth || null,
        gender: userData.data.gender || null,
      } as User;
      publishSession(toSessionUser(user));
      return user;
    } catch (err: unknown) {
      if (tokensSaved) {
        return rejectWithValue('Đã tạo phiên đăng nhập nhưng chưa tải được hồ sơ. Vui lòng tải lại trang.');
      }
      return rejectWithValue(getErrorMessage(err, 'Đăng nhập thất bại'));
    }
  }
)

export const logoutUser = createAsyncThunk(
  'auth/logoutUser',
  async (_, { rejectWithValue }) => {
    try {
      // The browser supplies the HttpOnly refresh cookie; JS never reads it.
      await fetchPublicApi('/auth/logout', { method: 'POST' });
      clearSession();
      return true;
    } catch (err: unknown) {
      return rejectWithValue(getErrorMessage(err, 'Chưa thể đăng xuất. Vui lòng thử lại.'));
    }
  },
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

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      state.user = null
      state.error = null
      state.registerSuccess = false
      state.restoreRequestId = null
      state.restoreError = null
      state.initialized = true
      state.loading = false
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
      .addCase(initializeAuth.pending, (state, action) => {
        state.loading = true
        state.restoreError = null
        state.restoreRequestId = action.meta.requestId
      })
      .addCase(initializeAuth.fulfilled, (state, action) => {
        if (state.restoreRequestId !== action.meta.requestId) return
        state.loading = false
        state.initialized = true
        state.restoreRequestId = null
        state.user = action.payload
      })
      .addCase(initializeAuth.rejected, (state, action) => {
        if (state.restoreRequestId !== action.meta.requestId) return
        state.loading = false
        state.initialized = true
        state.restoreRequestId = null
        const failure = action.payload as { kind?: string } | undefined
        if (failure?.kind === 'invalid') state.user = null
        else state.restoreError = 'Kết nối tạm thời gián đoạn. Phiên đăng nhập đã lưu được giữ lại.'
      })
      // Login
      .addCase(loginUser.pending, (state) => {
        state.restoreRequestId = null
        state.restoreError = null
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
      .addCase(logoutUser.pending, (state) => {
        state.restoreRequestId = null
      })
      .addCase(logoutUser.rejected, (state, action) => {
        state.error = action.payload as string
      })
      .addCase(logoutUser.fulfilled, (state) => {
        state.restoreError = null
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
  },
})

export const { logout, sessionChanged, resetRegisterSuccess } = authSlice.actions
export default authSlice.reducer
