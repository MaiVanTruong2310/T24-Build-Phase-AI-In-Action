import { useEffect, useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { fetchPublicApi } from '../app/apiClient'

export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState(() => {
    const p = new URLSearchParams(window.location.hash.slice(1))
    return p.get('type') === 'recovery' ? p.get('access_token') || '' : ''
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [done, setDone] = useState(false)
  useEffect(() => {
    const p = new URLSearchParams(window.location.hash.slice(1))
    if (p.get('error')) setError('Liên kết khôi phục đã hết hạn hoặc không hợp lệ. Vui lòng yêu cầu gửi lại.')
    if (p.has('access_token') || p.has('error')) window.history.replaceState(null, '', window.location.pathname + window.location.search)
  }, [])
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError(''); setNotice('')
    if (token ? password.length < 8 || password.length > 128 : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError(token ? 'Mật khẩu phải từ 8 đến 128 ký tự.' : 'Vui lòng nhập email đăng ký.'); return
    }
    setBusy(true)
    try {
      const response = await fetchPublicApi(token ? '/auth/password' : '/auth/forgot-password', {
        method: token ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(token ? { new_password: password } : { email: email.trim() }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || data.detail || 'Không thể xử lý yêu cầu.')
      if (token) { setDone(true); setToken(''); setPassword('') }
      setNotice(token ? 'Đã đổi mật khẩu. Vui lòng đăng nhập lại.' : 'Nếu tài khoản tồn tại, liên kết khôi phục sẽ được gửi qua email. Hãy kiểm tra cả mục Spam.')
    } catch (e) { setError(e instanceof TypeError ? 'Không thể kết nối máy chủ. Vui lòng thử lại sau.' : e instanceof Error ? e.message : 'Có lỗi xảy ra.') }
    finally { setBusy(false) }
  }
  return <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-xl dark:bg-slate-900">
    <h2 className="mb-4 text-xl font-bold">Khôi phục mật khẩu bằng email</h2>
    {error && <p role="alert" className="mb-4 text-sm text-red-600">{error}</p>}
    {notice && <p role="status" className="mb-4 text-sm text-green-700">{notice}</p>}
    {!done && <form onSubmit={submit} className="space-y-4">
      <label className="block text-sm">{token ? 'Mật khẩu mới' : 'Email đã đăng ký'}
        <input required type={token ? 'password' : 'email'} value={token ? password : email} onChange={e => token ? setPassword(e.target.value) : setEmail(e.target.value)} autoComplete={token ? 'new-password' : 'email'} className="mt-2 w-full rounded-xl border p-3 dark:bg-slate-950" />
      </label>
      <button disabled={busy} className="w-full rounded-xl bg-blue-600 p-3 text-white disabled:opacity-50">{busy ? 'Đang xử lý…' : token ? 'Đặt lại mật khẩu' : 'Gửi liên kết khôi phục'}</button>
    </form>}
    <Link to="/login" className="mt-5 block text-center text-sm text-blue-600">Quay lại đăng nhập</Link>
  </div>
}
