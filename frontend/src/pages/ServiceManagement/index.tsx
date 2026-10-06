import { TypewriterLoader } from '../../components/TypewriterLoader';
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

export default function ServiceManagement() {
  const [servicesState, setServicesState] = useState<RemoteData<Error, Service[]>>(notAsked());
  const [filters, setFilters] = useState<ServiceFilters>({ search: '', category: '', priceRange: '', status: '' });
  const services = servicesState._tag === 'Success' ? servicesState.value : EMPTY_SERVICES;
  const categories = useMemo(() => [...new Set(services.map(service => service.category).filter((category): category is string => Boolean(category)))].sort(), [services]);
  const filteredServices = useMemo(() => filterServices(services, filters), [services, filters]);

  const loadServices = async () => {
    setServicesState(loading());
    const result = await fetchServices()();
    if (result._tag === 'Right') {
      // Preserve API values; optional fields are rendered as unavailable.
      const enrichedServices = result.right.map(service => ({
        ...service,
        price: service.price,
        original_price: service.original_price,
        category: service.category,
        patient_count: service.patient_count,
        satisfaction_rate: service.satisfaction_rate,
        features: service.features ?? [],
      }));
      setServicesState(success(enrichedServices));
    } else {
      setServicesState(failure(result.left));
    }
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
          () => <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
            <TypewriterLoader size="md" />
            <span>Đang tải danh sách dịch vụ...</span>
          </div>,
          (err) => <div className="p-12 text-center text-rose-500 bg-rose-50">Lỗi tải dữ liệu: {err.message}</div>,
          () => filteredServices.length
            ? <ServiceGrid services={filteredServices} />
            : <div className="p-12 text-center text-slate-500" role="status">Không có dịch vụ phù hợp với bộ lọc.</div>
        )}
      </div>
    </div>
  );
}
