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
    return { all: bookings.length, pending_approval: pending, confirmed, rejected };
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
    const reason = window.prompt('Nhập lý do từ chối lịch hẹn:')?.trim();
    if (!reason) return;
    setActionId(id);
    setError('');
    try {
      replaceBooking(await rejectBooking(id, reason));
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Không thể từ chối lịch hẹn.');
    } finally {
      setActionId(null);
    }
  }, [replaceBooking]);

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
    </div>
  );
}
