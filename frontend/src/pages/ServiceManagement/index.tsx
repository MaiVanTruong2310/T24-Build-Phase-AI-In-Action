import { DataLoadingState } from '../../components/DataLoadingState';
import React, { useEffect, useMemo, useState } from 'react';
import { Header } from './Header';
import { Stats } from './Stats';
import { FilterBar } from './FilterBar';
import { ServiceFilters } from './FilterBar';
import { filterServices } from './filterServices';
import { exportServicesCsv } from './exportServicesCsv';
import { ServiceGrid } from './ServiceGrid';
import { RemoteData, notAsked, loading, success, failure, foldRemoteData } from './types';
import { fetchServices, Service } from './api';

const EMPTY_SERVICES: Service[] = [];
const PAGE_SIZE = 24;

function enrichServices(services: Service[]): Service[] {
  return services.map(service => ({
    ...service,
    price: service.price,
    original_price: service.original_price,
    category: service.category,
    patient_count: service.patient_count,
    satisfaction_rate: service.satisfaction_rate,
    features: service.features ?? [],
  }));
}

export default function ServiceManagement() {
  const [servicesState, setServicesState] = useState<RemoteData<Error, Service[]>>(notAsked());
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState<Error | null>(null);
  const [filters, setFilters] = useState<ServiceFilters>({ search: '', category: '', priceRange: '', status: '' });
  const services = servicesState._tag === 'Success' ? servicesState.value : EMPTY_SERVICES;
  const categories = useMemo(() => [...new Set(services.map(service => service.category).filter((category): category is string => Boolean(category)))].sort(), [services]);
  const filteredServices = useMemo(() => filterServices(services, filters), [services, filters]);

  const loadServices = async () => {
    setServicesState(loading());
    const result = await fetchServices(0, PAGE_SIZE)();

    if (result._tag === 'Right') {
      // Preserve API values; optional fields are rendered as unavailable.
      const page = enrichServices(result.right);
      setServicesState(success(page));
      setHasMore(page.length === PAGE_SIZE);

    } else {
      setServicesState(failure(result.left));
    }
  };
  const loadMoreServices = async () => {
    if (servicesState._tag !== 'Success' || loadingMore || !hasMore) return;
    setLoadingMore(true);
    setLoadMoreError(null);
    const result = await fetchServices(servicesState.value.length, PAGE_SIZE)();
    if (result._tag === 'Right') {
      const page = enrichServices(result.right);
      setServicesState(current => current._tag === 'Success' ? success([...current.value, ...page]) : current);
      setHasMore(page.length === PAGE_SIZE);
    } else {
      setLoadMoreError(result.left);
    }
    setLoadingMore(false);
  };


  useEffect(() => {
    loadServices();
  }, []);

  return (
    <div className="flex-1 bg-slate-50 min-h-screen p-4 md:p-8 flex flex-col gap-6">
      <Header onExport={() => exportServicesCsv(services)} />
      <Stats services={services} loaded={servicesState._tag === 'Success'} />

      <div className="flex flex-col gap-4">
        <FilterBar filters={filters} categories={categories} onChange={setFilters} />

        {foldRemoteData(
          servicesState,
          () => <div className="p-12 text-center text-slate-500">Đang khởi tạo...</div>,
          () => <DataLoadingState className="py-16 flex flex-col items-center justify-center text-slate-400" label="Đang tải danh sách dịch vụ…" />,

          (err) => <div className="p-12 text-center text-rose-500 bg-rose-50">Lỗi tải dữ liệu: {err.message}</div>,
          () => <>
            {filteredServices.length
              ? <ServiceGrid services={filteredServices} />
              : <div className="p-12 text-center text-slate-500" role="status">Không có dịch vụ phù hợp với bộ lọc.</div>}
            <p className="text-center text-xs text-slate-500" role="status">
              Đang hiển thị {filteredServices.length} / {services.length} dịch vụ đã tải
            </p>
            {hasMore && <div className="flex flex-col items-center gap-2">
              <button
                type="button"
                onClick={() => void loadMoreServices()}
                disabled={loadingMore}
                className="rounded-lg border border-sky-200 bg-white px-5 py-2.5 text-sm font-semibold text-sky-700 shadow-sm transition hover:bg-sky-50 disabled:cursor-wait disabled:opacity-60"
              >
                {loadingMore ? 'Đang tải thêm…' : 'Tải thêm dịch vụ'}
              </button>
              {loadMoreError && <p className="text-sm text-rose-600" role="alert">
                Không thể tải thêm: {loadMoreError.message}
              </p>}
            </div>}
          </>
        )}
      </div>
    </div>
  );
}
