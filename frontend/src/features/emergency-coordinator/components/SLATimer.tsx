import React, { useState, useEffect, memo } from 'react';

export const SLATimer = memo(({ initialSeconds = 56 }: { initialSeconds?: number }) => {
  const [seconds, setSeconds] = useState(initialSeconds);

  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => clearInterval(id);
  }, []);

  const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
  const secs = (seconds % 60).toString().padStart(2, '0');

  return (
    <div className="bg-white rounded-lg p-3 flex items-center gap-4">
      <div className="text-sm font-semibold text-gray-700">
        ⏱ SLA PHẢN ỨNG TỐI ĐA<br />
        <span className="text-xs text-gray-500 font-normal">Tự động kích hoạt báo động toàn viện khi hết giờ</span>
      </div>
      <div className="text-5xl font-bold text-red-600">
        {mins}:{secs}<span className="text-xl">GIÂY</span>
      </div>
    </div>
  );
});
