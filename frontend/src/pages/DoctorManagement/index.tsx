import React, { useEffect, useState } from 'react';
import { Header } from './Header';
import { Stats } from './Stats';
import { FilterBar } from './FilterBar';
import { DoctorTable } from './DoctorTable';
import { AiBanner } from './AiBanner';
import { RemoteData, Doctor, notAsked, loading, success, failure, foldRemoteData } from './types';
import { fetchDoctors } from './api';

export default function DoctorManagement() {
  const [doctorsState, setDoctorsState] = useState<RemoteData<Error, Doctor[]>>(notAsked());

  const loadDoctors = async () => {
    setDoctorsState(loading());
    const task = fetchDoctors();
    const result = await task();
    if (result._tag === 'Right') {
      setDoctorsState(success(result.right));
    } else {
      setDoctorsState(failure(result.left));
    }
  };

  useEffect(() => {
    loadDoctors();
  }, []);

  return (
    <div className="flex-1 bg-slate-50 min-h-screen p-4 md:p-8 flex flex-col gap-6">
      <Header />
      <Stats />
      
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <FilterBar />
        
        {foldRemoteData(
          doctorsState,
          () => <div className="p-12 text-center text-slate-500">Đang khởi tạo...</div>,
          () => <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
            <div className="w-6 h-6 border-2 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
            <span>Đang tải danh sách bác sĩ...</span>
          </div>,
          (err) => <div className="p-12 text-center text-rose-500 bg-rose-50">Lỗi tải dữ liệu: {err.message}</div>,
          (doctors) => <DoctorTable doctors={doctors} />
        )}
      </div>

      <AiBanner />
    </div>
  );
}
