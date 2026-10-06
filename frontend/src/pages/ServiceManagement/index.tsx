import { TypewriterLoader } from '../../components/TypewriterLoader';
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
      // Mock some UI data for the missing API fields
      const enrichedServices = result.right.map(service => ({
        ...service,
        price: service.price ?? 1850000,
        original_price: service.original_price ?? 2200000,
        category: service.category ?? 'Tiêu Chuẩn',
        patient_count: service.patient_count ?? Math.floor(Math.random() * 2000),
        satisfaction_rate: service.satisfaction_rate ?? 99,
        features: service.features ?? [
          'Khám nội khoa tổng quát & đo thị lực, răng hàm mặt',
          'Công thức máu 18 chỉ số (CBC) & Đường huyết đói',
          'Đánh giá men gan (AST, ALT) & Chức năng thận',
          'X-quang ngực thẳng kỹ thuật số & Siêu âm ổ bụng'
        ]
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
      <Header />
      <Stats />
      
      <div className="flex flex-col gap-4">
        <FilterBar />
        
        {foldRemoteData(
          servicesState,
          () => <div className="p-12 text-center text-slate-500">Đang khởi tạo...</div>,
          () => <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
            <TypewriterLoader size="md" />
            <span>Đang tải danh sách dịch vụ...</span>
          </div>,
          (err) => <div className="p-12 text-center text-rose-500 bg-rose-50">Lỗi tải dữ liệu: {err.message}</div>,
          (services) => <ServiceGrid services={services} />
        )}
      </div>
    </div>
  );
}
