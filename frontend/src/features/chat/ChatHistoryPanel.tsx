import { useEffect, useState } from 'react';
import { getConversations, type SavedConversation } from './api';

export function ChatHistoryPanel({ activeSessionId, onSelect }: { activeSessionId: string; onSelect: (id: string) => void }) {
  const [items, setItems] = useState<SavedConversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [more, setMore] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    getConversations(0, controller.signal).then(data => { if (!controller.signal.aborted) { setItems(data.conversations); setMore(data.has_more); } })
      .catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Không thể tải lịch sử.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [reload]);
  async function loadMore() {
    setLoading(true); setError('');
    try { const data = await getConversations(items.length); setItems([...items, ...data.conversations]); setMore(data.has_more); }
    catch (e) { setError(e instanceof Error ? e.message : 'Không thể tải lịch sử.'); }
    finally { setLoading(false); }
  }
  return <div className="max-h-64 overflow-auto border-b border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900">
    <h4 className="mb-2 text-xs font-semibold text-slate-700 dark:text-slate-200">Lịch sử trò chuyện của bạn</h4>
    {error && <p role="alert" className="mb-2 text-xs text-red-600">{error}<button className="ml-2 underline" onClick={() => setReload(value => value + 1)}>Thử lại</button></p>}
    {!loading && !error && items.length === 0 && <p className="text-xs text-slate-500">Chưa có cuộc trò chuyện được lưu.</p>}
    <ul className="space-y-1">{items.map(item => <li key={item.session_id}><button type="button" onClick={() => onSelect(item.session_id)} aria-current={item.session_id === activeSessionId ? 'true' : undefined} className={`w-full rounded-lg px-3 py-2 text-left text-xs ${item.session_id === activeSessionId ? 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-200' : 'text-slate-700 hover:bg-white dark:text-slate-200 dark:hover:bg-slate-800'}`}><span className="block truncate font-medium">{item.title}</span><time className="mt-1 block text-[10px] text-slate-400">{new Date(item.updated_at).toLocaleString('vi-VN')}</time></button></li>)}</ul>
    {loading && <p className="mt-2 text-xs text-slate-500">Đang tải lịch sử…</p>}
    {more && <button type="button" disabled={loading} onClick={loadMore} className="mt-2 text-xs text-blue-600">Xem thêm cuộc trò chuyện</button>}
  </div>;
}
