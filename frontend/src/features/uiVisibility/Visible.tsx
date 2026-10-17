import { useState, type ReactNode } from 'react';
import { Eye, EyeOff, Lock } from 'lucide-react';
import { UI_ENTRY, type UiKey } from './registry';
import { setUiVisibility, UI_EDIT_MODE, useUiHidden } from './store';
import './uiVisibility.css';

interface VisibleProps {
  id: UiKey;
  children: ReactNode;
  /** Bọc bằng thẻ inline (nút, mục menu) thay cho khối, chỉ ảnh hưởng chế độ sửa. */
  inline?: boolean;
}

/**
 * Bọc một thành phần để admin bật/tắt hiển thị (/staff/ui-editor).
 * Người dùng thường: bị ẩn thì không render gì, không thêm thẻ bọc nào (bố cục giữ nguyên).
 * Chế độ sửa (trong iframe của trang admin): viền + công tắc; thành phần đang ẩn hiện mờ để còn bật lại.
 */
export function Visible({ id, children, inline = false }: VisibleProps) {
  const hidden = useUiHidden(id);
  const entry = UI_ENTRY.get(id);
  const locked = Boolean(entry?.locked);
  if (!UI_EDIT_MODE) return hidden && !locked ? null : <>{children}</>;
  return <EditableVisible id={id} hidden={hidden && !locked} locked={locked} label={entry?.label ?? id} reason={entry?.reason} inline={inline}>{children}</EditableVisible>;
}

function EditableVisible({ id, hidden, locked, label, reason, inline, children }: {
  id: string; hidden: boolean; locked: boolean; label: string; reason?: string; inline: boolean; children: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const Tag = inline ? 'span' : 'div';
  const toggle = async () => {
    setBusy(true);
    setError('');
    try {
      await setUiVisibility(id, hidden);
    } catch (reasonError) {
      setError(reasonError instanceof Error ? reasonError.message : 'Không lưu được.');
    } finally {
      setBusy(false);
    }
  };
  const title = locked ? `${label} — ${reason || 'Luôn hiển thị.'}` : `${label}: đang ${hidden ? 'ẩn' : 'hiện'}. Bấm để ${hidden ? 'hiện' : 'ẩn'}.`;
  return (
    <Tag className={`uiv${inline ? ' uiv--inline' : ''}${hidden ? ' is-hidden' : ''}${locked ? ' is-locked' : ''}`} data-uiv={id}>
      <span className="uiv__bar">
        <button type="button" className="uiv__toggle" disabled={locked || busy} aria-pressed={!hidden} title={title} aria-label={title}
          onClick={(event) => { event.preventDefault(); event.stopPropagation(); void toggle(); }}>
          {locked ? <Lock aria-hidden="true" /> : hidden ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
          <span>{locked ? 'Khoá' : hidden ? 'Đang ẩn' : 'Đang hiện'}</span>
        </button>
        <span className="uiv__label">{label}</span>
        {error && <span className="uiv__error" role="alert">{error}</span>}
      </span>
      {children}
    </Tag>
  );
}
