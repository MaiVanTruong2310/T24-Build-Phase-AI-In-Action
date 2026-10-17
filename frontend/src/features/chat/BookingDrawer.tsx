import { useEffect, useId, useRef, useState, type ComponentProps, type TouchEvent } from 'react';
import { createPortal } from 'react-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { LiveBookingPanel } from './LiveBookingPanel';

type BookingDrawerProps = ComponentProps<typeof LiveBookingPanel> & {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function BookingDrawer({ open, onOpenChange, ...panelProps }: BookingDrawerProps) {
  const panelId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const touchStart = useRef<{ x: number; y: number } | null>(null);
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 639px)').matches);

  useEffect(() => {
    const query = window.matchMedia('(max-width: 639px)');
    const update = () => setMobile(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const triggerElement = triggerRef.current;
    const previousOverflow = document.body.style.overflow;
    if (mobile) document.body.style.overflow = 'hidden';
    panelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onOpenChange(false);
      }
      if (mobile && event.key === 'Tab') {
        const controls = Array.from(panelRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]'
        ) || []).filter((control) => control.getClientRects().length > 0);
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (!first) { event.preventDefault(); return; }
        if (event.shiftKey && (document.activeElement === first || document.activeElement === panelRef.current)) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === panelRef.current)) {
          event.preventDefault(); first.focus();
        }
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      if (mobile) document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', onKeyDown);
      if (previousFocus?.isConnected) previousFocus.focus();
      else triggerElement?.focus();
    };
  }, [open, mobile, onOpenChange]);

  const startSwipe = (event: TouchEvent) => {
    const touch = event.touches[0];
    touchStart.current = { x: touch.clientX, y: touch.clientY };
  };
  const finishSwipe = (event: TouchEvent) => {
    const start = touchStart.current;
    touchStart.current = null;
    if (!start) return;
    const touch = event.changedTouches[0];
    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    if (dx < 0) onOpenChange(true);
    else onOpenChange(false);
  };

  return createPortal(
    <>
      {open && mobile && (
        <div className="bd-backdrop" onClick={() => onOpenChange(false)} aria-hidden="true" />
      )}
      <div className="bd-layer">
      <div
        className={`bd-drawer${open ? ' is-open' : ''}`}
      >
        <button
          ref={triggerRef}
          type="button"
          onClick={() => onOpenChange(!open)}
          onTouchStart={startSwipe}
          onTouchEnd={finishSwipe}
          onTouchCancel={() => { touchStart.current = null; }}
          style={{ touchAction: 'pan-y' }}
          aria-label={open ? 'Thu gọn phiếu đăng ký khám' : 'Mở phiếu hẹn khám bác sĩ chuyên khoa'}
          aria-expanded={open}
          aria-controls={panelId}
          className={`bd-handle${open ? ' is-open' : ''}`}
        >
          {open ? <ChevronRight size={18} aria-hidden="true" /> : <ChevronLeft size={18} aria-hidden="true" />}
          <span className="bd-handle__label">Phiếu hẹn khám</span>
        </button>
        <div
          id={panelId}
          ref={panelRef}
          role={mobile ? 'dialog' : 'region'}
          aria-modal={mobile && open ? true : undefined}
          aria-label="Phiếu đăng ký khám bệnh"
          aria-hidden={!open}
          inert={!open}
          tabIndex={-1}
          className="bd-sheet"
        >
          <div
            onTouchStart={startSwipe}
            onTouchEnd={finishSwipe}
            onTouchCancel={() => { touchStart.current = null; }}
            style={{ touchAction: 'pan-y' }}
            className="bd-hint"
          >
            Vuốt sang phải để thu gọn phiếu
          </div>
          <div className="bd-body">
            <LiveBookingPanel {...panelProps} isMobileDrawer onClose={() => onOpenChange(false)} />
          </div>
        </div>
      </div>
      </div>
    </>,
    document.body
  );
}
