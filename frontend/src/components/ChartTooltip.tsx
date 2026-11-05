interface Entry {
  name?: string;
  value?: number | string;
  color?: string;
  dataKey?: string | number;
}

interface Props {
  active?: boolean;
  payload?: Entry[];
  label?: string | number;
  title?: (label: string | number | undefined) => string;
  format?: (value: number | string | undefined, entry: Entry) => string;
}

/** One tooltip, every series: value first (strong), series name second, keyed by a short line. */
export function ChartTooltip({ active, payload, label, title, format }: Props) {
  if (!active || !payload?.length) return null;
  return (
    <div className="tip" role="status">
      <div className="tip-title">{title ? title(label) : String(label ?? "")}</div>
      {payload.map((p, i) => (
        <div className="row" key={i}>
          <span className="key" style={{ background: p.color }} />
          <span className="v">{format ? format(p.value, p) : String(p.value ?? "")}</span>
          <span className="l">{p.name}</span>
        </div>
      ))}
    </div>
  );
}
