import { memo } from 'react';
import { ChatbotWidget } from '../../layouts/ChatbotWidget';

// Trang chat chiếm trọn vùng dưới header (RootLayout lo chiều cao). Nút 115 đã có ở header và dòng cuối khung chat.
export default memo(function PatientConsultationPage() {
  return (
    <div className="h-full min-h-0 w-full">
      <ChatbotWidget embedded />
    </div>
  );
});
