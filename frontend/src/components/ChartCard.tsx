import { useState, type ReactNode } from "react";
import { Icon } from "./Icon";
export interface TableColumn { key: string; label: string; numeric?: boolean; }
interface Props { title: string; subtitle?: string; columns: TableColumn[]; rows: Record<string, string | number>[]; dim?: boolean; children: ReactNode; }
export function ChartCard({ title, subtitle, columns, rows, dim, children }: Props) {
  const [table, setTable] = useState(false);
  return <section className={`card chart-card${dim ? " dim" : ""}`} aria-label={title} aria-busy={dim}>
    <div className="card-head">
      <div>
        <h2>
          {title}
        </h2>
        {subtitle && <div className="sub">
          {subtitle}
        </div>}
      </div>
      <div className="chart-view-switch" role="group" aria-label={`${title} display`}>
        <button onClick={() => setTable(false)} aria-pressed={!table} aria-label={`Show chart: ${title}`}>
          <Icon name="signal" size={14} />
        </button>
        <button onClick={() => setTable(true)} aria-pressed={table} aria-label={`Show table: ${title}`}>Table</button>
      </div>
    </div>

    {!rows.length ? <div className="chart-empty">
      <Icon name="overview" size={24} />
      <p>No data for this selection.</p>
      <span>Broaden the date range or clear your filters.</span>
    </div> : table ? <div className="table-wrap chart-table" tabIndex={0} role="region" aria-label={`${title} data table`}>
      <table className="data">
        <thead>
          <tr>
            {columns.map((c) => <th key={c.key} className={c.numeric ? "num" : undefined}>
              {c.label}
            </th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => <tr key={i}>
            {columns.map((c) => <td key={c.key} className={c.numeric ? "num" : undefined}>
              {r[c.key]}
            </td>)}
          </tr>)}
        </tbody>
      </table>
    </div> : <div className="plot">
      {children}
    </div>}

  </section>;
}
