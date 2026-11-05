# Frontend

React + Vite dashboard over the articles the ingest job keeps. It shows the screened news feed and reads it
against the question the Center cares about: **when does global fossil fuel consumption peak, and how does that
estimate move as news comes in?**

## Run it

```sh
cd frontend
npm install
npm run dev          # http://localhost:5173, bundled sample data
```

To read live data, copy `.env.example` to `.env` and fill in the project's Supabase URL and anon key
(Supabase → Project Settings → Data API). The anon key is public by design: the database only exposes
kept articles and active feeds to it (see [`packages/db/README.md`](../packages/db/README.md)). With no
`.env` the app runs on `src/data/sample.json`, a snapshot of real harvested articles, so it always renders.

```sh
npm run build        # type-check + production build to dist/
npm run preview
```

## What's on the page

| Section | What it shows |
| --- | --- |
| Filter row | Date range, category, source, search. Scopes **everything** below it, so all numbers agree. |
| Stat tiles | Consensus peak year (the hero figure), P(peak ≤ 2030), sources blended, articles in view, peak claims found in the news. |
| Consumption chart | 1900–2024 global fossil energy with the consensus p10–p90 window and median overlaid. |
| Distribution | Probability of each peak year from the weighted Monte-Carlo blend. |
| Consensus over time | Weekly median as kept articles accumulated: registry-only vs. with the media nowcast. This is the "updation over time" view. |
| Volume | Kept articles per week, stacked by `rules.yaml` category. |
| Kept articles | The feed itself. Articles that make a directional peak claim get a **▲ peak signal** chip. |
| Registry | The curated published positions (IEA, DNV, BP, OPEC, …) behind the consensus, with weights. |

Every chart has a **Table** toggle, so no value is reachable only by hovering.

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
explicitly because the RLS grants are per column (`select=*` is rejected). Pagination is in pages of
1000 up to 5000 articles.
