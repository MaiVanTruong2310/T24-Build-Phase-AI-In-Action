import React, { useEffect, useState } from 'react';
import { Header } from './Header';
import { Stats } from './Stats';
import { FilterBar } from './FilterBar';
import { ServiceGrid } from './ServiceGrid';
import { RemoteData, notAsked, loading, success, failure, foldRemoteData } from './types';
import { fetchServices, Service } from './api';

export default function ServiceManagement() {
  const [servicesState, setServicesState] = useState<RemoteData<Error, Service[]>>(notAsked());

  const loadServices = async () => {
    setServicesState(loading());
    const result = await fetchServices()();
    if (result._tag === 'Right') {
      setServicesState(success(result.right));
    } else {
      setServicesState(failure(result.left));
    }
  };

  useEffect(() => {
    loadServices();
  }, []);

  return (
    <div className="flex-1 bg-slate-50 min-h-screen p-4 md:p-8 flex flex-col gap-6">
      <Header />
      <Stats />
      
      <div className="flex flex-col gap-4">
        <FilterBar />
        
        {foldRemoteData(
          servicesState,
          () => <div className="p-12 text-center text-slate-500">Đang khởi tạo...</div>,
          () => <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
            <div className="w-6 h-6 border-2 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
            <span>Đang tải danh sách dịch vụ...</span>
          </div>,
          (err) => <div className="p-12 text-center text-rose-500 bg-rose-50">Lỗi tải dữ liệu: {err.message}</div>,
          (services) => <ServiceGrid services={services} />
        )}
      </div>
    </div>
  );
}
