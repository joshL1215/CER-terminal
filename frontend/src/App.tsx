import { useEffect, useMemo, useState } from "react";

import { ArticleFeed } from "./components/ArticleFeed";
import { FilterRow } from "./components/Filters";
import { DistributionChart, HistoryChart, TimelineChart } from "./components/OutlookCharts";
import { RegistryTable } from "./components/RegistryTable";
import { StatTiles } from "./components/StatTiles";
import { VolumeChart } from "./components/VolumeChart";
import { isLiveConfigured, loadDataset, loadSample } from "./data/client";
import type { Dataset } from "./data/types";
import { analyze, DEFAULT_FILTERS, type Filters } from "./model/analysis";

type Theme = "light" | "dark" | null;

function readTheme(): Theme {
  try {
    const t = localStorage.getItem("cer-theme");
    return t === "light" || t === "dark" ? t : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [dataset, setDataset] = useState<Dataset>(() => loadSample());
  const [loading, setLoading] = useState(isLiveConfigured);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [theme, setTheme] = useState<Theme>(readTheme);

  useEffect(() => {
    if (!isLiveConfigured) return;
    let cancelled = false;
    loadDataset()
      .then((d) => {
        if (!cancelled) setDataset(d);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme) root.setAttribute("data-theme", theme);
    else root.removeAttribute("data-theme");
    try {
      if (theme) localStorage.setItem("cer-theme", theme);
      else localStorage.removeItem("cer-theme");
    } catch {
      /* storage unavailable: the toggle still works for this page */
    }
  }, [theme]);

  const analysis = useMemo(() => analyze(dataset, filters), [dataset, filters]);
  const asOf = dataset.asOf.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>CER Terminal</h1>
          <div className="sub">Energy news, screened daily, read against the fossil fuel peak</div>
        </div>
        <div className="header-right">
          <span className={`badge${dataset.mode === "sample" ? " sample" : ""}`}>
            <span className="dot" />
            {dataset.mode === "live" ? "Live from Supabase" : "Sample snapshot"} · as of {asOf}
          </span>
          <button
            className="ghost"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            aria-label="Toggle color theme"
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      {error && (
        <div className="error" role="alert">
          Couldn't reach Supabase ({error}); showing the bundled sample instead.
        </div>
      )}

      <FilterRow filters={filters} feeds={dataset.feeds} count={analysis.articles.length} onChange={setFilters} />

      <StatTiles analysis={analysis} />

      <HistoryChart consensus={analysis.withNowcast} dim={loading} />
      <div className="grid-2">
        <DistributionChart consensus={analysis.withNowcast} dim={loading} />
        <TimelineChart points={analysis.timeline} dim={loading} />
      </div>
      <VolumeChart volume={analysis.volume} categories={analysis.categoriesInView} dim={loading} />

      <h2 className="section-title">Kept articles</h2>
      <ArticleFeed articles={analysis.articles} feedsById={analysis.feedsById} claimIds={analysis.claimIds} />

      <RegistryTable registry={analysis.registry} />

      <p className="note">
        How news enters the number: kept articles that make a directional claim about the fossil peak ("peaked
        in 2025", "nearing peak", "no peak before…") are blended as one pseudo-source, capped at half the weight
        of a top institution and decaying with a 60-day half-life. The registry of published outlooks carries the
        rest. Historical consumption is approximate (OWID / Energy Institute).
      </p>
    </div>
  );
}
