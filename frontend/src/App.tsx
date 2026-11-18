import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import { ArticleFeed } from "./components/ArticleFeed";
import { FilterRow } from "./components/Filters";
import { Icon, type IconName } from "./components/Icon";
import { DistributionChart, HistoryChart, TimelineChart } from "./components/OutlookCharts";
import { RegistryTable } from "./components/RegistryTable";
import { StatTiles } from "./components/StatTiles";
import { VolumeChart } from "./components/VolumeChart";
import { initialDataset, isLiveConfigured, loadDataset } from "./data/client";
import type { Dataset } from "./data/types";
import { analyze, articleCategories, DEFAULT_FILTERS, type Filters } from "./model/analysis";
import { tagCounts } from "./model/tags";

type View = "overview" | "news" | "sources";
const NAV: { id: View; label: string; icon: IconName }[] = [{ id: "overview", label: "Overview", icon: "overview" }, { id: "news", label: "News Feed", icon: "news" }, { id: "sources", label: "Sources & method", icon: "sources" }];
function readTheme(): "light" | "dark" {
  // index.html applies the same choice before React loads, so there is no flash.
  try { const value = localStorage.getItem("cer-theme"); if (value === "light" || value === "dark") return value; } catch { /* use the system setting */ }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [dataset, setDataset] = useState<Dataset>(initialDataset);
  const [hasLoaded, setHasLoaded] = useState(!isLiveConfigured);
  const [loading, setLoading] = useState(isLiveConfigured);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [theme, setTheme] = useState(readTheme);
  const [view, setView] = useState<View>("overview");
  const [includeNews, setIncludeNews] = useState(true);
  const [signalsOnly, setSignalsOnly] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!isLiveConfigured) return;
    let cancelled = false;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    loadDataset(controller.signal).then((d) => { if (!cancelled) { setDataset(d); setHasLoaded(true); } })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Unable to load articles"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; controller.abort(); };
  }, [refreshKey]);
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("cer-theme", theme); } catch { /* the toggle still works without storage */ }
  }, [theme]);

  // Typing in search stays responsive; the charts and estimate catch up a moment later.
  const deferredFilters = useDeferredValue(filters);
  const analysis = useMemo(() => analyze(dataset, deferredFilters), [dataset, deferredFilters]);
  const datasetTags = useMemo(() => tagCounts(dataset.articles), [dataset.articles]);
  const categories = useMemo(() => articleCategories(dataset.articles), [dataset.articles]);
  const articlesLoading = loading && !hasLoaded;
  const datasetEmpty = hasLoaded && !dataset.articles.length;
  const consensus = includeNews ? analysis.withNowcast : analysis.registryOnly;
  const shift = analysis.withNowcast.median - analysis.registryOnly.median;
  const asOf = dataset.asOf.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  const openView = useCallback((next: View) => { setView(next); window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); }, []);
  const openNews = (signals = false) => { setSignalsOnly(signals); openView("news"); };
  const topics = useMemo(() => {
    const counts = new Map<string, number>();
    for (const a of analysis.articles) counts.set(a.category ?? "other", (counts.get(a.category ?? "other") ?? 0) + 1);
    return [...counts].sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [analysis.articles]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <aside className="sidebar">
        <a className="brand" href="#" onClick={(e) => { e.preventDefault(); openView("overview"); }} aria-label="Center for Energy Research and Data Science Student Society: home">
          {/* Each logo is a stack of single-colour masks, so every part can follow the theme. */}
          <span className="logo-mask cer-logo" aria-hidden="true">
            <span className="cer-logo-orange" />
            <span className="cer-logo-blue" />
            <span className="cer-logo-text" />
          </span>
          <span className="brand-divider" aria-hidden="true" />
          <span className="logo-mask ds3-logo" aria-hidden="true">
            <span className="ds3-logo-orange" />
            <span className="ds3-logo-teal" />
            <span className="ds3-logo-text" />
          </span>
        </a>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {NAV.map((n) => <button key={n.id} className={`nav-item${view === n.id ? " active" : ""}`} aria-current={view === n.id ? "page" : undefined} onClick={() => openView(n.id)}>
            <Icon name={n.icon} />
            <span>
              {n.label}
            </span>
            {view === n.id && <span className="nav-dot" />}
          </button>)}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-rule" />
          <span>Center for Energy Research × DS3</span>
          <button className="theme-button" onClick={() => setTheme((t) => t === "dark" ? "light" : "dark")} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
            <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
            <span>
              {theme === "dark" ? "Light appearance" : "Dark appearance"}
            </span>
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">Workspace <Icon name="chevron" size={13} /><strong>
            {NAV.find((n) => n.id === view)?.label}
          </strong></div>
          <div className="header-right">
            <span className={`badge${dataset.mode === "sample" ? " sample" : ""}`}>
              <span className="dot" />
              {loading ? "Updating articles…" : error ? "Connection unavailable" : dataset.mode === "live" ? "Live articles" : "Sample data"}
            </span>
            {hasLoaded && <span className="as-of">As of {asOf}</span>}
            <button className="icon-button mobile-theme" aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} onClick={() => setTheme((t) => t === "dark" ? "light" : "dark")}>
              <Icon name={theme === "dark" ? "sun" : "moon"} size={15} />
            </button>
            {isLiveConfigured && <button className="icon-button" aria-label="Refresh live articles" disabled={loading} onClick={() => setRefreshKey((k) => k + 1)}>
              <Icon name="refresh" style={loading ? { animation: "spin 1s linear infinite" } : undefined} />
            </button>}
          </div>
        </header>
        <main id="main" className="main" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <h1 className={view === "overview" ? "outlook-title" : undefined}>
                {view === "overview" ? "When will fossil fuels peak?" : view === "news" ? "News Feed" : "Sources & method"}
              </h1>
              <p>
                {view === "overview" ? "An estimate of the year global fossil fuel use peaks, based on published outlooks and recent news." : view === "news" ? "Energy news articles. Filter by topic, region, energy type or source." : "The outlooks behind the estimate, and how news is counted."}
              </p>
            </div>
          </div>

          {error && <div className="error" role="alert">
            <strong>Articles could not be refreshed.</strong>
            {hasLoaded ? " Keeping the last loaded articles." : " Check the connection settings and try again."}
            <details>
              <summary>Connection details</summary>
              {error}
            </details>
            <button className="text-button" onClick={() => setRefreshKey((k) => k + 1)}>Try again <Icon name="refresh" size={14} /></button>
          </div>}

          {dataset.mode === "sample" && <div className="sample-notice">
            <span className="notice-symbol">i</span>
            <span><strong>Showing sample data.</strong> These articles are from {asOf}. Live data appears once the Supabase settings are configured.</span>
            <button className="text-button" onClick={() => openView("sources")}>About the data <Icon name="arrow" size={14} /></button>
          </div>}

          {dataset.totalArticles > dataset.articles.length && <div className="sample-notice" role="status">
            <span className="notice-symbol">i</span>
            <span>Showing the newest {dataset.articles.length.toLocaleString()} of {dataset.totalArticles.toLocaleString()} screened articles. Search, charts, saved articles and exports only use these.</span>
          </div>}

          {view !== "news" && <aside className="prototype-notice" aria-label="Forecasting development status">
            <strong>Forecasting prototype — still in development</strong>
            <p>Peak detection, news contributions, and forecast visualizations are experimental. The methods and estimates still require validation.</p>
          </aside>}

          {view !== "sources" && <FilterRow filters={filters} feeds={dataset.feeds} categories={categories} count={analysis.articles.length} tags={datasetTags} onChange={setFilters} />}

          <div className="view-content" key={view}>

            {view === "overview" && <>
              <div className="outlook-grid">
                <section className="forecast-panel" aria-label="Peak year estimate" aria-busy={loading}>
                  <div className="forecast-top">
                    <span className="forecast-tag">Prototype</span>
                  </div>
                  <h2>Estimated peak year</h2>
                  <div className="forecast-year" key={consensus.median.toFixed(1)}>
                    {consensus.median.toFixed(0)}
                    <span>median year</span>
                  </div>
                  <p className="forecast-range">80% likely between <strong>{consensus.p10.toFixed(0)}–{consensus.p90.toFixed(0)}</strong></p>
                  <div className="range-graphic" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <i />
                  </div>
                  <div className="forecast-control">
                    <span>Include news signals</span>
                    <button className="switch" role="switch" aria-checked={includeNews} aria-label="Include news signals in the estimate" onClick={() => setIncludeNews((v) => !v)}>
                      <span />
                    </button>
                  </div>
                  <p className="forecast-explanation">
                    {!includeNews ? "Showing the outlook registry alone. Turn on news signals to compare their effect." : !analysis.nowcast ? "No peak claims in this selection. The estimate reflects the outlook registry alone." : Math.abs(shift) < 0.05 ? "Selected news leaves the median unchanged at the displayed precision." : `Selected news shifts the median ${Math.abs(shift).toFixed(1)} years ${shift < 0 ? "earlier" : "later"} than the registry alone.`}
                  </p>
                  <button className="forecast-link" onClick={() => openView("sources")}>How is this estimated? <Icon name="arrow" size={16} /></button>
                </section>
                <HistoryChart consensus={consensus} dim={loading} />
              </div>
              <StatTiles analysis={analysis} consensus={consensus} onNews={openNews} onSources={() => openView("sources")} />
              <div className="section-heading">
                <div>
                  <h2>How certain is the estimate?</h2>
                </div>
              </div>
              <div className="grid-2">
                <DistributionChart consensus={consensus} dim={loading} />
                <TimelineChart points={analysis.timeline} dim={loading} />
              </div>
              <section className="insight-strip">
                <div className="insight-icon">
                  <Icon name="signal" size={21} />
                </div>
                <div>
                  <h3>Peak claims in the news</h3>
                  <p>
                    {analysis.nowcast ? `${analysis.claimIds.size} article${analysis.claimIds.size === 1 ? " contains" : "s contain"} a detected peak claim. Together they can only shift the estimate a limited amount, and older articles count for less.` : "None of these articles say when fossil fuels will peak, so the estimate uses the published outlooks only."}
                  </p>
                </div>
                <button className="text-button" onClick={() => openNews(true)}>See these articles <Icon name="arrow" size={16} /></button>
              </section>
              <div className="section-heading">
                <div>
                  <h2>Latest articles</h2>
                </div>
                <button className="text-button" onClick={() => openNews(false)}>View all articles <Icon name="arrow" size={16} /></button>
              </div>
              <ArticleFeed articles={analysis.articles} feedsById={analysis.feedsById} claimIds={analysis.claimIds} loading={articlesLoading} datasetEmpty={datasetEmpty} preview onReset={() => setFilters(DEFAULT_FILTERS)} />
            </>}

            {view === "news" && <>
              <div className="news-layout">
                <div>
                  <VolumeChart volume={analysis.volume} categories={analysis.categoriesInView} dim={loading} />
                </div>
                <section className="topics-card">
                  <h2>Top topics</h2>
                  <p>Click a topic to show only its articles.</p>
                  {topics.length ? topics.map(([topic, count]) => <button className="topic-row" key={topic} aria-pressed={filters.category === topic} onClick={() => setFilters((f) => ({ ...f, category: f.category === topic ? "all" : topic }))}>
                    <span>
                      {topic}
                    </span>
                    <span className="topic-track">
                      <i style={{ width: `${count / analysis.articles.length * 100}%` }} />
                    </span>
                    <strong>
                      {count}
                    </strong>
                    <Icon name="chevron" size={13} />
                  </button>) : <p className="note">No topics match these filters.</p>}
                  {filters.category !== "all" && <button className="text-button" onClick={() => setFilters((f) => ({ ...f, category: "all" }))}>Show all topics</button>}
                </section>
              </div>
              <ArticleFeed articles={analysis.articles} feedsById={analysis.feedsById} claimIds={analysis.claimIds} loading={articlesLoading} datasetEmpty={datasetEmpty} signalsOnly={signalsOnly} onSignalsChange={setSignalsOnly} onReset={() => { setFilters(DEFAULT_FILTERS); setSignalsOnly(false); }} />
            </>}

            {view === "sources" && <>
              <RegistryTable registry={analysis.registry} />
              <section className="method-note card" aria-label="How news enters the number">
      <p className="note">
        This forecasting prototype is still in development. Peak detection uses text patterns, and the
        news weights, registry inputs, and estimates still require validation. How news enters the
        experimental estimate: kept articles that make a directional claim about the fossil peak ("peaked
        in 2025", "nearing peak", "no peak before…") are blended as one pseudo-source, capped at half the weight
        of a top institution and decaying with a 60-day half-life. The registry of published outlooks carries the
        rest. Historical consumption is approximate (OWID / Energy Institute).
      </p>
              </section>
            </>}

          </div>
        </main>
      </div>
    </div>
  );
}
