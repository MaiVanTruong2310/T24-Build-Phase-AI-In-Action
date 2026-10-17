import { memo, useMemo, useState, type KeyboardEvent, type ReactNode } from 'react';
import data from './bodyRegions.json';
import './BodyMap.css';

interface BodyOption { label: string; text: string }
interface BodyRegion { id: string; label: string; hint?: string; keywords?: string[]; options: BodyOption[] }
type View = 'front' | 'back' | 'head' | 'abdomen';

const REGIONS = new Map<string, BodyRegion>((data.regions as BodyRegion[]).map((region) => [region.id, region]));
const ONSETS = data.onsets as BodyOption[];
const VIEWS: { id: View; label: string }[] = [
  { id: 'front', label: 'Mặt trước' },
  { id: 'back', label: 'Mặt sau' },
  { id: 'head', label: 'Đầu – mặt' },
  { id: 'abdomen', label: 'Bụng' },
];
const EXTRA_REGIONS = ['skin', 'whole_body'];

const fold = (text: string) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').toLowerCase();

// ===== Hình người trưởng thành, trung tính (viewBox 240×520). Lật ngang quanh x = 120 để vẽ nửa bên kia. =====
const MIRROR = 'matrix(-1 0 0 1 240 0)';
const both = (node: ReactNode) => <>{node}<g transform={MIRROR}>{node}</g></>;
const ARM = 'M64 106 Q52 110 50 128 L44 196 L38 262 Q34 276 34 296 Q36 308 44 306 Q50 300 50 286 L52 266 L58 200 L66 146 Z';
const LEG = 'M74 292 Q96 306 118 308 L116 364 L112 424 L110 478 Q113 492 106 500 L86 500 Q80 494 88 484 L88 424 L82 364 Z';
const TORSO =
  'M108 88 Q94 96 78 98 Q64 102 62 118 L64 170 Q68 206 72 236 Q68 266 74 292 Q96 306 120 306 Q144 306 166 292 Q172 266 168 236 Q172 206 176 170 L178 118 Q176 102 162 98 Q146 96 132 88 Z';
const SILHOUETTE = (
  <>
    {both(<path d={ARM} />)}
    {both(<path d={LEG} />)}
    <path d={TORSO} />
    <path d="M110 68 L130 68 L132 92 L108 92 Z" />
    <ellipse cx="120" cy="46" rx="25" ry="30" />
    {both(<ellipse cx="95" cy="48" rx="4" ry="8" />)}
  </>
);

// Vùng dùng chung hai mặt (tay, chân).
const LIMBS: Record<string, ReactNode> = {
  arm: both(<path d="M64 124 L56 128 L46 196 L40 258 L50 260 L57 200 L66 150 Z" />),
  wrist_hand: both(<ellipse cx="42" cy="284" rx="8" ry="16" />),
  thigh: both(<path d="M80 300 L116 310 L114 372 L86 372 Z" />),
  knee: both(<ellipse cx="100" cy="388" rx="13" ry="11" />),
  shin: both(<path d="M88 402 L113 402 L111 466 L90 466 Z" />),
  ankle_foot: both(<path d="M90 472 L111 472 L110 480 Q113 492 106 500 L86 500 Q80 494 88 484 Z" />),
};

const SHAPES: Record<View, Record<string, ReactNode>> = {
  // Mặt trước: bên trái hình là bên PHẢI của người bệnh.
  front: {
    ...LIMBS,
    head: <path d="M95.5 40 A25 30 0 0 1 144.5 40 Z" />,
    eyes: <rect x="104" y="42" width="32" height="8" rx="4" />,
    ear_nose: <>{both(<ellipse cx="95" cy="48" rx="4" ry="8" />)}<ellipse cx="120" cy="56" rx="4" ry="5" /></>,
    mouth: <ellipse cx="120" cy="66" rx="8" ry="4" />,
    throat: <rect x="112" y="76" width="16" height="14" rx="4" />,
    shoulder: both(<ellipse cx="70" cy="112" rx="10" ry="10" />),
    chest_right: <rect x="78" y="106" width="40" height="54" rx="8" />,
    chest_left: <rect x="122" y="106" width="40" height="54" rx="8" />,
    ruq: <rect x="80" y="164" width="26" height="30" rx="5" />,
    epigastric: <rect x="108" y="164" width="24" height="30" rx="5" />,
    luq: <rect x="134" y="164" width="26" height="30" rx="5" />,
    right_flank: <rect x="80" y="196" width="26" height="32" rx="5" />,
    periumbilical: <rect x="108" y="196" width="24" height="32" rx="5" />,
    left_flank: <rect x="134" y="196" width="26" height="32" rx="5" />,
    rlq: <rect x="80" y="230" width="26" height="30" rx="5" />,
    pelvic: <rect x="108" y="230" width="24" height="30" rx="5" />,
    llq: <rect x="134" y="230" width="26" height="30" rx="5" />,
    genital: <rect x="110" y="264" width="20" height="20" rx="8" />,
    hip: both(<ellipse cx="84" cy="284" rx="9" ry="9" />),
  },
  // Mặt sau: bên trái hình là bên TRÁI của người bệnh.
  back: {
    ...LIMBS,
    head: <ellipse cx="120" cy="46" rx="25" ry="30" />,
    neck_shoulder: <path d="M110 72 L130 72 L132 90 Q150 96 168 100 L170 122 L70 122 L72 100 Q90 96 108 90 Z" />,
    upper_back: <rect x="76" y="126" width="88" height="62" rx="10" />,
    flank: both(<rect x="70" y="192" width="24" height="40" rx="8" />),
    lumbar: <rect x="97" y="192" width="46" height="44" rx="8" />,
    buttock: <path d="M76 244 Q120 236 164 244 L166 290 Q120 304 74 290 Z" />,
  },
  // Phóng to đầu – mặt (viewBox 240×240).
  head: {
    head: <path d="M52.1 82 A72 90 0 0 1 187.9 82 Z" />,
    eyes: both(<ellipse cx="92" cy="102" rx="17" ry="9" />),
    ear_nose: <>{both(<ellipse cx="46" cy="116" rx="10" ry="22" />)}<path d="M120 108 L133 146 Q120 154 107 146 Z" /></>,
    mouth: <ellipse cx="120" cy="174" rx="26" ry="11" />,
    throat: <rect x="96" y="204" width="48" height="30" rx="10" />,
  },
  // Phóng to bụng: 9 vùng chuẩn + vùng kín (viewBox 240×260).
  abdomen: {
    ruq: <rect x="40" y="48" width="52" height="56" rx="8" />,
    epigastric: <rect x="94" y="48" width="52" height="56" rx="8" />,
    luq: <rect x="148" y="48" width="52" height="56" rx="8" />,
    right_flank: <rect x="40" y="106" width="52" height="56" rx="8" />,
    periumbilical: <rect x="94" y="106" width="52" height="56" rx="8" />,
    left_flank: <rect x="148" y="106" width="52" height="56" rx="8" />,
    rlq: <rect x="40" y="164" width="52" height="56" rx="8" />,
    pelvic: <rect x="94" y="164" width="52" height="56" rx="8" />,
    llq: <rect x="148" y="164" width="52" height="56" rx="8" />,
    genital: <rect x="98" y="226" width="44" height="22" rx="10" />,
  },
};

const VIEW_BOX: Record<View, string> = { front: '0 0 240 520', back: '0 0 240 520', head: '0 0 240 240', abdomen: '0 0 240 260' };

// Nền (không bấm được) và mốc giải phẫu giúp định vị.
const BACKDROP: Record<View, ReactNode> = {
  front: SILHOUETTE,
  back: SILHOUETTE,
  head: (
    <>
      <rect x="92" y="190" width="56" height="48" rx="8" />
      {both(<ellipse cx="46" cy="116" rx="10" ry="22" />)}
      <ellipse cx="120" cy="112" rx="72" ry="90" />
    </>
  ),
  abdomen: <path d="M36 18 Q120 2 204 18 Q214 120 206 216 Q120 262 34 216 Q26 120 36 18 Z" />,
};
const LANDMARKS: Record<View, ReactNode> = {
  front: (
    <>
      <path d="M84 102 Q100 99 116 104 M124 104 Q140 99 156 102" />
      <path d="M84 162 Q120 146 156 162" strokeDasharray="3 3" />
      <circle cx="120" cy="212" r="2.5" />
    </>
  ),
  back: <path d="M120 94 L120 290" strokeDasharray="3 4" />,
  head: null,
  abdomen: (
    <>
      <path d="M44 64 Q120 22 196 64" strokeDasharray="4 4" />
      <circle cx="120" cy="134" r="4" />
    </>
  ),
};
// Nhãn chữ trong khung phóng to: [vùng, x, y, dòng chữ].
const LABELS: Partial<Record<View, [string, number, number, string[]][]>> = {
  head: [
    ['head', 120, 50, ['Đầu']],
    ['eyes', 120, 106, ['Mắt']],
    ['ear_nose', 120, 136, ['Mũi']],
    ['ear_nose', 46, 148, ['Tai']],
    ['mouth', 120, 178, ['Miệng – răng']],
    ['throat', 120, 223, ['Cổ họng']],
  ],
  abdomen: [
    ['ruq', 66, 72, ['Hạ sườn', 'phải']],
    ['epigastric', 120, 72, ['Thượng vị', '(dạ dày)']],
    ['luq', 174, 72, ['Hạ sườn', 'trái']],
    ['right_flank', 66, 130, ['Mạn sườn', 'phải']],
    ['periumbilical', 120, 152, ['Quanh rốn']],
    ['left_flank', 174, 130, ['Mạn sườn', 'trái']],
    ['rlq', 66, 188, ['Hố chậu', 'phải']],
    ['pelvic', 120, 188, ['Hạ vị']],
    ['llq', 174, 188, ['Hố chậu', 'trái']],
    ['genital', 120, 241, ['Vùng kín']],
  ],
};
// Ký hiệu bên Phải/Trái của người bệnh: mặt trước và các khung phóng to nhìn từ phía trước.
const SIDES: Record<View, [string, string, number]> = {
  front: ['P', 'T', 30], back: ['T', 'P', 30], head: ['P', 'T', 18], abdomen: ['P', 'T', 14],
};

interface BodyMapProps {
  onPick: (text: string) => void;
  disabled?: boolean;
}

export const BodyMap = memo(function BodyMap({ onPick, disabled = false }: BodyMapProps) {
  const [view, setView] = useState<View>('front');
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [picked, setPicked] = useState<BodyOption | null>(null);
  const [query, setQuery] = useState('');
  const selectedRegion = selected ? REGIONS.get(selected) : undefined;
  const focusRegion = (hovered && REGIONS.get(hovered)) || selectedRegion;

  const matches = useMemo(() => {
    const needle = fold(query.trim());
    if (!needle) return [];
    return [...REGIONS.values()]
      .filter((region) =>
        [region.label, ...(region.keywords || []), ...region.options.map((option) => option.label)]
          .some((word) => fold(word).includes(needle)))
      .slice(0, 6);
  }, [query]);

  const choose = (id: string) => {
    if (disabled) return;
    setSelected(id);
    setPicked(null);
    setHovered(null);  // chạm trên điện thoại: không để "rê chuột" dính ở vùng nằm dưới ngón tay sau khi hình dịch
  };
  const onKey = (event: KeyboardEvent, id: string) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(id); }
  };
  const finish = (onset?: BodyOption) => {
    if (!picked) return;
    onPick(onset ? `${picked.text}, ${onset.text}` : picked.text);
    setSelected(null);
    setPicked(null);
    setQuery('');
  };
  const [rightMark, leftMark, sideY] = SIDES[view];
  const [, , width] = VIEW_BOX[view].split(' ').map(Number);

  return (
    <div className="body-map" aria-disabled={disabled || undefined}>
      <div className="body-map__head">
        <p className="body-map__title">Chỉ chỗ khó chịu</p>
      </div>
      <div className="body-map__views" role="group" aria-label="Chọn khung nhìn">
        {VIEWS.map((item) => (
          <button key={item.id} type="button" aria-pressed={view === item.id} onClick={() => { setView(item.id); setHovered(null); }}
            className={`body-map__view ${view === item.id ? 'is-active' : ''}`}>
            {item.label}
          </button>
        ))}
      </div>

      <label className="body-map__search">
        <span className="sr-only">Tìm nhanh vùng cơ thể</span>
        <input type="search" value={query} disabled={disabled} onChange={(event) => setQuery(event.target.value)}
          placeholder="Tìm nhanh: dạ dày, đầu gối, hậu môn…" />
      </label>
      {matches.length > 0 && (
        <div className="body-map__matches" role="group" aria-label="Kết quả tìm">
          {matches.map((region) => (
            <button key={region.id} type="button" className="body-map__extra" onClick={() => { choose(region.id); setQuery(''); }}>
              {region.label}
            </button>
          ))}
        </div>
      )}

      <div className="body-map__caption" aria-live="polite">
        {focusRegion ? (
          <>
            <strong>{focusRegion.label}</strong>
            {focusRegion.hint && <span>{focusRegion.hint}</span>}
          </>
        ) : (
          <span>Rê chuột hoặc chạm vào vùng đang khó chịu</span>
        )}
      </div>

      {selectedRegion && (
        <div className="body-map__panel" role="group" aria-label={`Triệu chứng ở ${selectedRegion.label}`}>
          {!picked ? (
            <>
              <p className="body-map__panel-title">{selectedRegion.label}: anh/chị bị thế nào?</p>
              <div className="body-map__options">
                {selectedRegion.options.map((option) => (
                  <button key={option.text} type="button" disabled={disabled} className="body-map__option" onClick={() => setPicked(option)}>
                    {option.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <p className="body-map__panel-title">{picked.label}: bắt đầu từ khi nào?</p>
              <div className="body-map__options">
                {ONSETS.map((onset) => (
                  <button key={onset.text} type="button" disabled={disabled} className="body-map__option" onClick={() => finish(onset)}>
                    {onset.label}
                  </button>
                ))}
              </div>
              <div className="body-map__panel-actions">
                <button type="button" className="body-map__link" onClick={() => setPicked(null)}>← Chọn lại</button>
                <button type="button" className="body-map__link" disabled={disabled} onClick={() => finish()}>Bỏ qua, không nhớ rõ</button>
              </div>
            </>
          )}
          <p className="body-map__panel-note">Câu sẽ được điền vào ô nhập, anh/chị có thể sửa hoặc kể thêm trước khi gửi. Chọn tiếp vùng khác để kể thêm triệu chứng.</p>
        </div>
      )}

      <svg viewBox={VIEW_BOX[view]} className={`body-map__svg body-map__svg--${view}`} role="group"
        aria-label={`Hình cơ thể, ${VIEWS.find((item) => item.id === view)?.label.toLowerCase()}`}>
        <g className="body-map__base" aria-hidden="true">{BACKDROP[view]}</g>
        {Object.entries(SHAPES[view]).map(([id, shape]) => {
          const region = REGIONS.get(id);
          if (!region) return null;
          return (
            <g key={id} role="button" tabIndex={disabled ? -1 : 0} aria-label={region.label} aria-pressed={selected === id}
              className={`body-map__region ${selected === id ? 'is-selected' : ''} ${hovered === id ? 'is-hovered' : ''}`}
              onMouseEnter={() => setHovered(id)} onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(id)} onBlur={() => setHovered(null)}
              onClick={() => choose(id)} onKeyDown={(event) => onKey(event, id)}>
              <title>{region.hint ? `${region.label}: ${region.hint}` : region.label}</title>
              {shape}
            </g>
          );
        })}
        <g className="body-map__landmarks" aria-hidden="true">{LANDMARKS[view]}</g>
        {LABELS[view]?.map(([id, x, y, lines]) => (
          <text key={`${id}-${x}-${y}`} x={x} y={y} className={`body-map__label ${selected === id ? 'is-selected' : ''}`} aria-hidden="true">
            {lines.map((line, index) => <tspan key={line} x={x} dy={index ? '1.15em' : 0}>{line}</tspan>)}
          </text>
        ))}
        <g className="body-map__sides" aria-hidden="true">
          <text x="10" y={sideY}>{rightMark}</text>
          <text x={width - 10} y={sideY}>{leftMark}</text>
        </g>
      </svg>
      <p className="body-map__hint">
        {view === 'back' ? 'Nhìn từ phía sau: bên trái hình là bên trái của anh/chị.' : 'P = bên phải, T = bên trái của anh/chị.'}
      </p>

      <div className="body-map__extras">
        {EXTRA_REGIONS.map((id) => (
          <button key={id} type="button" disabled={disabled} aria-pressed={selected === id} onClick={() => choose(id)}
            className={`body-map__extra ${selected === id ? 'is-active' : ''}`}>
            {REGIONS.get(id)?.label}
          </button>
        ))}
      </div>
    </div>
  );
});
