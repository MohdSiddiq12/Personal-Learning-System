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
import { LearningLoop, validateCustomMinutes } from "./LearningLoop";
import { ShelfBookCard } from "./ShelfBookCard";

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
    page_refs: [2], support: "weak", progress: { status: "learning" }, children: [],
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
          { topic_id: "a", position: 0, day_number: 1, is_optional: false, minutes_allocated: 5, is_condensed: true },
          { topic_id: "c", position: 2, day_number: 1, is_optional: true },
        ]}
        onOpen={() => undefined}
      />,
    );
    const text = document.body.textContent ?? "";
    expect(text.indexOf("First core idea")).toBeLessThan(text.indexOf("Second core idea"));
    expect(screen.getByText("Bonus topics (1)")).toBeTruthy();
    expect(screen.getByText("Optional detail")).toBeTruthy();
    expect(screen.getByText("Short version")).toBeTruthy();
    expect(screen.getByText("Check the source")).toBeTruthy();
    expect(screen.getByText("Day 1, 5 min")).toBeTruthy();
  });

  it("counts only importance four and above and labels the visual status", () => {
    expect(getProgressStats(topics)).toEqual({ understood: 1, total: 2 });
    render(<ProgressVisual topics={topics} />);
    expect(screen.getByText("Key ideas understood: 1 of 2 (50%)")).toBeTruthy();
    expect(screen.getAllByRole("progressbar")[1].getAttribute("aria-valuenow")).toBe("50");
    expect(screen.getByText("learning")).toBeTruthy();
  });

  it("keeps recall answers hidden until the learner reveals them", () => {
    render(
      <LessonReader
        lesson={lesson}
        topic={topics[0]}
        sourcePages={[]}
        onStatusChange={() => undefined}
        status="new"
        notes={[]}
        onSaveNote={async () => undefined}
        onSavePassage={async () => undefined}
        onComplete={async () => undefined}
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
      if (requestPath.includes("/progress")) return { path_percent: 0, core_percent: 0, topics_total: 0, topics_understood: 0 };
      return [];
    });
    render(
      <LearningLoop
        bookId="book-1"
        accessToken="token"
        pages={[]}
        refreshKey=""
      />,
    );
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("learning map"));
  });

  it("validates custom daily minutes at the requested boundaries", () => {
    expect(validateCustomMinutes("")).toContain("Enter");
    expect(validateCustomMinutes("4")).toContain("at least 5");
    expect(validateCustomMinutes("5")).toBe("");
    expect(validateCustomMinutes("15")).toBe("");
    expect(validateCustomMinutes("180")).toBe("");
    expect(validateCustomMinutes("181")).toContain("no more than 180");
    expect(validateCustomMinutes("15.5")).toContain("whole number");
  });

  it("shows an answer reveal button and self-check text without grading", () => {
    render(<LessonReader lesson={lesson} topic={topics[0]} sourcePages={[]} onStatusChange={() => undefined} status="new" notes={[]} onSaveNote={async () => undefined} onSavePassage={async () => undefined} onComplete={async () => undefined} />);
    expect(screen.getByText("This is a self-check. Your answers are not graded.")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Reveal answer" })).toHaveLength(2);
  });

  it("counts zero core topics safely and excludes review from understood", () => {
    const reviewOnly = [{ ...topics[2], importance: 4, progress: { status: "review" as const } }];
    expect(getProgressStats(reviewOnly)).toEqual({ understood: 0, total: 1 });
    expect(getProgressStats([])).toEqual({ understood: 0, total: 0 });
    render(<ProgressVisual topics={reviewOnly} />);
    expect(screen.getByText("Key ideas understood: 0 of 1 (0%)")).toBeTruthy();
  });

  it("does not start a map job until a mode is selected and consent is checked", async () => {
    vi.mocked(apiRequest).mockImplementation(async (path) => {
      const requestPath = String(path ?? "");
      if (requestPath.endsWith("/map")) return { topics: [], summary: null };
      if (requestPath.endsWith("/active-job")) return null;
      if (requestPath.endsWith("/preferences")) return { ...{ minutes_per_topic: 10, daily_minutes: 30, goal: "understand" } };
      if (requestPath.endsWith("/path")) return { items: [] };
      if (requestPath.endsWith("/progress")) return { path_percent: 0, core_percent: 0, topics_total: 0, topics_understood: 0 };
      return [];
    });
    render(<LearningLoop bookId="book-1" accessToken="token" pages={[]} refreshKey="" />);
    await screen.findByRole("heading", { name: "What would you like to do with this book?" });
    fireEvent.click(screen.getByRole("button", { name: /Customize my learning path/ }));
    const create = screen.getByRole("button", { name: "Create my learning map" });
    expect(create).toHaveProperty("disabled", true);
    fireEvent.click(screen.getByRole("checkbox"));
    expect(create).toHaveProperty("disabled", false);
    expect(vi.mocked(apiRequest).mock.calls.some(([path]) => String(path).includes("map-jobs"))).toBe(false);
  });

  it("shows only the lesson's cited source pages and sends completion result to the caller", async () => {
    const onComplete = vi.fn(async () => undefined);
    render(<LessonReader lesson={lesson} topic={topics[0]} sourcePages={[
      { page_number: 1, text: "Cited text", char_count: 10, is_empty: false, has_images: false },
    ]} onStatusChange={() => undefined} status="new" notes={[]} onSaveNote={async () => undefined} onSavePassage={async () => undefined} onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Check the source (1 cited pages)"));
    expect(screen.getByText("Cited text")).toBeTruthy();
    expect(screen.queryByText("Uncited text")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Need review" }));
    expect(onComplete).toHaveBeenCalledWith("review");
    fireEvent.click(screen.getByRole("button", { name: "Got it" }));
    expect(onComplete).toHaveBeenCalledWith("understood");
  });

  it("sends lesson completion to the API and displays only cited pages", async () => {
    const topic = { ...topics[0], page_refs: [1] };
    vi.mocked(apiRequest).mockImplementation(async (path) => {
      const requestPath = String(path ?? "");
      if (requestPath.endsWith("/map")) return { topics: [topic], summary: null };
      if (requestPath.endsWith("/preferences")) return defaultsForTest;
      if (requestPath.endsWith("/path")) return { items: [{ id: "path-item-1", topic_id: "a", position: 0, day_number: 1, is_optional: false, minutes_allocated: 5 }] };
      if (requestPath.endsWith("/notes") || requestPath.endsWith("/highlights")) return [];
      if (requestPath.endsWith("/progress")) return { path_percent: 0, core_percent: 0, topics_total: 1, topics_understood: 0 };
      if (requestPath.endsWith("/active-job")) return null;
      if (requestPath.includes("/lesson?")) return { ...lesson, target_minutes: 5 };
      return {};
    });
    render(<LearningLoop bookId="book-1" accessToken="token" pages={[
      { page_number: 1, text: "Cited page text", char_count: 15, is_empty: false, has_images: false },
      { page_number: 2, text: "Uncited page text", char_count: 17, is_empty: false, has_images: false },
    ]} refreshKey="" />);
    await screen.findByRole("heading", { name: "Your learning loop" });
    fireEvent.click(screen.getAllByRole("button", { name: /First core idea/ })[0]);
    await screen.findByRole("heading", { name: "First core idea", level: 3 });
    fireEvent.click(screen.getByText("Check the source (1 cited pages)"));
    expect(screen.getByText("Cited page text")).toBeTruthy();
    expect(screen.queryByText("Uncited page text")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Got it" }));
    await waitFor(() => expect(vi.mocked(apiRequest).mock.calls.some(([path, , options]) => String(path).includes("/path-items/path-item-1/complete") && options?.body === JSON.stringify({ status: "understood" }))).toBe(true));
    expect(await screen.findByText("Today's session is done.")).toBeTruthy();
  });

  it("offers the next same-day topic and reuses its prefetched cached lesson", async () => {
    const pathItems = [
      { id: "path-item-a", topic_id: "a", position: 0, day_number: 1, is_optional: false, minutes_allocated: 5 },
      { id: "path-item-b", topic_id: "b", position: 1, day_number: 1, is_optional: false, minutes_allocated: 10 },
    ];
    vi.mocked(apiRequest).mockImplementation(async (path) => {
      const requestPath = String(path ?? "");
      if (requestPath.endsWith("/map")) return { topics: topics.slice(0, 2), summary: null };
      if (requestPath.endsWith("/preferences")) return defaultsForTest;
      if (requestPath.endsWith("/path")) return { items: pathItems };
      if (requestPath.endsWith("/notes") || requestPath.endsWith("/highlights")) return [];
      if (requestPath.endsWith("/progress")) return { path_percent: 0, core_percent: 0, topics_total: 2, topics_understood: 0 };
      if (requestPath.endsWith("/active-job")) return null;
      if (requestPath.includes("/lesson?")) return lesson;
      return {};
    });
    render(<LearningLoop bookId="book-1" accessToken="token" pages={[]} refreshKey="" />);
    await screen.findByRole("heading", { name: "Your learning loop" });
    fireEvent.click(screen.getAllByRole("button", { name: /First core idea/ })[0]);
    await screen.findByRole("heading", { name: "First core idea", level: 3 });
    fireEvent.click(screen.getByRole("button", { name: "Got it" }));
    const nextButton = await screen.findByRole("button", { name: "Next topic" });
    expect(vi.mocked(apiRequest).mock.calls.some(([path]) => String(path).includes("/topics/b/lesson?target_minutes=10"))).toBe(true);
    fireEvent.click(nextButton);
    expect(await screen.findByRole("heading", { name: "Second core idea", level: 3 })).toBeTruthy();
    expect(vi.mocked(apiRequest).mock.calls.filter(([path]) => String(path).includes("/topics/b/lesson?target_minutes=10"))).toHaveLength(1);
  });

  it("shows every shelf progress field and opens the selected book", () => {
    const onSelect = vi.fn();
    render(<ShelfBookCard book={{ id: "book-1", title: "A useful book", page_count: 120, path_percent: 25, topics_understood: 1, topics_total: 4, next_day: 2, next_minutes: 10 }} index={0} selected onSelect={onSelect} />);
    expect(screen.getByRole("progressbar", { name: "A useful book path progress" }).getAttribute("aria-valuenow")).toBe("25");
    expect(screen.getByText("Core ideas 1 of 4")).toBeTruthy();
    expect(screen.getByText("Continue Day 2, 10 min")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /A useful book/ }));
    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("selects preset time options and validates a custom time in the flow", async () => {
    vi.mocked(apiRequest).mockImplementation(async (path) => {
      const requestPath = String(path ?? "");
      if (requestPath.endsWith("/map")) return { topics: [], summary: null };
      if (requestPath.endsWith("/active-job")) return null;
      if (requestPath.endsWith("/preferences")) return { ...defaultsForTest };
      if (requestPath.endsWith("/path")) return { items: [] };
      if (requestPath.endsWith("/progress")) return { path_percent: 0, core_percent: 0, topics_total: 0, topics_understood: 0 };
      return { id: "job-1", kind: "map", status: "queued", step: "queued", progress_pct: 0, total_chunks: 1, done_chunks: 0, error_code: null, error_message: null };
    });
    render(<LearningLoop bookId="book-1" accessToken="token" pages={[]} refreshKey="" />);
    await screen.findByRole("heading", { name: "What would you like to do with this book?" });
    fireEvent.click(screen.getByRole("button", { name: /Customize my learning path/ }));
    const fiveMinutes = screen.getByRole("radio", { name: "5 minutes" }) as HTMLInputElement;
    fireEvent.click(fiveMinutes);
    expect(fiveMinutes.checked).toBe(true);
    for (const label of ["10 minutes", "30 minutes", "1 hour"]) {
      const option = screen.getByRole("radio", { name: label }) as HTMLInputElement;
      fireEvent.click(option);
      expect(option.checked).toBe(true);
    }
    fireEvent.click(screen.getByRole("radio", { name: "Custom" }));
    const custom = screen.getByRole("spinbutton", { name: /Custom minutes/ }) as HTMLInputElement;
    fireEvent.change(custom, { target: { value: "4" } });
    expect(screen.getByRole("alert").textContent).toContain("at least 5");
    fireEvent.change(custom, { target: { value: "15" } });
    expect(screen.queryByRole("alert")).toBeNull();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Create my learning map" }));
    await waitFor(() => expect(vi.mocked(apiRequest).mock.calls.some(([path]) => String(path).endsWith("/map-jobs"))).toBe(true));
  });

  it("resumes an active map job and offers retry for a rate limited failure", async () => {
    vi.mocked(apiRequest).mockImplementation(async (path) => {
      const requestPath = String(path ?? "");
      if (requestPath.endsWith("/map")) return { topics: [], summary: null };
      if (requestPath.endsWith("/active-job")) return { id: "job-1", kind: "map", status: "failed", step: "waiting", progress_pct: 50, total_chunks: 2, done_chunks: 1, error_code: "rate_limited", error_message: "Busy" };
      if (requestPath.endsWith("/preferences")) return defaultsForTest;
      if (requestPath.endsWith("/path")) return { items: [] };
      if (requestPath.endsWith("/progress")) return { path_percent: 0, core_percent: 0, topics_total: 0, topics_understood: 0 };
      return { id: "job-1", kind: "map", status: "queued", step: "queued", progress_pct: 50, total_chunks: 2, done_chunks: 1, error_code: null, error_message: null };
    });
    render(<LearningLoop bookId="book-1" accessToken="token" pages={[]} refreshKey="" />);
    await screen.findByText("Busy, waiting about 2 seconds before checking again.");
    expect(screen.getByRole("progressbar", { name: "Learning map progress" }).getAttribute("aria-valuenow")).toBe("50");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(vi.mocked(apiRequest).mock.calls.some(([path]) => String(path).endsWith("/retry"))).toBe(true));
  });

  it("explains an exhausted generation budget without offering a retry", async () => {
    vi.mocked(apiRequest).mockImplementation(async (path) => {
      const requestPath = String(path ?? "");
      if (requestPath.endsWith("/map")) return { topics: [], summary: null };
      if (requestPath.endsWith("/active-job")) return { id: "job-1", kind: "map", status: "failed", step: "failed", progress_pct: 0, total_chunks: 1, done_chunks: 0, error_code: "budget_exhausted", error_message: "Daily capacity reached. Please try again tomorrow." };
      if (requestPath.endsWith("/preferences")) return defaultsForTest;
      if (requestPath.endsWith("/path")) return { items: [] };
      if (requestPath.endsWith("/progress")) return { path_percent: 0, core_percent: 0, topics_total: 0, topics_understood: 0 };
      return [];
    });
    render(<LearningLoop bookId="book-1" accessToken="token" pages={[]} refreshKey="" />);
    await screen.findByText("Daily capacity reached. Please try again tomorrow.");
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });
});

const defaultsForTest = { minutes_per_topic: 10, daily_minutes: 30, goal: "understand" as const };
