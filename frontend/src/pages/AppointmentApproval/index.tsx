import { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { approveBooking, rejectBooking } from './api';
import type { AppDispatch, RootState } from '../../app/store';
import { approvalPageKey, clearBookingApprovalPages, loadBookingApprovalViews } from '../../features/booking-approvals/bookingApprovalsSlice';
import type { TabFilter } from './components/constants';
import { PageHeader } from './components/PageHeader';
import { FilterBar } from './components/FilterBar';
import { BookingList } from './components/BookingList';
import { PageFooter } from './components/PageFooter';

export default function AppointmentApproval() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const approvalState = useSelector((state: RootState) => state.bookingApprovals);
  const [activeTab, setActiveTab] = useState<TabFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [serviceId, setServiceId] = useState('');
  const [offset, setOffset] = useState(0);
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [sortBy, setSortBy] = useState<'updated' | 'time' | 'risk'>('updated');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);
  const [reviewTarget, setReviewTarget] = useState<{ id: string; status: 'rejected' } | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [error, setError] = useState('');

  const pageSize = 20;
  const filters = useMemo(() => ({ q: debouncedQuery || undefined, serviceId: serviceId || undefined, offset, limit: pageSize }), [debouncedQuery, offset, serviceId]);
  const queryKey = approvalPageKey(filters, activeTab);
  const currentPage = approvalState.pages[queryKey];
  const loadingKey = JSON.stringify([debouncedQuery, serviceId, offset, pageSize]);
  const isRefreshing = Boolean(approvalState.loading[loadingKey] && !currentPage);

  useEffect(() => {
    void dispatch(loadBookingApprovalViews(filters));
  }, [dispatch, filters, currentPage]);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(searchQuery.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [searchQuery]);

  /* ── Derived counts ── */
  const counts = currentPage?.status_counts ?? { all: 0, pending_approval: 0, confirmed: 0, rejected: 0 };

  useEffect(() => {
    if (currentPage && offset > 0 && offset >= currentPage.total) {
      setOffset(Math.max(0, Math.floor((currentPage.total - 1) / pageSize) * pageSize));
    }
  }, [currentPage, offset]);

  /* ── Filter + sort ── */
  const filtered = useMemo(() => sortBy === 'updated' ? currentPage?.items ?? [] : [...(currentPage?.items ?? [])].sort((a, b) => {
      if (sortBy === 'risk') {
        const ra = a.ai_triage?.ats_level ?? Number.MAX_SAFE_INTEGER;
        const rb = b.ai_triage?.ats_level ?? Number.MAX_SAFE_INTEGER;
        if (ra !== rb) return ra - rb;
      }
      return new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime();
    }), [currentPage, sortBy]);

  const toggleSort = () => setSortBy(current => current === 'updated' ? 'time' : current === 'time' ? 'risk' : 'updated');

  /* ── Handlers ── */
  const handleRefresh = useCallback(() => {
    void dispatch(loadBookingApprovalViews({ ...filters, force: true }));
  }, [dispatch, filters]);

  const handleOpenDetail = useCallback(
    (id: string) => navigate(`/staff/appointments/approve/${id}`),
    [navigate],
  );

  const handleToggleExpand = useCallback(
    (id: string) => setExpandedId(prev => (prev === id ? null : id)),
    [],
  );

  const handleApprove = async (id: string) => {
    setActionId(id);
    setError('');
    try {
      await approveBooking(id);
      dispatch(clearBookingApprovalPages());
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Không thể duyệt lịch hẹn.');
    } finally {
      setActionId(null);
    }
  };

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
      await rejectBooking(id, reviewNote.trim());
      setReviewTarget(null);
      setReviewNote('');
      dispatch(clearBookingApprovalPages());
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Không thể từ chối lịch hẹn.');
    } finally {
      setActionId(null);
    }
  }, [dispatch, reviewNote, reviewTarget]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <PageHeader
        counts={counts}
        isRefreshing={isRefreshing}
        onRefresh={handleRefresh}
      />

      {(error || approvalState.errors[loadingKey]) && <div role="alert" className="mx-6 mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error || approvalState.errors[loadingKey]}</div>}

      <FilterBar
        activeTab={activeTab}
        onTabChange={tab => { setOffset(0); setActiveTab(tab); }}
        searchQuery={searchQuery}
        onSearchChange={query => { setOffset(0); setSearchQuery(query); }}
        serviceId={serviceId}
        services={approvalState.services}
        onServiceChange={id => { setOffset(0); setServiceId(id); }}
        sortBy={sortBy}
        onSortToggle={toggleSort}
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
        totalCount={currentPage?.total ?? 0}
        offset={offset}
        limit={pageSize}
        onPageChange={setOffset}
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
