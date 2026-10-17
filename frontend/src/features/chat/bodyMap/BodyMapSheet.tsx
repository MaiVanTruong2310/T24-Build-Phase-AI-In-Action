import { useEffect, useRef } from 'react';
import { BodyMap } from './BodyMap';

interface BodyMapSheetProps {
  open: boolean;
  onClose: () => void;
  onPick: (text: string) => void;
}

// Màn hình nhỏ không có cột trái: mở hình cơ thể dạng bảng trượt từ dưới lên.
export function BodyMapSheet({ open, onClose, onPick }: BodyMapSheetProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="body-map-sheet" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Chỉ chỗ khó chịu trên cơ thể" className="body-map-sheet__panel" onClick={(event) => event.stopPropagation()}>
        <button ref={closeRef} type="button" className="body-map-sheet__close" onClick={onClose}>Đóng</button>
        <BodyMap onPick={(text) => { onPick(text); onClose(); }} />
      </div>
    </div>
  );
}
