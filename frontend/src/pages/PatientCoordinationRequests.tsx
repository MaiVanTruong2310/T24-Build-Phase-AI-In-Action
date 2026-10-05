import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchWithAuth } from '../app/apiClient'
import { PatientUpdates } from '../features/coordinator/PatientUpdates'
import { statuses, dateTime } from '../features/coordinator/api'
interface Receipt { id: string; session_id: string | null; status: string; created_at: string; name: string | null; plan: Record<string, string> }
export default function PatientCoordinationRequests() {
  const [items, setItems] = useState<Receipt[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    const controller = new AbortController()
    const load = async () => {
      try {
        const response = await fetchWithAuth('/coordination/live/mine', { signal: controller.signal })
        const value = await response.json()
        if (!response.ok) throw new Error(value.message || 'Không thể tải phiếu.')
        if (!stopped) { setItems(value.data); setError(''); setLoading(false) }
      } catch (e) { if (!stopped) { setError(e instanceof Error ? e.message : 'Không thể kết nối.'); setLoading(false) } }
      finally { if (!stopped) timer = setTimeout(load, 5000) }
    }
    void load()
    return () => { stopped = true; clearTimeout(timer); controller.abort() }
  }, [])
  return <div className="mx-auto max-w-4xl space-y-5 p-5 text-slate-800"><header><h1 className="text-xl font-semibold">Phiếu đăng ký và điều phối</h1><p className="mt-2 text-sm text-slate-600">Theo dõi phương án khám, hướng dẫn cọc và xác nhận từ điều phối viên. Khách chưa đăng nhập cần dùng trình duyệt đã gửi phiếu.</p><Link to="/patient/appointments" className="mt-3 inline-block text-sm underline">Đăng ký khám</Link></header>{error && <p role="alert">{error}</p>}{loading && <p>Đang tải phiếu…</p>}{!loading && !items.length && <p>Chưa có phiếu điều phối trong phiên này.</p>}{items.map(item => <section key={item.id} className="rounded border border-slate-200 bg-white p-5"><h2 className="font-semibold">{item.name || 'Phiếu đăng ký'} · {item.id.slice(0, 8).toUpperCase()}</h2><p className="mt-2 text-sm">{statuses[item.status] || item.status} · {dateTime(item.created_at)}</p>{item.plan.starts_at && <p className="mt-2 text-sm">Giờ khám: {dateTime(item.plan.starts_at)}{item.status !== 'confirmed' && item.status !== 'completed' ? ' (chưa xác nhận)' : ''}</p>}{item.session_id && <PatientUpdates canReply sessionId={item.session_id} owner={item.id} />}</section>)}</div>
}
