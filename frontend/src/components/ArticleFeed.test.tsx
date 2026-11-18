import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Article, Feed } from "../data/types";
import { ArticleFeed } from "./ArticleFeed";

const feed: Feed = { id: "lab", name: "Energy Laboratory", url: "https://news.example/rss", category: "research", tags: [] };
const articles: Article[] = Array.from({ length: 14 }, (_, i) => ({
  id: 14 - i, url: `https://news.example/${14 - i}`, title: `Report ${14 - i}`,
  description: `Summary ${14 - i}`, published_at: `2026-11-${String(17 - i).padStart(2, "0")}T12:00:00Z`, category: "research", feed_id: feed.id,
}));
const props = { articles, feedsById: new Map([[feed.id, feed]]), claimIds: new Map([[14, 2030]]), onReset: vi.fn() };

beforeEach(() => localStorage.clear());
afterEach(cleanup);

describe("article controls using pipeline rows", () => {
  it("displays source, URL, summary, peak signals, pagination and sorting", async () => {
    const user = userEvent.setup();
    render(<ArticleFeed {...props} />);
    expect(screen.getAllByRole("article")).toHaveLength(12);
    const first = screen.getAllByRole("article")[0];
    expect(within(first).getByRole("link", { name: "Report 14" }).getAttribute("href")).toBe("https://news.example/14");
    expect(within(first).getByText("Energy Laboratory")).toBeTruthy();
    expect(within(first).getByText("Peak signal · 2030")).toBeTruthy();
    await user.click(within(first).getByText("Read summary"));
    expect(within(first).getByText("Summary 14")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: /Load 12 more/ }));
    expect(screen.getAllByRole("article")).toHaveLength(14);
    await user.selectOptions(screen.getByLabelText("Article sort order"), "oldest");
    expect(within(screen.getAllByRole("article")[0]).getByRole("link").textContent).toBe("Report 1");
  });

  it("persists saved URLs across remounts and filters the saved selection", async () => {
    const user = userEvent.setup();
    const view = render(<ArticleFeed {...props} />);
    await user.click(screen.getByRole("button", { name: "Save article: Report 14" }));
    expect(JSON.parse(localStorage.getItem("cer-saved-articles")!)).toEqual(["https://news.example/14"]);
    view.unmount();
    render(<ArticleFeed {...props} />);
    await user.click(screen.getByRole("button", { name: "Saved" }));
    expect(screen.getAllByRole("article")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Unsave article: Report 14" }));
    expect(screen.queryAllByRole("article")).toHaveLength(0);
    expect(screen.getByText("No saved articles in this selection")).toBeTruthy();
  });

  it("exports the entire filtered selection, including unloaded list pages", async () => {
    const createObjectURL = vi.fn((_blob: Blob) => "blob:test-export");
    vi.stubGlobal("URL", class extends URL { static createObjectURL = createObjectURL; static revokeObjectURL = vi.fn(); });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<ArticleFeed {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "Export CSV" }));
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const csv = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.readAsText(blob);
    });
    expect(csv).toContain('"Report 14","Energy Laboratory"');
    expect(csv).toContain('"Report 1","Energy Laboratory"');
    expect(csv).toContain('"2030","https://news.example/14"');
    expect(csv.split("\r\n")).toHaveLength(15);
  });

  it("shows loading and pipeline-empty states independently of filter misses", () => {
    const view = render(<ArticleFeed {...props} articles={[]} loading />);
    expect(screen.getByRole("heading", { name: "Loading screened articles…" })).toBeTruthy();
    expect(screen.queryByText("No articles found")).toBeNull();
    view.rerender(<ArticleFeed {...props} articles={[]} datasetEmpty />);
    expect(screen.getByText("No screened articles available yet")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Reset filters" })).toBeNull();
    view.rerender(<ArticleFeed {...props} articles={[]} />);
    expect(screen.getByText("No articles found")).toBeTruthy();
  });
});
