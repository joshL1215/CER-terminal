// Global fossil fuel primary energy consumption, TWh (approx. OWID / Energy
// Institute Statistical Review). Anchor points, linearly interpolated.

const ANCHORS: [number, number][] = [
  [1900, 5972], [1910, 9300], [1920, 11800], [1930, 13500], [1940, 16800], [1950, 20100],
  [1960, 30500], [1965, 37600], [1970, 50600], [1975, 57700], [1980, 66700], [1985, 71500],
  [1990, 77400], [1995, 81600], [2000, 89400], [2005, 104200], [2010, 117100],
  [2015, 126500], [2019, 136100], [2020, 131300], [2021, 137200], [2022, 138700],
  [2023, 139900], [2024, 141000],
];

export interface HistoryPoint {
  year: number;
  twh: number;
}

export const FOSSIL_HISTORY: HistoryPoint[] = (() => {
  const out: HistoryPoint[] = [];
  for (let i = 0; i < ANCHORS.length - 1; i++) {
    const [y0, v0] = ANCHORS[i];
    const [y1, v1] = ANCHORS[i + 1];
    for (let y = y0; y < y1; y++) out.push({ year: y, twh: v0 + ((v1 - v0) * (y - y0)) / (y1 - y0) });
  }
  out.push({ year: ANCHORS[ANCHORS.length - 1][0], twh: ANCHORS[ANCHORS.length - 1][1] });
  return out;
})();
