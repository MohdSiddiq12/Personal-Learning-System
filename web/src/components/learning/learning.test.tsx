import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest } from "@/lib/api";
import {
  getProgressStats,
  LessonReader,
  PathView,
  ProgressVisual,
} from "./learningViews";
import type { Topic, TopicLesson } from "./learningViews";
import { LearningLoop } from "./LearningLoop";

vi.mock("@/lib/api", () => ({ apiRequest: vi.fn() }));

const topics: Topic[] = [
  {
    id: "a", parent_id: null, kind: "topic", title: "First core idea",
    summary: "Summary", importance: 5, est_minutes: 8, position: 0,
    page_refs: [1], progress: { status: "understood" }, children: [],
  },
  {
    id: "b", parent_id: null, kind: "topic", title: "Second core idea",
    summary: "Summary", importance: 4, est_minutes: 12, position: 1,
    page_refs: [2], progress: { status: "learning" }, children: [],
  },
  {
    id: "c", parent_id: null, kind: "topic", title: "Optional detail",
    summary: "Summary", importance: 2, est_minutes: 30, position: 2,
    page_refs: [3], progress: { status: "new" }, children: [],
  },
];

const lesson: TopicLesson = {
  body: "A short lesson body.",
  recall_questions: [
    { question: "What is the first idea?", answer: "It is a grounded idea." },
    { question: "What can you try?", answer: "Try one small action." },
  ],
  action: "Apply this idea to one choice.",
};

describe("learning loop components", () => {
  beforeEach(() => vi.mocked(apiRequest).mockReset());

  it("shows path items in position order and separates optional topics", () => {
    render(
      <PathView
        topics={topics}
        items={[
          { topic_id: "b", position: 1, day_number: 1, is_optional: false },
          { topic_id: "a", position: 0, day_number: 1, is_optional: false },
          { topic_id: "c", position: 2, day_number: 1, is_optional: true },
        ]}
        onOpen={() => undefined}
      />,
    );
    const text = document.body.textContent ?? "";
    expect(text.indexOf("First core idea")).toBeLessThan(text.indexOf("Second core idea"));
    expect(screen.getByRole("heading", { name: "Optional topics" })).toBeTruthy();
    expect(screen.getByText("Optional detail")).toBeTruthy();
  });

  it("counts only importance four and above and labels the visual status", () => {
    expect(getProgressStats(topics)).toEqual({ understood: 1, total: 2 });
    render(<ProgressVisual topics={topics} />);
    expect(screen.getByText("Core ideas understood: 1 of 2")).toBeTruthy();
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("1");
    expect(screen.getByText("learning")).toBeTruthy();
  });

  it("keeps recall answers hidden until the learner reveals them", () => {
    render(
      <LessonReader
        lesson={lesson}
        topic={topics[0]}
        sourcePage={null}
        onSelectPage={() => undefined}
        onStatusChange={() => undefined}
        status="new"
        notes={[]}
        onSaveNote={async () => undefined}
        onSavePassage={async () => undefined}
      />,
    );
    expect(screen.queryByText("It is a grounded idea.")).toBeNull();
    fireEvent.click(screen.getAllByRole("button", { name: "Reveal answer" })[0]);
    expect(screen.getByText("It is a grounded idea.")).toBeTruthy();
    expect(screen.queryByText("Try one small action.")).toBeNull();
  });

  it("shows a friendly error when the learning map cannot load", async () => {
    vi.mocked(apiRequest).mockImplementation(async (path) => {
      const requestPath = String(path ?? "");
      if (requestPath.includes("/map")) throw new Error("The learning map could not be loaded.");
      if (requestPath.includes("/preferences")) return { minutes_per_topic: 10, daily_minutes: 30, goal: "understand" };
      if (requestPath.endsWith("/path")) return { items: [] };
      return [];
    });
    render(
      <LearningLoop
        bookId="book-1"
        accessToken="token"
        pages={[]}
        onSelectPage={() => undefined}
        refreshKey=""
      />,
    );
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("learning map"));
  });
});
