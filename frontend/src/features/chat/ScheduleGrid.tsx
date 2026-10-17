import { useState } from 'react';
import { CalendarDays } from 'lucide-react';
import type { ScheduleGridCell, ScheduleGridData } from './api';
import './ScheduleGrid.css';

interface ScheduleGridProps {
  grid: ScheduleGridData;
  disabled?: boolean;
  /** Gửi câu chọn ("14:00 chiều 17/10 · Nguyễn Văn Thái") như bấm nút trả lời nhanh. */
  onPick: (reply: string) => void;
}

/** Lưới lịch trống 7 ngày × 2 buổi; ô nhiều bác sĩ mở danh sách để chọn người. Dữ liệu lấy từ DB, không do AI viết. */
export function ScheduleGrid({ grid, disabled = false, onPick }: ScheduleGridProps) {
  const [openKey, setOpenKey] = useState<string | null>(null);
  const openEntries = openKey ? grid.cells[openKey] ?? [] : [];
  const openDay = openKey ? grid.days.find((day) => openKey.startsWith(day.date)) : undefined;
  const openPeriod = openKey ? grid.periods.find((period) => openKey.endsWith(period.key)) : undefined;

  const pickCell = (key: string, entries: ScheduleGridCell[]) => {
    if (entries.length === 1) { onPick(entries[0].reply); return; }
    setOpenKey((current) => (current === key ? null : key));
  };

  const title = grid.doctor ? `BS. ${grid.doctor}` : grid.department;
  return (
    <section className="sgrid" aria-label="Lịch trống 7 ngày">
      <header className="sgrid__head">
        <CalendarDays aria-hidden="true" />
        <span className="sgrid__title">Lịch trống · {title}</span>
        {grid.facility && <span className="sgrid__facility">{grid.facility}</span>}
      </header>
      <div className="sgrid__scroll">
        <table className="sgrid__table">
          <thead>
            <tr>
              <th scope="col" className="sgrid__corner"><span className="sr-only">Buổi</span></th>
              {grid.days.map((day) => (
                <th key={day.date} scope="col"><span className="sgrid__wd">{day.weekday}</span><span className="sgrid__date">{day.label}</span></th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.periods.map((period) => (
              <tr key={period.key}>
                <th scope="row" className="sgrid__period">{period.label}</th>
                {grid.days.map((day) => {
                  const key = `${day.date}|${period.key}`;
                  const entries = grid.cells[key] ?? [];
                  if (!entries.length) return <td key={key} className="sgrid__cell is-empty" aria-label={`${period.label} ${day.weekday} ${day.label}: hết lịch`}>—</td>;
                  const single = entries.length === 1;
                  const label = grid.doctor || single ? entries[0].time : `${entries.length} BS`;
                  return (
                    <td key={key} className="sgrid__cell">
                      <button
                        type="button"
                        disabled={disabled}
                        aria-pressed={openKey === key}
                        aria-label={`${period.label} ${day.weekday} ${day.label}: ${single ? `${entries[0].time} với BS. ${entries[0].doctor}` : `${entries.length} bác sĩ còn trống`}`}
                        className={`sgrid__btn${grid.highlight === key ? ' is-highlight' : ''}${openKey === key ? ' is-open' : ''}`}
                        onClick={() => pickCell(key, entries)}
                      >
                        {label}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {openKey && openEntries.length > 1 && (
        <div className="sgrid__pick" role="group" aria-label={`Chọn bác sĩ: ${openPeriod?.label ?? ''} ${openDay?.weekday ?? ''} ${openDay?.label ?? ''}`}>
          <p className="sgrid__pick-title">{openPeriod?.label} {openDay?.weekday} {openDay?.label}: chọn bác sĩ</p>
          {openEntries.map((entry) => (
            <button key={entry.schedule_id} type="button" disabled={disabled} className="sgrid__doc" onClick={() => onPick(entry.reply)}>
              <strong>BS. {entry.doctor}</strong>
              <span>{entry.time}{entry.facility ? ` · ${entry.facility}` : ''}</span>
            </button>
          ))}
        </div>
      )}
      <p className="sgrid__hint">Bấm ô để chọn. Hoặc nhắn ngày giờ bạn muốn.</p>
    </section>
  );
}
