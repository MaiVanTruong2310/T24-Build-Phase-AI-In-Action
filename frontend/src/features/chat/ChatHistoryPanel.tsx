import { useEffect, useState } from 'react';
import { LoaderCircle, Trash2 } from 'lucide-react';
import { deleteConversation, getConversations, type SavedConversation } from './api';

interface Props {
  activeSessionId: string;
  patientProfileId?: string;
  onSelect: (id: string) => void;
  onDeleted: (id: string) => void;
  onDeletingChange: (value: boolean) => void;
  busy?: boolean;
}

export function ChatHistoryPanel({ patientProfileId, activeSessionId, onSelect, onDeleted, onDeletingChange, busy = false }: Props) {
  const [items, setItems] = useState<SavedConversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [more, setMore] = useState(false);
  const [reload, setReload] = useState(0);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    getConversations(0, controller.signal, patientProfileId).then(data => { if (!controller.signal.aborted) { setItems(data.conversations); setMore(data.has_more); } })
      .catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Không thể tải lịch sử.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [reload, patientProfileId]);
  const locked = loading || busy || deleting !== null;
  async function loadMore() {
    setLoading(true); setError('');
    try { const data = await getConversations(items.length, undefined, patientProfileId); setItems(current => [...current, ...data.conversations]); setMore(data.has_more); }
    catch (e) { setError(e instanceof Error ? e.message : 'Không thể tải lịch sử.'); }
    finally { setLoading(false); }
  }
  async function remove(id: string) {
    if (locked) return;
    setDeleting(id); onDeletingChange(true); setError('');
    try {
      await deleteConversation(id);
      setItems(current => current.filter(item => item.session_id !== id));
      setPendingDelete(null);
      onDeleted(id);
    } catch (e) { setError(e instanceof Error ? e.message : 'Không thể xóa cuộc trò chuyện.'); }
    finally { setDeleting(null); onDeletingChange(false); }
  }
  return <div className="max-h-72 overflow-auto border-b border-app-border bg-app-page p-3 text-app-text">
    <h4 className="mb-2 text-xs font-semibold">Lịch sử trò chuyện của bạn</h4>
    {error && <p role="alert" className="mb-2 text-xs text-red-700 dark:text-red-300">{error}<button type="button" disabled={locked} className="ml-2 underline disabled:opacity-50" onClick={() => setReload(value => value + 1)}>Thử tải lại</button></p>}
    {!loading && !error && items.length === 0 && <p className="text-xs text-app-secondary">Chưa có cuộc trò chuyện được lưu.</p>}
    <ul className="space-y-2">{items.map(item => <li key={item.session_id} className="rounded-lg border border-app-border bg-app-surface">
      <div className="flex items-center gap-1 p-1">
        <button type="button" disabled={locked} onClick={() => onSelect(item.session_id)} aria-current={item.session_id === activeSessionId ? 'true' : undefined}
          className={`min-w-0 flex-1 rounded-md px-2 py-2 text-left text-xs disabled:opacity-60 ${item.session_id === activeSessionId ? 'bg-app-tint text-app-primary' : 'hover:bg-app-muted'}`}>
          <span className="block truncate font-medium">{item.title}</span><time className="mt-1 block text-[10px] text-app-secondary">{new Date(item.updated_at).toLocaleString('vi-VN')}</time>
        </button>
        <button type="button" disabled={locked} onClick={() => setPendingDelete(item.session_id)} aria-label={`Xóa cuộc trò chuyện: ${item.title}`} title="Xóa cuộc trò chuyện"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-app-secondary hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950/50 dark:hover:text-red-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:opacity-40">
          {deleting === item.session_id ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
        </button>
      </div>
      {pendingDelete === item.session_id && <div className="border-t border-app-border p-3 text-xs" role="group" aria-label="Xác nhận xóa cuộc trò chuyện">
        <p>Xóa cuộc trò chuyện này? Không thể khôi phục lịch sử đã xóa.</p>
        <p className="mt-1 text-app-secondary">Phiếu khám và hồ sơ điều phối liên quan vẫn được giữ.</p>
        <div className="mt-3 flex justify-end gap-2"><button type="button" disabled={deleting !== null} onClick={() => setPendingDelete(null)} className="rounded-md border border-app-border px-3 py-2 hover:bg-app-muted disabled:opacity-50">Giữ lại</button>
          <button type="button" disabled={locked} onClick={() => void remove(item.session_id)} className="rounded-md bg-red-700 px-3 py-2 font-semibold text-white hover:bg-red-800 disabled:opacity-50">{deleting === item.session_id ? 'Đang xóa…' : 'Xóa cuộc trò chuyện'}</button></div>
      </div>}
    </li>)}</ul>
    {loading && <p role="status" className="mt-2 text-xs text-app-secondary">Đang tải lịch sử…</p>}
    {more && <button type="button" disabled={locked} onClick={loadMore} className="mt-2 text-xs text-app-primary disabled:opacity-50">Xem thêm cuộc trò chuyện</button>}
  </div>;
}
