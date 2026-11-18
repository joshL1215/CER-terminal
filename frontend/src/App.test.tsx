import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Dataset } from "./data/types";
import App from "./App";

const { loadDataset } = vi.hoisted(() => ({ loadDataset: vi.fn() }));
vi.mock("./data/client", () => ({
  isLiveConfigured: true,
  loadDataset,
  initialDataset: (): Dataset => ({ articles: [], feeds: [], totalArticles: 0, mode: "live", asOf: new Date() }),
}));
// jsdom has no layout engine. The actual chart cards and their data tables are
// exercised below; only the canvas sizing wrapper is omitted.
vi.mock("recharts", async (importOriginal) => ({
  ...await importOriginal<typeof import("recharts")>(),
  ResponsiveContainer: () => null,
}));

const dataset: Dataset = {
  mode: "live", asOf: new Date("2026-11-17T12:00:00Z"), totalArticles: 2,
  feeds: [{ id: "lab", name: "Pipeline laboratory", url: "https://lab.example/feed", category: "research", tags: ["science"] }],
  articles: [
    { id: 101, title: "Fossil fuels peak in 2030", url: "https://lab.example/fossil", description: "Pipeline summary", published_at: "2026-11-16T12:00:00Z", category: "research", feed_id: "lab" },
    { id: 102, title: "Hydrogen infrastructure expands", url: "https://lab.example/hydrogen", description: null, published_at: "2026-11-15T12:00:00Z", category: "hydrogen", feed_id: "lab" },
  ],
};

beforeEach(() => {
  loadDataset.mockReset();
  localStorage.clear();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
  vi.stubGlobal("scrollTo", vi.fn());
});
afterEach(cleanup);

describe("live pipeline dashboard", () => {
  it("uses the loaded rows for previews, topics, search, chart tables and signal controls", async () => {
    loadDataset.mockResolvedValue(dataset);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText("Live articles")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Fossil fuels peak in 2030" }).getAttribute("href")).toBe(dataset.articles[0].url);
    expect(screen.queryByText("Sample data")).toBeNull();
    await user.click(screen.getByRole("button", { name: "News intelligence" }));
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.getByRole("option", { name: "Hydrogen" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Show table: What the feed is talking about" }));
    const table = screen.getByRole("region", { name: "What the feed is talking about data table" });
    expect(within(table).getByRole("columnheader", { name: "hydrogen" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: /Peak signals 1/ }));
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Fossil fuels peak in 2030" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: /All articles 2/ }));
    await user.type(screen.getByRole("searchbox", { name: "Search articles" }), "hydrogen");
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Hydrogen infrastructure expands" })).toBeTruthy();
  });

  it("shows no sample evidence while loading or after an initial connection error", async () => {
    let rejectRequest!: (error: Error) => void;
    loadDataset.mockReturnValue(new Promise((_resolve, reject) => { rejectRequest = reject; }));
    render(<App />);
    expect(screen.getByText("Loading screened articles…")).toBeTruthy();
    expect(screen.queryAllByRole("article")).toHaveLength(0);
    expect(screen.queryByText("Sample data")).toBeNull();
    rejectRequest(new Error("Invalid API key"));
    expect(await screen.findByText("Connection unavailable")).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toContain("Check the connection settings");
    expect(screen.queryAllByRole("article")).toHaveLength(0);
  });

  it("combines dynamic pipeline topics with region and energy controls and clears them", async () => {
    loadDataset.mockResolvedValue({ ...dataset, articles: [
      { ...dataset.articles[0], title: "China expands solar generation", category: "renewables" },
      { ...dataset.articles[1], title: "Europe expands oil production", category: "renewables" },
    ] });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Live articles");
    await user.click(screen.getByRole("button", { name: "News intelligence" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Category" }), "renewables");
    await user.selectOptions(screen.getByRole("combobox", { name: "Region" }), "asia");
    await user.selectOptions(screen.getByRole("combobox", { name: "Energy type" }), "solar");
    await user.type(screen.getByRole("searchbox", { name: "Search articles" }), "science");
    expect(screen.getAllByRole("article")).toHaveLength(1);
    const article = screen.getByRole("article");
    expect(within(article).getByRole("link", { name: "China expands solar generation" })).toBeTruthy();
    expect(within(article).getByText("China")).toBeTruthy();
    expect(within(article).getByText("Solar")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect((screen.getByRole("combobox", { name: "Region" }) as HTMLSelectElement).value).toBe("all");
    expect((screen.getByRole("combobox", { name: "Energy type" }) as HTMLSelectElement).value).toBe("all");
  });

  it("retains loaded articles after a refresh fails and supports retry", async () => {
    loadDataset.mockResolvedValueOnce(dataset).mockRejectedValueOnce(new Error("Network unavailable")).mockResolvedValueOnce(dataset);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Live articles");
    await user.click(screen.getByRole("button", { name: "Refresh live articles" }));
    expect(await screen.findByText("Connection unavailable")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Fossil fuels peak in 2030" })).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toContain("Keeping the last loaded articles");
    await user.click(screen.getByRole("button", { name: /Try again/ }));
    await screen.findByText("Live articles");
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
