import type { CSSProperties } from "react";

export type IconName = "overview" | "news" | "sources" | "arrow" | "search" | "sun" | "moon" | "download" | "bookmark" | "signal" | "refresh" | "close" | "chevron" | "external" | "check";
const paths: Record<IconName, string> = {
  overview: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  news: "M4 4h16v16H4z M8 8h8 M8 12h8 M8 16h4",
  sources: "M12 3 3 7l9 4 9-4-9-4Z M3 12l9 4 9-4 M3 17l9 4 9-4",
  arrow: "M4 12h16 M14 6l6 6-6 6",
  search: "M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  sun: "M12 3V1 M12 23v-2 M3 12H1 M23 12h-2 M4 4l2 2 M18 18l2 2 M4 20l2-2 M18 6l2-2 M17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0",
  moon: "M21 13a9 9 0 0 1-10-10 9 9 0 1 0 10 10Z",
  download: "M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5",
  bookmark: "M6 3h12v18l-6-4-6 4V3Z",
  signal: "M3 17l6-6 4 4 8-11 M15 4h6v6",
  refresh: "M20 7a8 8 0 1 0 0 10 M20 3v5h-5",
  close: "m6 6 12 12 M6 18 18 6",
  chevron: "m9 5 7 7-7 7",
  external: "M14 3h7v7 M21 3 10 14 M10 3H3v18h18v-7",
  check: "m5 12 4 4L19 6",
};
export function Icon({ name, size = 18, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}>
    <path d={paths[name]} />
  </svg>;
}
