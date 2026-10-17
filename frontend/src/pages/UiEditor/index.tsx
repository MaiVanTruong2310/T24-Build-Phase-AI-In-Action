import { useEffect, useState } from 'react'
import { Eye, EyeOff, Lock, RotateCw } from 'lucide-react'
import { UI_PAGES, UI_REGISTRY, type UiEntry, type UiPageId } from '../../features/uiVisibility/registry'
import { isUiHidden, refreshUiVisibility, setUiVisibility, UI_CHANGED_MESSAGE, useUiVersion } from '../../features/uiVisibility/store'

type PreviewRole = 'guest' | 'patient'

// Trang admin: xem trang người dùng thật trong iframe (chế độ sửa) + bảng công tắc theo từng trang.
export default function UiEditor() {
  useUiVersion()
  const [pageId, setPageId] = useState<UiPageId>('home')
  const [role, setRole] = useState<PreviewRole>('guest')
  const [frameKey, setFrameKey] = useState(0)
  const [busyKey, setBusyKey] = useState('')
  const [error, setError] = useState('')
  const page = UI_PAGES.find((item) => item.id === pageId) ?? UI_PAGES[0]
  const entries: readonly UiEntry[] = UI_REGISTRY.filter((entry) => entry.page === pageId)
  const hiddenCount = (id: UiPageId) => UI_REGISTRY.filter((entry) => entry.page === id && isUiHidden(entry.id)).length

  useEffect(() => {
    void refreshUiVisibility()
    // Công tắc bấm trong iframe → cập nhật bảng bên trái.
    const onMessage = (event: MessageEvent) => {
      if (event.origin === window.location.origin && event.data?.type === UI_CHANGED_MESSAGE) void refreshUiVisibility()
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

  const toggle = async (entry: UiEntry) => {
    setBusyKey(entry.id)
    setError('')
    try {
      await setUiVisibility(entry.id, isUiHidden(entry.id))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Không lưu được.')
    } finally {
      setBusyKey('')
    }
  }

  const src = `${page.path}?ui-edit=1&ui-role=${role}`

  return <div className="flex flex-col gap-4 p-4 lg:h-[calc(100dvh-4rem)] lg:flex-row lg:p-5">
    <aside className="flex min-h-0 shrink-0 flex-col gap-4 lg:w-80" aria-label="Bảng ẩn/hiện thành phần">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">Ẩn/hiện giao diện người dùng</h1>
        <p className="mt-1 text-sm text-slate-500">Bật/tắt áp dụng ngay cho mọi người dùng. Thành phần an toàn được khoá, luôn hiển thị.</p>
      </div>

      <div role="radiogroup" aria-label="Xem như" className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1 text-sm font-medium">
        {(['guest', 'patient'] as const).map((value) => <button key={value} type="button" role="radio" aria-checked={role === value}
          onClick={() => setRole(value)}
          className={`rounded-lg px-3 py-1.5 ${role === value ? 'bg-white text-emerald-800 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>
          {value === 'guest' ? 'Xem như khách' : 'Xem như bệnh nhân'}
        </button>)}
      </div>

      <label className="block text-sm font-medium text-slate-700">Trang
        <select value={pageId} onChange={(event) => setPageId(event.target.value as UiPageId)}
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
          {UI_PAGES.map((item) => {
            const count = hiddenCount(item.id)
            return <option key={item.id} value={item.id}>{item.label}{count ? ` (${count} đang ẩn)` : ''}</option>
          })}
        </select>
      </label>
      {page.note && <p className="-mt-2 text-xs text-slate-500">{page.note}</p>}

      {error && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}

      <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-2">
        {entries.map((entry) => {
          const hidden = !entry.locked && isUiHidden(entry.id)
          return <li key={entry.id}>
            <button type="button" disabled={entry.locked || busyKey === entry.id} onClick={() => void toggle(entry)}
              role="switch" aria-checked={!hidden} title={entry.locked ? entry.reason : `Bấm để ${hidden ? 'hiện' : 'ẩn'}`}
              className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:hover:bg-transparent">
              <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-white ${entry.locked ? 'bg-slate-400' : hidden ? 'bg-rose-600' : 'bg-emerald-600'}`}>
                {entry.locked ? <Lock size={14} aria-hidden="true" /> : hidden ? <EyeOff size={14} aria-hidden="true" /> : <Eye size={14} aria-hidden="true" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className={`block truncate ${hidden ? 'text-slate-400 line-through' : 'text-slate-800'}`}>{entry.label}</span>
                <span className="block text-xs text-slate-500">{entry.locked ? entry.reason : hidden ? 'Đang ẩn' : 'Đang hiện'}</span>
              </span>
            </button>
          </li>
        })}
      </ul>
    </aside>

    <section className="flex min-h-[70vh] min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white" aria-label="Xem trước trang người dùng">
      <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2 text-xs text-slate-500">
        <span className="min-w-0 flex-1 truncate">Xem trước: <code>{page.path}</code> · bấm nút trên từng thành phần để bật/tắt</span>
        <button type="button" onClick={() => setFrameKey((value) => value + 1)} className="inline-flex items-center gap-1 rounded-md px-2 py-1 hover:bg-slate-100">
          <RotateCw size={14} aria-hidden="true" /> Tải lại
        </button>
      </div>
      <iframe key={`${src}#${frameKey}`} src={src} title="Xem trước trang người dùng" className="min-h-0 w-full flex-1 border-0" />
    </section>
  </div>
}
