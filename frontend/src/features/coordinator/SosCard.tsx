import { dateTime } from './api'

interface SosSnapshot {
  triggered_at?: string
  latitude?: number | null
  longitude?: number | null
  accuracy_m?: number | null
  maps_url?: string | null
  location_error?: string | null
}

/** Thẻ SOS: hiển thị tên, SĐT (bấm để gọi) và vị trí (bấm để mở bản đồ) mà bệnh nhân gửi khi bấm 115. */
export function SosCard({ snapshot, patient }: { snapshot: Record<string, unknown>; patient: Record<string, string | null> }) {
  const sos = snapshot.sos as SosSnapshot | undefined
  if (!sos) return null
  const phone = patient.phone || ''
  return (
    <div className="cw-emergency-banner" role="alert" style={{ borderWidth: 2 }}>
      <strong>🚨 BỆNH NHÂN BẤM SOS CẤP CỨU</strong>
      <p style={{ margin: '6px 0 0' }}>
        <b>{patient.name || 'Chưa rõ tên'}</b> · {phone ? <a href={`tel:${phone}`}>{phone}</a> : 'chưa có SĐT'} · {dateTime(sos.triggered_at)}
      </p>
      <p style={{ margin: '4px 0 0' }}>
        {sos.maps_url ? (
          <>
            📍 <a href={sos.maps_url} target="_blank" rel="noreferrer noopener">Mở vị trí trên Google Maps</a>
            {' '}({sos.latitude?.toFixed(5)}, {sos.longitude?.toFixed(5)}{sos.accuracy_m != null ? `, sai số ~${Math.round(sos.accuracy_m)} m` : ''})
          </>
        ) : (
          <>📍 Không lấy được vị trí{sos.location_error ? ` (${sos.location_error})` : ''}. Hãy hỏi địa chỉ khi gọi lại.</>
        )}
      </p>
    </div>
  )
}
