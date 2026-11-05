import { useState, type ReactNode } from "react";

export interface TableColumn {
  key: string;
  label: string;
  numeric?: boolean;
}

interface Props {
  title: string;
  subtitle?: string;
  columns: TableColumn[];
  rows: Record<string, string | number>[];
  dim?: boolean;
  children: ReactNode;
}

/** A chart with its table twin: every value is reachable without hovering. */
export function ChartCard({ title, subtitle, columns, rows, dim, children }: Props) {
  const [table, setTable] = useState(false);
  return (
    <section className={`card${dim ? " dim" : ""}`} aria-label={title}>
      <div className="card-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <div className="sub">{subtitle}</div>}
        </div>
        <button className="toggle" onClick={() => setTable((t) => !t)} aria-pressed={table}>
          {table ? "Chart" : "Table"}
        </button>
      </div>
      {table ? (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c.key} className={c.numeric ? "num" : undefined}>
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  {columns.map((c) => (
                    <td key={c.key} className={c.numeric ? "num" : undefined}>
                      {r[c.key]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="plot">{children}</div>
      )}
    </section>
  );
}
