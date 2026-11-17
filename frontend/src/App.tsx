import { useCallback, useEffect, useMemo, useState } from "react";
import { ArticleFeed } from "./components/ArticleFeed";
import { FilterRow } from "./components/Filters";
import { Icon, type IconName } from "./components/Icon";
import { DistributionChart, HistoryChart, TimelineChart } from "./components/OutlookCharts";
import { RegistryTable } from "./components/RegistryTable";
import { StatTiles } from "./components/StatTiles";
import { VolumeChart } from "./components/VolumeChart";
import { isLiveConfigured, loadDataset, loadSample } from "./data/client";
import type { Dataset } from "./data/types";
import { analyze, DEFAULT_FILTERS, type Filters } from "./model/analysis";

type View = "overview" | "news" | "sources";
const NAV: { id: View; label: string; icon: IconName }[] = [{ id: "overview", label: "Overview", icon: "overview" }, { id: "news", label: "News intelligence", icon: "news" }, { id: "sources", label: "Sources & method", icon: "sources" }];
function readTheme(): "light" | "dark" {
  try { const value = localStorage.getItem("cer-theme"); if (value === "light" || value === "dark") return value; } catch { /* use the default */ }
  return "light";
}

export default function App() {
  const [dataset, setDataset] = useState<Dataset>(() => loadSample());
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
    setLoading(true);
    setError(null);
    loadDataset().then((d) => { if (!cancelled) setDataset(d); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Unable to load articles"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [refreshKey]);
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("cer-theme", theme); } catch { /* the toggle still works without storage */ }
  }, [theme]);

  const analysis = useMemo(() => analyze(dataset, filters), [dataset, filters]);
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
        <a className="brand" href="#" onClick={(e) => { e.preventDefault(); openView("overview"); }} aria-label="CER Terminal home">
          <span className="brand-mark">
            <span />
            <span />
            <span />
            <span />
          </span>
          <span>CER<span className="brand-light"> Terminal</span><small>ENERGY INTELLIGENCE</small></span>
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
          <span>Center for Energy Research</span>
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
              {loading ? "Updating articles…" : dataset.mode === "live" ? "Live articles" : "Sample data"}
            </span>
            <span className="as-of">As of {asOf}</span>
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
              <div className="eyebrow"><span /> THE FOSSIL FUEL PEAK OBSERVATORY</div>
              <h1 className={view === "overview" ? "outlook-title" : undefined}>
                {view === "overview" ? "When will fossil fuels peak?" : view === "news" ? "News intelligence" : "Sources & method"}
              </h1>
              <p>
                {view === "overview" ? "Track the outlook. Understand the uncertainty. Explore the evidence behind the shift." : view === "news" ? "Screened energy news, connected to the question that matters." : "Published outlooks and how news enters the number."}
              </p>
            </div>
            <span className="edition">CER / {dataset.asOf.getFullYear()}<span>ENERGY OUTLOOK</span></span>
          </div>

          {error && <div className="error" role="alert">
            <strong>Articles could not be refreshed.</strong>
            {dataset.mode === "sample" ? "Showing the sample snapshot." : "Keeping the last loaded articles."}
            <details>
              <summary>Connection details</summary>
              {error}
            </details>
            <button className="text-button" onClick={() => setRefreshKey((k) => k + 1)}>Try again <Icon name="refresh" size={14} /></button>
          </div>}

          {dataset.mode === "sample" && <div className="sample-notice">
            <span className="notice-symbol">i</span>
            <span><strong>You’re exploring a sample snapshot.</strong> Articles are from {asOf}. Connect live data when your project credentials are available.</span>
            <button className="text-button" onClick={() => openView("sources")}>About the data <Icon name="arrow" size={14} /></button>
          </div>}

          {view !== "sources" && <FilterRow filters={filters} feeds={dataset.feeds} count={analysis.articles.length} onChange={setFilters} />}

          <div className="view-content" key={view}>

            {view === "overview" && <>
              <div className="outlook-grid">
                <section className="forecast-panel" aria-label="Peak year estimate" aria-busy={loading}>
                  <div className="forecast-top">
                    <span className="eyebrow">THE CURRENT OUTLOOK</span>
                    <span className="forecast-tag">Model estimate</span>
                  </div>
                  <h2>Global fossil fuel peak</h2>
                  <div className="forecast-year" key={consensus.median.toFixed(1)}>
                    {consensus.median.toFixed(0)}
                    <span>median year</span>
                  </div>
                  <p className="forecast-range">Central 80% range <strong>{consensus.p10.toFixed(0)}–{consensus.p90.toFixed(0)}</strong></p>
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
                  <span className="eyebrow">BEYOND A SINGLE YEAR</span>
                  <h2>The shape of the outlook</h2>
                </div>
                <span className="section-aside">Uncertainty is part of the picture.</span>
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
                  <h3>What is the news telling us?</h3>
                  <p>
                    {analysis.nowcast ? `${analysis.claimIds.size} article${analysis.claimIds.size === 1 ? " contains" : "s contain"} a detected peak claim. Their combined influence is capped and fades with age.` : "No directional peak claims were detected in these articles. Broader energy coverage provides context without moving the estimate."}
                  </p>
                </div>
                <button className="text-button" onClick={() => openNews(true)}>Inspect the signals <Icon name="arrow" size={16} /></button>
              </section>
              <div className="section-heading">
                <div>
                  <span className="eyebrow">FROM THE NEWS DESK</span>
                  <h2>Latest intelligence</h2>
                </div>
                <button className="text-button" onClick={() => openNews(false)}>View all articles <Icon name="arrow" size={16} /></button>
              </div>
              <ArticleFeed articles={analysis.articles} feedsById={analysis.feedsById} claimIds={analysis.claimIds} preview onReset={() => setFilters(DEFAULT_FILTERS)} />
            </>}

            {view === "news" && <>
              <div className="news-layout">
                <div>
                  <div className="section-heading compact">
                    <div>
                      <span className="eyebrow">COVERAGE AT A GLANCE</span>
                      <h2>The conversation over time</h2>
                    </div>
                  </div>
                  <VolumeChart volume={analysis.volume} categories={analysis.categoriesInView} dim={loading} />
                </div>
                <section className="topics-card">
                  <span className="eyebrow">IN YOUR SELECTION</span>
                  <h2>Topics in focus</h2>
                  <p>Select a topic to explore its coverage.</p>
                  {topics.length ? topics.map(([topic, count]) => <button className="topic-row" key={topic} onClick={() => setFilters((f) => ({ ...f, category: f.category === topic ? "all" : topic }))}>
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
              <ArticleFeed articles={analysis.articles} feedsById={analysis.feedsById} claimIds={analysis.claimIds} signalsOnly={signalsOnly} onSignalsChange={setSignalsOnly} onReset={() => { setFilters(DEFAULT_FILTERS); setSignalsOnly(false); }} />
            </>}

            {view === "sources" && <>
              <RegistryTable registry={analysis.registry} />
              <section className="method-note card" aria-label="How news enters the number">
      <p className="note">
        How news enters the number: kept articles that make a directional claim about the fossil peak ("peaked
        in 2025", "nearing peak", "no peak before…") are blended as one pseudo-source, capped at half the weight
        of a top institution and decaying with a 60-day half-life. The registry of published outlooks carries the
        rest. Historical consumption is approximate (OWID / Energy Institute).
      </p>
              </section>
            </>}

          </div>
          <footer className="footer">
            <span><span className="footer-mark">CER</span> Energy intelligence, with perspective.</span>
            <span>Energy news, screened daily</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
