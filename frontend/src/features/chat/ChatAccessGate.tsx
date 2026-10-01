import { useState, type FormEvent } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { MessageCircle, ArrowRight, UserRound } from 'lucide-react';
import { normalizeChatProfile, type ChatProfile } from './profile';

export function ChatAccessGate({ onGuest }: { onGuest: (profile: ChatProfile) => void }) {
  const location = useLocation();
  const [guestMode, setGuestMode] = useState(false);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [error, setError] = useState('');
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const profile = normalizeChatProfile(name, phone);
    if (!profile) {
      setError('Vui lòng nhập tên từ 2–120 ký tự và số điện thoại hợp lệ (9–15 chữ số).');
      return;
    }
    onGuest(profile);
  };
  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center overflow-y-auto bg-slate-100/40 dark:bg-slate-950/40 p-4 backdrop-blur-sm">
      <section aria-label="Bắt đầu trò chuyện" className="w-full max-w-sm rounded-2xl border border-blue-100 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 shadow-xl">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-cyan-300"><MessageCircle className="h-6 w-6" /></div>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Bắt đầu trò chuyện</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">Đăng nhập hoặc cung cấp tên và số điện thoại để trợ lý hỗ trợ bạn trong phiên tư vấn.</p>
        {!guestMode ? (
          <div className="mt-5 space-y-3">
            <Link to={`/login?returnTo=${encodeURIComponent(location.pathname)}`} className="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700">Đăng nhập để chat <ArrowRight className="h-4 w-4" /></Link>
            <button type="button" onClick={() => setGuestMode(true)} className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-3 text-sm font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"><UserRound className="h-4 w-4" />Tiếp tục với tư cách khách</button>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-5 space-y-4">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">Tên của bạn
              <input autoFocus required minLength={2} maxLength={120} autoComplete="name" value={name} onChange={event => setName(event.target.value)} className="mt-1.5 w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2.5 outline-none focus:ring-2 focus:ring-blue-500" placeholder="Ví dụ: Nguyễn Văn An" />
            </label>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">Số điện thoại
              <input required type="tel" maxLength={24} autoComplete="tel" value={phone} onChange={event => setPhone(event.target.value)} className="mt-1.5 w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2.5 outline-none focus:ring-2 focus:ring-blue-500" placeholder="Ví dụ: 0912 345 678" />
            </label>
            <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">Tên và số điện thoại được dùng cho phiên tư vấn này và điền sẵn khi bạn muốn đặt hẹn. Thông tin chưa được xác thực bằng OTP.</p>
            {error && <p role="alert" className="text-xs text-red-600">{error}</p>}
            <button type="submit" className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700">Bắt đầu chat</button>
            <button type="button" onClick={() => setGuestMode(false)} className="w-full text-sm text-slate-500 hover:text-blue-600">Quay lại</button>
          </form>
        )}
      </section>
    </div>
  );
}
