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
        <div className="fixed inset-0 z-[10000] bg-slate-950/40" onClick={() => onOpenChange(false)} aria-hidden="true" />
      )}
      <div className="pointer-events-none fixed inset-0 z-[10001] overflow-hidden">
      <div
        className={`pointer-events-auto absolute inset-y-0 right-0 w-full sm:inset-y-4 sm:w-[400px] sm:max-w-[calc(100vw-3rem)] transition-transform duration-300 ease-out motion-reduce:transition-none ${open ? 'translate-x-0' : 'translate-x-full'}`}
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
          className={`absolute top-1/2 h-32 w-10 -translate-y-1/2 flex-col items-center justify-center gap-1.5 rounded-l-2xl border border-r-0 border-blue-400/80 light:border-app-primary bg-gradient-to-b from-blue-600 to-cyan-600 light:from-app-primary light:to-app-primary text-white shadow-2xl hover:from-blue-500 hover:to-cyan-500 light:hover:from-app-primary-hover light:hover:to-app-primary-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 cursor-pointer active:scale-95 transition-all ${open ? 'hidden sm:flex sm:-left-10' : 'flex -left-10'}`}
        >
          {open ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          <span className="text-[10px] font-bold tracking-wider [writing-mode:vertical-rl] select-none py-1">Phiếu Hẹn Khám</span>
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
          className="flex h-full min-h-0 flex-col overflow-hidden border-l border-slate-200 light:border-app-border bg-white light:bg-app-surface shadow-2xl outline-none sm:rounded-l-2xl dark:border-slate-800 dark:bg-[#0c162d]"
        >
          <div
            onTouchStart={startSwipe}
            onTouchEnd={finishSwipe}
            onTouchCancel={() => { touchStart.current = null; }}
            style={{ touchAction: 'pan-y' }}
            className="shrink-0 border-b border-slate-200 light:border-app-border bg-blue-50 light:bg-app-muted px-12 py-3 text-center text-xs text-blue-700 light:text-app-primary dark:border-slate-800 dark:bg-slate-900 dark:text-cyan-300"
          >
            Vuốt sang phải để thu gọn phiếu
          </div>
          <div className="min-h-0 flex-1 pb-[env(safe-area-inset-bottom)]">
            <LiveBookingPanel {...panelProps} isMobileDrawer onClose={() => onOpenChange(false)} />
          </div>
        </div>
      </div>
      </div>
    </>,
    document.body
  );
}
