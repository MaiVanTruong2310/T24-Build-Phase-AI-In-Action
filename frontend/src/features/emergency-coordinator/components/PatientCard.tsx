import React, { memo } from 'react';

type PatientData = {
  name: string;
  age: string;
  id: string;
  phone: string;
  kin: string;
  history: string[];
};

export const PatientCard = memo(({ data }: { data: PatientData }) => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
    <div className="flex items-center gap-4 mb-4">
      <div className="w-14 h-14 bg-gray-200 rounded-full overflow-hidden">
        <img src="https://i.pravatar.cc/150?img=11" alt="Patient" />
      </div>
      <div>
        <h2 className="text-xl font-bold text-gray-900">{data.name}</h2>
        <div className="text-sm text-gray-500">{data.age} • Mã: {data.id}</div>
      </div>
    </div>
    <div className="space-y-3">
      <div className="bg-gray-50 p-3 rounded-lg">
        <div className="text-xs text-gray-500 uppercase">SĐT Bệnh Nhân</div>
        <div className="font-semibold text-blue-600">{data.phone}</div>
      </div>
      <div className="bg-gray-50 p-3 rounded-lg">
        <div className="text-xs text-gray-500 uppercase">Người nhà khẩn cấp</div>
        <div className="font-semibold">{data.kin}</div>
      </div>
    </div>
  </div>
));
