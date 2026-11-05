import type { Forecast } from "../model/registry";

export function RegistryTable({ registry }: { registry: Forecast[] }) {
  const rows = [...registry].sort((a, b) => a.peakYear - b.peakYear);
  return (
    <details className="registry">
      <summary>Major-source registry ({rows.length} positions after dedupe)</summary>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Org</th>
              <th>Report</th>
              <th>Scenario</th>
              <th>Type</th>
              <th className="num">Peak year</th>
              <th className="num">Weight</th>
              <th className="num">± yr</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.org}|${r.scenario}`} title={r.note}>
                <td>
                  {r.org}
                  {!r.verified && " †"}
                </td>
                <td>{r.report}</td>
                <td>{r.scenario}</td>
                <td>{r.sourceType}</td>
                <td className="num">{r.censored ? "≥ 2050" : r.peakYear}</td>
                <td className="num">{r.weight.toFixed(1)}</td>
                <td className="num">{r.sigma.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="note">
        Only baseline scenarios enter the blend. Weight ≈ methodology transparency + track record − conflict of
        interest. † = stance proxy, not a published peak-year figure. "≥ 2050" rows are right-censored: they pull
        the distribution's tail without being silenced.
      </div>
    </details>
  );
}
