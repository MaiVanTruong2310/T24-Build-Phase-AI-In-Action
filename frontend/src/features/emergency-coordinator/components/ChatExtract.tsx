import React, { memo } from 'react';
import { MessageSquare } from 'lucide-react';

export const ChatExtract = memo(() => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
    <h3 className="font-bold text-gray-800 flex items-center gap-2 mb-4">
      <MessageSquare className="w-5 h-5 text-blue-500" />
      Trích Xuất Hội Thoại Kích Hoạt
    </h3>
    <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
      <div className="flex justify-end">
        <div className="bg-blue-100 text-blue-900 p-3 rounded-2xl rounded-tr-none max-w-[80%] shadow-sm">
          Chào bác sĩ, ngực trái của tôi tự nhiên đau thắt dữ dội quá...
        </div>
      </div>
      <div className="flex justify-start">
        <div className="bg-white border border-gray-200 text-gray-800 p-3 rounded-2xl rounded-tl-none max-w-[80%] shadow-sm">
          Chào anh Long! Tình trạng đau ngực lan vai và cánh tay trái là dấu hiệu cần hết sức thận trọng...
        </div>
      </div>
    </div>
  </div>
));
