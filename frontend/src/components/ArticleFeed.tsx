import { useEffect, useMemo, useState } from "react";
import type { Article, Feed } from "../data/types";
import { OTHER } from "../model/analysis";
import { Icon } from "./Icon";
import { categoryColor } from "./VolumeChart";

interface Props {
  articles: Article[];
  feedsById: Map<string, Feed>;
  claimIds: Map<number, number>;
  preview?: boolean;
  loading?: boolean;
  datasetEmpty?: boolean;
  signalsOnly?: boolean;
  onSignalsChange?: (value: boolean) => void;
  onReset: () => void;
}
const SAVED_KEY = "cer-saved-articles";
function readSaved(): string[] {
  try { const value: unknown = JSON.parse(localStorage.getItem(SAVED_KEY) ?? "[]"); return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : []; } catch { return []; }
}
function formatDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "Date unavailable";
}
function csvCell(value: string | number): string {
  const text = String(value);
  return `"${(/^[=+@\-\t\r]/.test(text) ? "'" + text : text).replace(/"/g, '""')}"`;
}
export function ArticleFeed({ articles, feedsById, claimIds, preview = false, loading = false, datasetEmpty = false, signalsOnly = false, onSignalsChange, onReset }: Props) {
  const [saved, setSaved] = useState(readSaved);
  const [savedOnly, setSavedOnly] = useState(false);
  const [oldestFirst, setOldestFirst] = useState(false);
  const [limit, setLimit] = useState(12);
  const [storageError, setStorageError] = useState(false);
  useEffect(() => { setLimit(12); }, [articles, signalsOnly, savedOnly, oldestFirst]);
  // Also update the preview when articles are saved in another tab.
  useEffect(() => { const sync = (event: StorageEvent) => { if (event.key === SAVED_KEY) setSaved(readSaved()); }; window.addEventListener("storage", sync); return () => window.removeEventListener("storage", sync); }, []);
  const toggleSaved = (url: string) => {
    const next = saved.includes(url) ? saved.filter((s) => s !== url) : [...saved, url];
    setSaved(next);
    try { localStorage.setItem(SAVED_KEY, JSON.stringify(next)); setStorageError(false); } catch { setStorageError(true); }
  };
  const visible = useMemo(() => {
    const result = articles.filter((a) => (!signalsOnly || claimIds.has(a.id)) && (!savedOnly || saved.includes(a.url)));
    return oldestFirst ? [...result].reverse() : result;
  }, [articles, claimIds, signalsOnly, savedOnly, saved, oldestFirst]);
  const exportArticles = () => {
    const rows = [["Title", "Source", "Published", "Topic", "Prototype detected peak year", "URL"], ...visible.map((a) => [a.title, feedsById.get(a.feed_id)?.name ?? a.feed_id, a.published_at ?? "", a.category ?? OTHER, claimIds.get(a.id) ?? "", a.url])];
    const url = URL.createObjectURL(new Blob(["\uFEFF", rows.map((r) => r.map(csvCell).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8;" }));
    const link = document.createElement("a"); link.href = url; link.download = "cer-energy-intelligence.csv"; document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <section className={`article-section${preview ? " preview-feed" : ""}`} aria-label={preview ? "Latest articles" : "News articles"} aria-busy={loading}>

    {!preview && <div className="feed-toolbar">
      <div className="feed-controls">
        <button className={`filter-chip${!savedOnly && !signalsOnly ? " selected" : ""}`} aria-pressed={!savedOnly && !signalsOnly} onClick={() => { setSavedOnly(false); onSignalsChange?.(false); }}>All articles <span>
          {articles.length}
        </span></button>
        <button className={`filter-chip${signalsOnly ? " selected" : ""}`} aria-pressed={signalsOnly} onClick={() => onSignalsChange?.(!signalsOnly)}><Icon name="signal" size={15} /> Peak signals <span>
          {claimIds.size}
        </span></button>
        <button className={`filter-chip${savedOnly ? " selected" : ""}`} aria-pressed={savedOnly} onClick={() => setSavedOnly((v) => !v)}><Icon name="bookmark" size={14} /> Saved</button>
      </div>
      <div className="feed-actions">
        <select aria-label="Article sort order" value={oldestFirst ? "oldest" : "newest"} onChange={(e) => setOldestFirst(e.target.value === "oldest")}>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
        <button className="ghost" onClick={exportArticles} disabled={!visible.length}><Icon name="download" size={15} /> Export CSV</button>
      </div>
    </div>}

    {!preview && <p className="note">Peak signals are a prototype still in development. Detected claims and their forecast contributions require validation.</p>}

    {!preview && <div className="feed-count" role="status">{visible.length} article{visible.length === 1 ? "" : "s"}{signalsOnly || savedOnly ? ` · ${[signalsOnly && "peak signals", savedOnly && "saved in this browser"].filter(Boolean).join(" · ")}` : " · selected evidence"}<span>These list controls do not change the forecast.</span></div>}

    {storageError && <p className="note" role="status">Browser storage is unavailable. Saved articles will last for this visit only.</p>}

    {loading && !articles.length ? <div className="empty" role="status"><h3>Loading screened articles…</h3><p>Fetching the latest available news.</p></div> : !visible.length ? <div className="empty">
      <span className="empty-icon">
        <Icon name={savedOnly ? "bookmark" : "search"} size={26} />
      </span>
      <h3>
        {datasetEmpty ? "No screened articles available yet" : savedOnly ? "No saved articles in this selection" : signalsOnly ? "No peak signals in this selection" : "No articles found"}
      </h3>
      <p>
        {datasetEmpty ? "Articles appear here after the collection pipeline keeps them from active sources." : savedOnly ? "Use the bookmark beside an article to save it, or broaden your filters." : "Try another topic, a wider date range, or a different search."}
      </p>
      {!datasetEmpty && <button className="ghost" onClick={() => { setSavedOnly(false); onSignalsChange?.(false); onReset(); }}>Reset filters</button>}
    </div> : <div className="feed">
      {visible.slice(0, preview ? 3 : limit).map((a) => {
        const cat = a.category ?? OTHER;
        const claim = claimIds.get(a.id);
        const isSaved = saved.includes(a.url);
        return <article className="article" key={a.url}>
          <div className="article-accent" style={{ background: categoryColor(cat) }} />
          <div className="article-body">
            <div className="article-topline">
              <span className="source-name">
                {feedsById.get(a.feed_id)?.name ?? a.feed_id}
              </span>
              <span className="meta-date">
                {formatDate(a.published_at)}
              </span>
              <button className={`bookmark-button${isSaved ? " saved" : ""}`} aria-pressed={isSaved} aria-label={`${isSaved ? "Unsave" : "Save"} article: ${a.title}`} onClick={() => toggleSaved(a.url)}>
                <Icon name="bookmark" size={17} />
              </button>
            </div>
            <h3>
              <a href={a.url} target="_blank" rel="noopener noreferrer">
                {a.title}
                <Icon name="external" size={15} />
              </a>
            </h3>
            <div className="article-tags">
              <span className="topic-label">
                <span className="swatch" style={{ background: categoryColor(cat) }} />
                {cat}
              </span>
              {claim !== undefined && <span className="chip signal" title="Prototype peak detection — still in development; review the source before relying on it"><Icon name="signal" size={13} /> Peak signal · {claim}</span>}
            </div>

            {a.description && <details className="article-details">
              <summary>Read summary <Icon name="chevron" size={12} /></summary>
              <p>
                {a.description}
              </p>
              {claim !== undefined && <p className="claim-note">A prototype text rule detected this peak claim. Detection and forecast contributions are still in development and require validation against the source.</p>}
            </details>}

          </div>
        </article>;
      })}
    </div>}

    {!preview && visible.length > limit && <div className="load-more">
      <span>Showing {Math.min(limit, visible.length)} of {visible.length} articles</span>
      <button className="ghost" onClick={() => setLimit((n) => n + 12)}>Load 12 more <Icon name="chevron" size={14} /></button>
    </div>}

  </section>;
}
