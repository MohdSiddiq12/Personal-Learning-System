"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { apiRequest, type BookPage } from "@/lib/api";
import {
  LessonReader,
  PathView,
  ProgressVisual,
  TopicTree,
} from "./learningViews";
import type {
  LearningGoal,
  PathItem,
  SavedNote,
  Topic,
  TopicLesson,
  TopicStatus,
} from "./learningViews";

type Preferences = {
  minutes_per_topic: number;
  daily_minutes: number;
  goal: LearningGoal;
};
type SavedHighlight = {
  id: string;
  topic_id: string | null;
  page: number;
  text: string;
  note: string;
};
const defaults: Preferences = { minutes_per_topic: 10, daily_minutes: 30, goal: "understand" };

function InlineError({ message }: { message: string }) {
  return <p className="learning-error" role="alert">{message}</p>;
}

export function LearningLoop({
  bookId,
  accessToken,
  pages,
  onSelectPage,
  refreshKey,
}: {
  bookId: string;
  accessToken: string;
  pages: BookPage[];
  onSelectPage: (page: number) => void;
  refreshKey: string;
}) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [pathItems, setPathItems] = useState<PathItem[]>([]);
  const [preferences, setPreferences] = useState<Preferences>(defaults);
  const [activeTopic, setActiveTopic] = useState<Topic | null>(null);
  const [lesson, setLesson] = useState<TopicLesson | null>(null);
  const [lessonLoading, setLessonLoading] = useState(false);
  const [needsGeneration, setNeedsGeneration] = useState(false);
  const [consent, setConsent] = useState(false);
  const [notes, setNotes] = useState<SavedNote[]>([]);
  const [highlights, setHighlights] = useState<SavedHighlight[]>([]);
  const [sourcePageNumber, setSourcePageNumber] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const sourcePage = pages.find((page) => page.page_number === sourcePageNumber) ?? null;

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setActiveTopic(null);
    setLesson(null);
    setNeedsGeneration(false);
    setConsent(false);
    const pathRequest = apiRequest<{ items: PathItem[] }>(
      "/api/books/" + bookId + "/path",
      accessToken,
    ).catch((reason: unknown) => {
      if (reason instanceof Error && reason.message === "Learning path not found.") return { items: [] };
      throw reason;
    });
    const preferencesRequest = apiRequest<Preferences>(
      "/api/books/" + bookId + "/preferences",
      accessToken,
    ).catch((reason: unknown) => {
      if (reason instanceof Error && reason.message === "Learning preferences not found.") return defaults;
      throw reason;
    });
    void Promise.all([
      apiRequest<{ topics: Topic[] }>("/api/books/" + bookId + "/map", accessToken),
      preferencesRequest,
      pathRequest,
      apiRequest<SavedNote[]>("/api/books/" + bookId + "/notes", accessToken),
      apiRequest<SavedHighlight[]>("/api/books/" + bookId + "/highlights", accessToken),
    ]).then(([map, savedPreferences, savedPath, savedNotes, savedHighlights]) => {
      if (!active) return;
      setTopics(map.topics);
      setPreferences(savedPreferences);
      setPathItems(savedPath.items);
      setNotes(savedNotes);
      setHighlights(savedHighlights);
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "Could not load learning data.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [accessToken, bookId, refreshKey]);

  const activeStatus = useMemo(
    () => activeTopic?.progress?.status ?? "new",
    [activeTopic],
  );

  async function openLesson(topic: Topic) {
    setActiveTopic(topic);
    setLesson(null);
    setNeedsGeneration(false);
    setConsent(false);
    setLessonLoading(true);
    setSourcePageNumber(topic.page_refs[0] ?? null);
    setError("");
    setNotice("");
    try {
      const saved = await apiRequest<TopicLesson>("/api/topics/" + topic.id + "/lesson", accessToken);
      setLesson(saved);
    } catch (reason) {
      if (reason instanceof Error && reason.message === "Lesson not found.") setNeedsGeneration(true);
      else setError(reason instanceof Error ? reason.message : "Could not open this lesson.");
    } finally {
      setLessonLoading(false);
    }
  }

  async function generateLesson() {
    if (!activeTopic || !consent) return;
    setWorking(true);
    setError("");
    try {
      const result = await apiRequest<TopicLesson>("/api/topics/" + activeTopic.id + "/lesson", accessToken, {
        method: "POST",
        body: JSON.stringify({ consent }),
      });
      setLesson(result);
      setNeedsGeneration(false);
      setNotice("Lesson saved to your library.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not generate this lesson.");
    } finally {
      setWorking(false);
    }
  }

  async function buildPath(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setWorking(true);
    setError("");
    setNotice("");
    try {
      await apiRequest("/api/books/" + bookId + "/preferences", accessToken, {
        method: "PUT",
        body: JSON.stringify(preferences),
      });
      const result = await apiRequest<{ items: PathItem[] }>(
        "/api/books/" + bookId + "/path",
        accessToken,
        { method: "POST" },
      );
      setPathItems(result.items);
      setNotice("Your learning path is ready.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save preferences or build your path.");
    } finally {
      setWorking(false);
    }
  }

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError("");
    setNotice("");
    try {
      await apiRequest("/api/books/" + bookId + "/preferences", accessToken, {
        method: "PUT",
        body: JSON.stringify(preferences),
      });
      setNotice("Learning preferences saved.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save preferences.");
    } finally {
      setWorking(false);
    }
  }

  async function setTopicStatus(status: TopicStatus) {
    if (!activeTopic) return;
    setWorking(true);
    setError("");
    try {
      await apiRequest("/api/topics/" + activeTopic.id + "/status", accessToken, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      const update = (items: Topic[]): Topic[] => items.map((item) =>
        item.id === activeTopic.id
          ? { ...item, progress: { status } }
          : { ...item, children: update(item.children ?? []) },
      );
      setTopics(update(topics));
      setActiveTopic({ ...activeTopic, progress: { status } });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update topic status.");
    } finally {
      setWorking(false);
    }
  }

  async function saveNote(body: string) {
    if (!activeTopic) return;
    try {
      const created = await apiRequest<SavedNote>("/api/books/" + bookId + "/notes", accessToken, {
        method: "POST",
        body: JSON.stringify({ topic_id: activeTopic.id, body }),
      });
      setNotes((current) => [created, ...current]);
      setNotice("Note saved.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the note.");
      throw reason;
    }
  }

  async function savePassage(page: number, text: string) {
    if (!activeTopic) return;
    try {
      const created = await apiRequest<SavedHighlight>("/api/books/" + bookId + "/highlights", accessToken, {
        method: "POST",
        body: JSON.stringify({ topic_id: activeTopic.id, page, text }),
      });
      setHighlights((current) => [created, ...current]);
      setNotice("Passage from page " + page + " saved.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the passage.");
      throw reason;
    }
  }

  if (loading) return <section className="learning-panel" aria-live="polite">Loading your learning map…</section>;
  return (
    <section className="learning-panel" aria-labelledby="learning-title">
      <div className="learning-section-heading"><div><p className="eyebrow">LEARN A LITTLE, KEEP IT</p><h2 id="learning-title">Your learning loop</h2></div></div>
      {error && <InlineError message={error} />}
      {notice && <p className="learning-notice" role="status">{notice}</p>}
      {topics.length === 0 ? (
        <p className="learning-muted">Build a page-cited study guide above to create your book map.</p>
      ) : (
        <>
          <ProgressVisual topics={topics} />
          <section className="book-map-view" aria-labelledby="map-title"><h3 id="map-title">Book map</h3><TopicTree topics={topics} onOpen={(topic) => void openLesson(topic)} /></section>
          <section className="preferences-panel" aria-labelledby="preferences-title">
            <h3 id="preferences-title">Set your study rhythm</h3>
            <form onSubmit={(event) => void savePreferences(event)}>
              <label>Minutes per topic<input min={1} max={240} onChange={(event) => setPreferences((current) => ({ ...current, minutes_per_topic: Number(event.target.value) }))} type="number" value={preferences.minutes_per_topic} /></label>
              <label>Minutes per day<input min={1} max={1440} onChange={(event) => setPreferences((current) => ({ ...current, daily_minutes: Number(event.target.value) }))} type="number" value={preferences.daily_minutes} /></label>
              <label>Goal<select onChange={(event) => setPreferences((current) => ({ ...current, goal: event.target.value as LearningGoal }))} value={preferences.goal}><option value="understand">Understand</option><option value="apply">Apply</option><option value="review">Review</option></select></label>
              <button className="button button-outline" disabled={working} type="submit">Save preferences</button>
            </form>
            <button className="button button-dark" disabled={working} onClick={() => void buildPath()} type="button">{working ? "Building…" : "Build my path"}</button>
          </section>
          <PathView items={pathItems} topics={topics} onOpen={(topic) => void openLesson(topic)} />
          <section className="saved-passages" aria-labelledby="saved-passages-title">
            <h3 id="saved-passages-title">Saved passages</h3>
            {highlights.length === 0 ? <p className="learning-muted">Passages you save from lesson sources will show here.</p> : highlights.map((highlight) => <blockquote key={highlight.id}><p>{highlight.text}</p><cite>Page {highlight.page}</cite></blockquote>)}
          </section>
        </>
      )}
      {activeTopic && (
        <section className="lesson-modal" aria-labelledby="lesson-modal-title">
          <div className="lesson-modal-heading"><h2 id="lesson-modal-title">{activeTopic.title}</h2><button aria-label="Close lesson" onClick={() => { setActiveTopic(null); setConsent(false); }} type="button">Close</button></div>
          {lesson ? (
            <LessonReader lesson={lesson} topic={activeTopic} sourcePage={sourcePage}
              onSelectPage={(page) => { setSourcePageNumber(page); onSelectPage(page); }}
              onStatusChange={(status) => void setTopicStatus(status)}
              status={activeStatus}
              notes={notes.filter((note) => note.topic_id === activeTopic.id)}
              onSaveNote={saveNote} onSavePassage={savePassage} />
          ) : lessonLoading ? <p className="learning-muted" aria-live="polite">Loading lesson…</p> : needsGeneration ? (
            <div className="lesson-gate">
              <p>This lesson sends the topic’s cited pages and one neighboring page to Groq for generation. The learning service manages the provider connection.</p>
              <label className="lesson-consent"><input checked={consent} onChange={(event) => setConsent(event.target.checked)} type="checkbox" />I consent to sending these source pages to Groq to generate this lesson.</label>
              <button className="button button-dark" disabled={!consent || working} onClick={() => void generateLesson()} type="button">{working ? "Generating lesson…" : "Generate lesson"}</button>
            </div>
          ) : <p className="learning-muted">Choose this topic to load its lesson.</p>}
        </section>
      )}
    </section>
  );
}
