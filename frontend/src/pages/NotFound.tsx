import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-5 text-center">
      <section aria-labelledby="not-found-title" className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">404</p>
        <h1 id="not-found-title" className="mt-2 text-2xl font-bold text-slate-900">Không tìm thấy trang</h1>
        <p className="mt-2 text-sm text-slate-600">Đường dẫn này không tồn tại hoặc đã được thay đổi.</p>
        <Link to="/" className="mt-6 inline-flex rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:ring-offset-2">
          Về trang chủ
        </Link>
      </section>
    </main>
  )
}
