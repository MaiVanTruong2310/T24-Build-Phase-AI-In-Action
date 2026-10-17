interface SummaryCardProps {
  label: string;
  value: number;
  accent: string;
  bg: string;
  border: string;
  dot: string;
}

export function SummaryCard({ label, value, accent, bg, border, dot }: SummaryCardProps) {
  return (
    <div className={`${bg} ${border} border rounded-xl px-4 py-3 flex items-center justify-between`}>
      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</p>
        <p className={`text-2xl font-extrabold mt-1 ${accent}`}>{value}</p>
      </div>
      <div className={`w-3 h-3 rounded-full ${dot}`} />
    </div>
  );
}
