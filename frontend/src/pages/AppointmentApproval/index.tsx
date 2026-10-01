import { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { PendingBooking } from './api';
import { approveBooking, fetchPendingBookings, rejectBooking } from './api';
import type { TabFilter } from './components/constants';
import { PageHeader } from './components/PageHeader';
import { FilterBar } from './components/FilterBar';
import { BookingList } from './components/BookingList';
import { PageFooter } from './components/PageFooter';

export default function AppointmentApproval() {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState<PendingBooking[]>([]);
  const [activeTab, setActiveTab] = useState<TabFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'time' | 'risk'>('time');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);
  const [reviewTarget, setReviewTarget] = useState<{ id: string; status: 'rejected' } | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [error, setError] = useState('');

  const loadBookings = useCallback(async () => {
    setIsRefreshing(true);
    setError('');
    try {
      setBookings(await fetchPendingBookings());
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Không thể tải danh sách lịch hẹn.');
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadBookings();
  }, [loadBookings]);

  /* ── Derived counts ── */
  const counts = useMemo(() => {
    const pending = bookings.filter(b => b.status === 'pending_approval').length;
    const confirmed = bookings.filter(b => b.status === 'confirmed').length;
    const rejected = bookings.filter(b => b.status === 'rejected').length;
    const cancelled = bookings.filter(b => b.status === 'cancelled').length;
    const expired = bookings.filter(b => b.status === 'expired').length;
    return { all: bookings.length, pending_approval: pending, confirmed, rejected, cancelled, expired };
  }, [bookings]);

  /* ── Filter + sort ── */
  const filtered = useMemo(() => {
    let list = bookings;

    if (activeTab !== 'all') {
      list = list.filter(b => b.status === activeTab);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        b =>
          b.patient_name.toLowerCase().includes(q) ||
          b.booking_code.toLowerCase().includes(q) ||
          b.doctor_name.toLowerCase().includes(q) ||
          b.specialty_name.toLowerCase().includes(q),
      );
    }

    list = [...list].sort((a, b) => {
      if (sortBy === 'risk') {
        const riskOrder = { critical: 0, high: 1, medium: 2, low: 3 };
        const ra = riskOrder[a.triage?.risk_level ?? 'low'] ?? 3;
        const rb = riskOrder[b.triage?.risk_level ?? 'low'] ?? 3;
        if (ra !== rb) return ra - rb;
      }
      return new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime();
    });

    return list;
  }, [bookings, activeTab, searchQuery, sortBy]);

  /* ── Handlers ── */
  const handleRefresh = useCallback(() => {
    void loadBookings();
  }, [loadBookings]);

  const handleOpenDetail = useCallback(
    (id: string) => navigate(`/staff/appointments/approve/${id}`),
    [navigate],
  );

  const handleToggleExpand = useCallback(
    (id: string) => setExpandedId(prev => (prev === id ? null : id)),
    [],
  );

  const replaceBooking = useCallback((updated: PendingBooking) => {
    setBookings(current => current.map(item => (item.id === updated.id ? updated : item)));
  }, []);

  const handleApprove = useCallback(async (id: string) => {
    setActionId(id);
    setError('');
    try {
      replaceBooking(await approveBooking(id));
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Không thể duyệt lịch hẹn.');
    } finally {
      setActionId(null);
    }
  }, [replaceBooking]);

  const handleReject = useCallback(async (id: string) => {
    setReviewTarget({ id, status: 'rejected' });
    setReviewNote('');
  }, []);

  const confirmReject = useCallback(async () => {
    if (!reviewTarget || !reviewNote.trim()) return;
    const id = reviewTarget.id;
    setActionId(id);
    setError('');
    try {
      replaceBooking(await rejectBooking(id, reviewNote.trim()));
      setReviewTarget(null);
      setReviewNote('');
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Không thể từ chối lịch hẹn.');
    } finally {
      setActionId(null);
    }
  }, [replaceBooking, reviewNote, reviewTarget]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <PageHeader
        counts={counts}
        isRefreshing={isRefreshing}
        onRefresh={handleRefresh}
      />

      {error && <div role="alert" className="mx-6 mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <FilterBar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        sortBy={sortBy}
        onSortToggle={() => setSortBy(s => (s === 'time' ? 'risk' : 'time'))}
        counts={counts}
      />

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
        <BookingList
          bookings={filtered}
          isRefreshing={isRefreshing}
          expandedId={expandedId}
          onToggleExpand={handleToggleExpand}
          onOpenDetail={handleOpenDetail}
          onApprove={handleApprove}
          onReject={handleReject}
          actionId={actionId}
        />
      </div>

      <PageFooter
        filteredCount={filtered.length}
        totalCount={bookings.length}
      />

      {reviewTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <h2 className="text-lg font-bold text-slate-900">Từ chối lịch hẹn</h2>
            <p className="mt-2 text-sm text-slate-600">Vui lòng nhập lý do để bệnh nhân có thể biết hướng xử lý tiếp theo.</p>
            <textarea
              autoFocus
              value={reviewNote}
              onChange={(event) => setReviewNote(event.target.value)}
              maxLength={2000}
              rows={4}
              className="mt-4 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              placeholder="Lý do từ chối"
            />
            <div className="mt-4 flex justify-end gap-3">
              <button onClick={() => setReviewTarget(null)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Huỷ</button>
              <button onClick={() => void confirmReject()} disabled={!reviewNote.trim() || Boolean(actionId)} className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">Xác nhận từ chối</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
