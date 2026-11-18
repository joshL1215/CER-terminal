# Frontend

React + Vite dashboard over the articles the ingest job keeps. It shows the screened news feed and reads it
against the question the Center cares about: **when does global fossil fuel consumption peak, and how does that
estimate move as news comes in?**

**Forecasting is a prototype still in development.** Peak-claim detection, news contributions,
peak-year estimates, probability distributions, and reconstructed forecast timelines are experimental
and require methodological validation. The current implementation uses text-pattern rules,
hand-selected weights, and a static source registry that includes placeholder entries.

Article collection and browsing features are implemented and tested. Live Supabase verification and
deployment are still pending. Article coverage charts report counts from the loaded dataset;
forecast charts display experimental model outputs.

## Run it

```sh
cd frontend
npm install
npm run dev          # http://localhost:5173, bundled sample data
```

To read live data, copy `.env.example` to `.env.local` and fill in the project's Supabase URL and anon key
(Supabase → Project Settings → Data API). The anon key is public by design: the database only exposes
kept articles and active feeds to it (see [`packages/db/README.md`](../packages/db/README.md)). With no
live settings the app runs on `src/data/sample.json`, a snapshot of real harvested articles. Setting only
one variable is reported as a connection error. Restart Vite after changing local settings.

```sh
npm run build        # type-check + production build to dist/
npm run preview
npm test             # data access, article controls, and analysis regression tests
```

## GitHub build settings

In the repository's **Settings → Secrets and variables → Actions**, add these two secrets
(repository variables also work):

| Name | Value |
| --- | --- |
| `VITE_SUPABASE_URL` | Supabase project URL, e.g. `https://your-project-ref.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Public anon key for that same Supabase project |

The [Frontend workflow](../.github/workflows/frontend.yml) runs tests, injects those settings into
the Vite production build, and uploads `frontend-dist` as a downloadable Actions artifact. It can
also be run manually. This builds the app; hosting/deployment is a separate step. Vite reads these
settings **at build time**, so rebuild after changing them. Fork PRs without secrets build in sample mode.

The ingest workflow continues using `DATABASE_URL` and the LLM settings. Never put a database
connection string or service-role key into a `VITE_` setting. Apply the existing database migrations
before using the frontend; public reads depend on their RLS policies and column grants.

## Client workspace

- **Overview** — median peak year and central 80% range, consumption history, probability distribution,
  reconstructed consensus timeline, and a three-article news preview. Toggle **Include news signals**
  to compare the registry-only estimate with the news-adjusted estimate. Click the source, article,
  or signal tiles to open the supporting evidence.
- **News intelligence** — coverage by week, topic shortcuts, and an article explorer. Expand article
  summaries, filter to peak signals, bookmark articles, sort by date, load more, or export the current
  selection as CSV. Saved articles stay in this browser; they do not sync to an account.
- **Sources & method** — the original major-source registry, with the same columns, positions,
  source notes, and methodology wording, presented in the updated layout.

Articles also carry **region** and **energy-type** tags (`src/model/tags.ts`), found by plain keyword rules on
the title and summary, with no AI. They power the Region and Energy type filters, the chips on each article, and two
extra CSV columns. A tag means the article *mentions* that place or energy type, not that it is mainly about it.
Edit the patterns in `tags.ts` to change what counts.

The global search (title, summary, source name, topic, and source tags), date range, topic, region,
energy-type, and source filters change the article slice and its contribution
into the forecast. The static registry remains fixed. Saved/signal filters and sorting inside the
article list only change that list; the UI labels this distinction. Dates are relative to the dataset's
as-of date so sample snapshots remain usable.

Every chart has a **Table** view. The interface supports narrow screens, keyboard focus, light/dark
appearance, and reduced-motion preferences. Sample snapshots, initial loading, empty pipelines,
and failed live refreshes are labeled. Failed refreshes retain previously loaded live articles;
an initial connection failure displays no sample articles.

## How the number is built (`src/model/`)

1. **`registry.ts`** — hand-curated published peak-year positions. One voice per org/scenario; the newest
   edition wins (`cleanRegistry`). "No peak before 2050" positions are kept as right-censored, not dropped.
2. **`nowcast.ts`** — kept articles whose title/description make a directional claim ("peaked in 2025",
   "nearing peak", "no peak…") become one **media nowcast** pseudo-source: recency-weighted (60-day
   half-life), capped at weight 0.5 (half a top institution). News moves the number between report
   vintages; it can never outvote the registry, and it decays on its own once the majors publish.
3. **`consensus.ts`** — credibility-weighted Monte-Carlo blend (seeded, so renders are stable).
4. **`timeline.ts`** — the same blend recomputed week by week over the article history.
5. **`analysis.ts`** — one function from (dataset, filters) to everything the page renders.

The registry and the historical consumption series are static data in this folder for now; moving them
into tables (and letting the ingest job's LLM extract peak claims instead of the regex in `nowcast.ts`)
is the natural next step.

## Data access

`src/data/client.ts` reads `articles` and `feeds` through `@supabase/supabase-js`, listing columns
explicitly because the RLS grants are per column (`select=*` is rejected). RLS exposes only kept
articles from active feeds; queries do not filter on the private `status` or `active` columns.
Both tables are paginated, including when the project's API row limit is below 1000. Articles use
publication date then ID for deterministic newest-first ordering, up to 5000 rows. If more rows
exist, the UI discloses that search, charts, saved selections, and exports use the loaded subset.
Topic choices come from the article data so new pipeline categories appear automatically.

If live mode is empty, check that the ingest job has classified articles as `kept` and their feeds
are active. Fetch-only runs (`--skip-classify`) leave new articles `pending`, which are intentionally
invisible to the frontend. Connection errors expose details and a retry control; check that the
Data API is enabled and the URL/key belong to the migrated project.
