"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { apiRequest, type BookPage, type GenerationJob } from "@/lib/api";
import {
  flattenTopics,
  LessonReader,
  PathView,
  ProgressVisual,
  TopicTree,
} from "./learningViews";
import type { LearningGoal, PathItem, SavedNote, Topic, TopicLesson, TopicStatus } from "./learningViews";
import type { BookSummary } from "@/lib/api";

type Preferences = { minutes_per_topic: number; daily_minutes: number; goal: LearningGoal };
type SavedHighlight = { id: string; topic_id: string | null; page: number; text: string; note: string };
type Progress = { path_percent: number; core_percent: number; topics_total: number; topics_understood: number };
const defaults: Preferences = { minutes_per_topic: 10, daily_minutes: 30, goal: "understand" };
const presets = [5, 10, 30, 60];

function InlineError({ message }: { message: string }) { return <p className="learning-error" role="alert">{message}</p>; }

export function validateCustomMinutes(value: string): string {
  if (!value.trim()) return "Enter a daily time in minutes.";
  if (!/^\d+$/.test(value.trim())) return "Enter a whole number of minutes.";
  const minutes = Number(value);
  if (minutes < 5) return "Choose at least 5 minutes per day.";
  if (minutes > 180) return "Choose no more than 180 minutes per day.";
  return "";
}

export function LearningLoop({ bookId, accessToken, pages, refreshKey }: {
  bookId: string; accessToken: string; pages: BookPage[]; refreshKey: string;
}) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [pathItems, setPathItems] = useState<PathItem[]>([]);
  const [preferences, setPreferences] = useState<Preferences>(defaults);
  const [customMinutes, setCustomMinutes] = useState("");
  const [customSelected, setCustomSelected] = useState(false);
  const [mode, setMode] = useState<"path" | "overview" | null>(null);
  const [activeTopic, setActiveTopic] = useState<Topic | null>(null);
  const [activeTargetMinutes, setActiveTargetMinutes] = useState<5 | 10>(10);
  const [lesson, setLesson] = useState<TopicLesson | null>(null);
  const [prefetchedLessons, setPrefetchedLessons] = useState<Record<string, TopicLesson>>({});
  const [sessionResult, setSessionResult] = useState<{ nextTopic: Topic | null } | null>(null);
  const [lessonJob, setLessonJob] = useState<GenerationJob | null>(null);
  const [job, setJob] = useState<GenerationJob | null>(null);
  const [lessonLoading, setLessonLoading] = useState(false);
  const [needsGeneration, setNeedsGeneration] = useState(false);
  const [consent, setConsent] = useState(false);
  const [notes, setNotes] = useState<SavedNote[]>([]);
  const [highlights, setHighlights] = useState<SavedHighlight[]>([]);
  const [progress, setProgress] = useState<Progress>({ path_percent: 0, core_percent: 0, topics_total: 0, topics_understood: 0 });
  const [summary, setSummary] = useState<BookSummary | null>(null);
  const [activeTab, setActiveTab] = useState<"path" | "learned" | "progress">("path");
  const [learned, setLearned] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showPreferences, setShowPreferences] = useState(false);
  const activeStatus = useMemo(() => activeTopic?.progress?.status ?? "new", [activeTopic]);
  const sourcePages = activeTopic ? pages.filter((page) => activeTopic.page_refs.includes(page.page_number)) : [];
  const customError = customSelected ? validateCustomMinutes(customMinutes) : "";
  const selectedMinutes = customSelected ? Number(customMinutes) : preferences.daily_minutes;
  const canBuild = Boolean(mode && consent && selectedMinutes >= 5 && selectedMinutes <= 180 && !customError);

  async function loadLearningData() {
    const [map, pref, path, savedNotes, savedHighlights, currentProgress] = await Promise.all([
      apiRequest<{ topics: Topic[]; summary?: BookSummary | null }>(`/api/books/${bookId}/map`, accessToken),
      apiRequest<Preferences>(`/api/books/${bookId}/preferences`, accessToken).catch(() => defaults),
      apiRequest<{ items: PathItem[] }>(`/api/books/${bookId}/path`, accessToken).catch(() => ({ items: [] })),
      apiRequest<SavedNote[]>(`/api/books/${bookId}/notes`, accessToken).catch(() => []),
      apiRequest<SavedHighlight[]>(`/api/books/${bookId}/highlights`, accessToken).catch(() => []),
      apiRequest<Progress>(`/api/books/${bookId}/progress`, accessToken).catch(() => ({ path_percent: 0, core_percent: 0, topics_total: 0, topics_understood: 0 })),
    ]);
    setTopics(map.topics); setPreferences(pref); setPathItems(path.items); setNotes(savedNotes); setHighlights(savedHighlights); setProgress(currentProgress);
    setSummary(map.summary ?? null);
    return map.topics;
  }

  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setActiveTopic(null); setLesson(null); setLessonJob(null);
    void Promise.all([
      loadLearningData(),
      apiRequest<GenerationJob | null>(`/api/books/${bookId}/active-job`, accessToken).catch(() => null),
    ]).then(([loadedTopics, activeJob]) => {
      if (!active) return;
      if (!loadedTopics.length) setMode("path");
      if (activeJob) setJob(activeJob);
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load your learning plan."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [accessToken, bookId, refreshKey]);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    let active = true;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const next = await apiRequest<GenerationJob>(`/api/map-jobs/${job.id}`, accessToken);
        if (!active) return;
        setJob(next);
        if (next.status === "done") {
          await loadLearningData();
          if (mode === "path") {
            await apiRequest(`/api/books/${bookId}/path`, accessToken, { method: "POST" });
            await loadLearningData();
            setActiveTab("path");
          }
          setMode(mode === "overview" ? "overview" : null);
          setNotice("Your learning map is ready.");
        }
        else if (next.status === "failed") setError(next.error_message || "The learning map could not be completed.");
        else timer = window.setTimeout(poll, 2500);
      } catch (reason) {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "Could not check generation progress.");
        timer = window.setTimeout(poll, 4000);
      }
    };
    timer = window.setTimeout(poll, 2200);
    return () => { active = false; if (timer) window.clearTimeout(timer); };
  }, [job?.id, job?.status, accessToken, mode, bookId]);

  useEffect(() => {
    if (!lessonJob || !activeTopic || !["queued", "running"].includes(lessonJob.status)) return;
    let active = true;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const next = await apiRequest<GenerationJob>(`/api/topics/${activeTopic.id}/lesson-jobs/${lessonJob.id}`, accessToken);
        if (!active) return;
        setLessonJob(next);
        if (next.status === "done") {
          const cached = await apiRequest<TopicLesson>(`/api/topics/${activeTopic.id}/lesson?target_minutes=${activeTargetMinutes}`, accessToken);
          if (active) { setLesson(cached); setNeedsGeneration(false); }
        } else if (next.status === "failed") setError(next.error_message || "The lesson could not be completed.");
        else timer = window.setTimeout(poll, 2500);
      } catch (reason) {
        if (active) { setError(reason instanceof Error ? reason.message : "Could not check lesson progress."); timer = window.setTimeout(poll, 4000); }
      }
    };
    timer = window.setTimeout(poll, 2200);
    return () => { active = false; if (timer) window.clearTimeout(timer); };
  }, [lessonJob, activeTopic, activeTargetMinutes, accessToken]);

  async function startMap() {
    if (!canBuild) return;
    setWorking(true); setError("");
    try {
      if (mode === "path") {
        const nextPreferences = { ...preferences, daily_minutes: selectedMinutes };
        await apiRequest(`/api/books/${bookId}/preferences`, accessToken, { method: "PUT", body: JSON.stringify(nextPreferences) });
        setPreferences(nextPreferences);
      }
      const queued = await apiRequest<GenerationJob>(`/api/books/${bookId}/map-jobs`, accessToken, { method: "POST", body: JSON.stringify({ consent }) });
      setJob(queued); setConsent(false);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not start map generation."); }
    finally { setWorking(false); }
  }

  async function retryMap() {
    if (!job) return;
    setError("");
    try { setJob(await apiRequest<GenerationJob>(`/api/map-jobs/${job.id}/retry`, accessToken, { method: "POST" })); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not retry map generation."); }
  }

  async function openLesson(topic: Topic) {
    const pathItem = pathItems.find((item) => item.topic_id === topic.id);
    const target = (pathItem?.minutes_allocated ?? topic.est_minutes) <= 5 ? 5 : 10;
    setActiveTargetMinutes(target);
    setActiveTopic(topic); setSessionResult(null); setLesson(null); setNeedsGeneration(false); setConsent(false); setLessonJob(null); setError(""); setNotice("");
    const prefetched = prefetchedLessons[topic.id];
    if (prefetched) {
      setLesson(prefetched);
      setPrefetchedLessons((current) => {
        const remaining = { ...current };
        delete remaining[topic.id];
        return remaining;
      });
      setLessonLoading(false);
      return;
    }
    setLessonLoading(true);
    try { setLesson(await apiRequest<TopicLesson>(`/api/topics/${topic.id}/lesson?target_minutes=${target}`, accessToken)); }
    catch (reason) { if (reason instanceof Error && reason.message === "Lesson not found.") setNeedsGeneration(true); else setError(reason instanceof Error ? reason.message : "Could not load the lesson."); }
    finally { setLessonLoading(false); }
  }

  async function generateLesson() {
    if (!activeTopic || !consent) return;
    setWorking(true); setError("");
    try {
      const result = await apiRequest<GenerationJob>(`/api/topics/${activeTopic.id}/lesson-jobs`, accessToken, { method: "POST", body: JSON.stringify({ consent, target_minutes: activeTargetMinutes }) });
      if ("cached" in result) setLesson(result.cached as TopicLesson);
      else setLessonJob(result);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not start lesson generation."); }
    finally { setWorking(false); }
  }

  async function buildPath(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault(); setWorking(true); setError("");
    try {
      const nextPreferences = { ...preferences, daily_minutes: selectedMinutes };
      await apiRequest(`/api/books/${bookId}/preferences`, accessToken, { method: "PUT", body: JSON.stringify(nextPreferences) });
      setPreferences(nextPreferences);
      const result = await apiRequest<{ items: PathItem[] }>(`/api/books/${bookId}/path`, accessToken, { method: "POST" });
      const saved = await apiRequest<{ items: PathItem[] }>(`/api/books/${bookId}/path`, accessToken);
      setPathItems(saved.items ?? result.items); setShowPreferences(false); setNotice("Your daily learning path is ready.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not build your path."); }
    finally { setWorking(false); }
  }

  async function setTopicStatus(status: TopicStatus) {
    if (!activeTopic) return;
    try {
      await apiRequest(`/api/topics/${activeTopic.id}/status`, accessToken, { method: "PUT", body: JSON.stringify({ status }) });
      const update = (items: Topic[]): Topic[] => items.map((item) => item.id === activeTopic.id ? { ...item, progress: { status } } : { ...item, children: update(item.children ?? []) });
      const nextTopics = update(topics); setTopics(nextTopics); setActiveTopic({ ...activeTopic, progress: { status } });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update topic status."); }
  }

  async function completeTopic(result: "understood" | "review") {
    if (!activeTopic) return;
    const item = pathItems.find((candidate) => candidate.topic_id === activeTopic.id);
    if (!item?.id) { await setTopicStatus(result); setActiveTopic(null); return; }
    const nextItem = pathItems
      .filter((candidate) => !candidate.is_optional && !candidate.completed_at && candidate.day_number === item.day_number && candidate.position > item.position)
      .sort((left, right) => left.position - right.position)[0];
    const nextTopic = nextItem ? flattenTopics(topics).find((topic) => topic.id === nextItem.topic_id) ?? null : null;
    try {
      await apiRequest(`/api/path-items/${item.id}/complete`, accessToken, { method: "POST", body: JSON.stringify({ status: result }) });
      await loadLearningData();
      setLesson(null);
      setSessionResult({ nextTopic });
      setNotice(result === "understood" ? "Marked understood." : "Saved for review.");
      if (nextTopic && nextItem) {
        const target = (nextItem.minutes_allocated ?? nextTopic.est_minutes) <= 5 ? 5 : 10;
        try {
          const cached = await apiRequest<TopicLesson>(`/api/topics/${nextTopic.id}/lesson?target_minutes=${target}`, accessToken);
          setPrefetchedLessons((current) => ({ ...current, [nextTopic.id]: cached }));
        } catch {
          // Generate only after the learner opens the lesson and consents.
        }
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save this session."); }
  }

  async function saveNote(body: string) {
    if (!activeTopic) return;
    const created = await apiRequest<SavedNote>(`/api/books/${bookId}/notes`, accessToken, { method: "POST", body: JSON.stringify({ topic_id: activeTopic.id, body }) });
    setNotes((current) => [created, ...current]); setNotice("Note saved.");
  }
  async function savePassage(page: number, text: string) {
    if (!activeTopic) return;
    const created = await apiRequest<SavedHighlight>(`/api/books/${bookId}/highlights`, accessToken, { method: "POST", body: JSON.stringify({ topic_id: activeTopic.id, page, text }) });
    setHighlights((current) => [created, ...current]); setNotice("Passage from page " + page + " saved.");
  }

  useEffect(() => {
    if (activeTab === "learned") void apiRequest<Record<string, unknown>[]>(`/api/books/${bookId}/learned`, accessToken).then(setLearned).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load learned topics."));
  }, [activeTab, bookId, accessToken]);

  if (loading) return <section className="learning-panel" aria-live="polite">Loading your learning plan…</section>;
  if (!topics.length) return <section className="learning-panel" aria-labelledby="learning-title"><h2 id="learning-title">What would you like to do with this book?</h2>{error && <InlineError message={error} />}
    <div className="flow-choice-group" role="group" aria-label="Choose a learning mode"><button className={mode === "path" ? "choice-card is-selected" : "choice-card"} aria-pressed={mode === "path"} onClick={() => setMode("path")} type="button"><strong>Customize my learning path</strong><span>Choose your daily time and follow a guided plan.</span><small>Recommended</small></button><button className={mode === "overview" ? "choice-card is-selected" : "choice-card"} aria-pressed={mode === "overview"} onClick={() => setMode("overview")} type="button"><strong>Quick overview</strong><span>Build a concise map of the book’s ideas first.</span></button></div>
    {mode === "path" && <section className="daily-time-panel"><h3>How much time can you give per day?</h3><div className="time-options" role="radiogroup" aria-label="Daily learning time">{presets.map((minutes) => <label className={preferences.daily_minutes === minutes && !customSelected ? "time-option is-selected" : "time-option"} key={minutes}><input checked={preferences.daily_minutes === minutes && !customSelected} name="daily-minutes" onChange={() => { setCustomSelected(false); setPreferences((current) => ({ ...current, daily_minutes: minutes })); }} type="radio" value={minutes} /><span>{minutes < 60 ? `${minutes} minutes` : "1 hour"}</span></label>)}<label className={customSelected ? "time-option is-selected" : "time-option"}><input checked={customSelected} name="daily-minutes" onChange={() => setCustomSelected(true)} type="radio" value="custom" /><span>Custom</span></label></div>{customSelected && <label className="custom-time-field">Custom minutes<input inputMode="numeric" min={5} max={180} onChange={(event) => setCustomMinutes(event.target.value)} placeholder="For example 15" type="number" value={customMinutes} />{customError && <span className="field-error" role="alert">{customError}</span>}</label>}</section>}
    {mode && <><label className="lesson-consent"><input checked={consent} onChange={(event) => setConsent(event.target.checked)} type="checkbox" />Text from this book will be sent to Groq to create my learning map. I own this book or may use it for personal study. <a href="/terms#privacy">Privacy details</a></label><button className="button button-dark" disabled={!canBuild || working} onClick={() => void startMap()} type="button">{working ? "Starting…" : "Create my learning map"}</button></>}
    {job && <section className="job-progress" aria-live="polite"><p>{job.step.replaceAll("_", " ")} · {job.progress_pct}%</p><div role="progressbar" aria-label="Learning map progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={job.progress_pct}><span style={{ width: job.progress_pct + "%" }} /></div><small>This can take a few minutes.</small>{job.error_code === "rate_limited" && <p>Busy, waiting about 2 seconds before checking again.</p>}{job.error_code === "budget_exhausted" && <p>Daily capacity reached. Please try again tomorrow.</p>}{job.status === "failed" && job.error_code !== "budget_exhausted" && <button className="button button-outline" onClick={() => void retryMap()} type="button">Retry</button>}</section>}
  </section>;

  return <section className="learning-panel" aria-labelledby="learning-title"><div className="learning-section-heading"><div><p className="eyebrow">LEARN A LITTLE, KEEP IT</p><h2 id="learning-title">Your learning loop</h2></div></div>{error && <InlineError message={error} />}{notice && <p className="learning-notice" role="status">{notice}</p>}
    {job?.status === "queued" || job?.status === "running" ? <section className="job-progress" aria-live="polite"><p>{job.step.replaceAll("_", " ")} · {job.progress_pct}%</p><div role="progressbar" aria-label="Learning map progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={job.progress_pct}><span style={{ width: job.progress_pct + "%" }} /></div><small>This can take a few minutes.</small></section> : null}
    {mode === "overview" && summary && <section className="quick-overview"><h3>Quick overview</h3><p>{summary.overview}</p><button className="button button-dark" onClick={() => { setMode("path"); setShowPreferences(true); }} type="button">Turn this into a path</button></section>}
    <ProgressVisual topics={topics} pathPercent={progress.path_percent} />
    <div className="learning-tabs" role="tablist" aria-label="Book learning views">{(["path", "learned", "progress"] as const).map((tab) => <button role="tab" aria-selected={activeTab === tab} key={tab} onClick={() => setActiveTab(tab)} type="button">{tab === "path" ? "Path" : tab === "learned" ? "Learned" : "Progress"}</button>)}</div>
    {activeTab === "path" && <><section className="book-map-view"><h3>Book map</h3><TopicTree topics={topics} onOpen={(topic) => void openLesson(topic)} /></section><button className="button button-outline" onClick={() => setShowPreferences((value) => !value)} type="button">Change daily time</button>{showPreferences && <section className="daily-time-panel"><h3>Choose daily minutes</h3><div className="time-options" role="radiogroup" aria-label="Daily learning time">{presets.map((minutes) => <label className={preferences.daily_minutes === minutes && !customSelected ? "time-option is-selected" : "time-option"} key={minutes}><input checked={preferences.daily_minutes === minutes && !customSelected} name="change-minutes" onChange={() => { setCustomSelected(false); setPreferences((current) => ({ ...current, daily_minutes: minutes })); }} type="radio" value={minutes} /><span>{minutes < 60 ? `${minutes} minutes` : "1 hour"}</span></label>)}</div><button className="button button-dark" disabled={working} onClick={() => void buildPath()} type="button">{working ? "Saving…" : "Save and rebuild path"}</button></section>}<PathView items={pathItems} topics={topics} onOpen={(topic) => void openLesson(topic)} onStart={(topic) => void openLesson(topic)} /></>}
    {activeTab === "learned" && <section aria-label="Learned topics">{learned.length ? learned.map((item, index) => <article className="learned-card" key={index}><h3>{String((item.topic as Record<string, unknown>)?.title ?? "Completed topic")}</h3><p>Completed session</p></article>) : <p className="learning-muted">Completed lessons, notes, and saved passages will appear here.</p>}</section>}
    {activeTab === "progress" && <ProgressVisual topics={topics} pathPercent={progress.path_percent} />}
    <section className="saved-passages"><h3>Saved passages</h3>{highlights.length === 0 ? <p className="learning-muted">Passages saved from cited lesson pages appear here.</p> : highlights.map((item) => <blockquote key={item.id}><p>{item.text}</p><cite>Page {item.page}</cite></blockquote>)}</section>
    {activeTopic && <section className="lesson-modal" aria-labelledby="lesson-modal-title"><div className="lesson-modal-heading"><h2 id="lesson-modal-title">{activeTopic.title}</h2><button aria-label="Close lesson" onClick={() => { setActiveTopic(null); setSessionResult(null); setConsent(false); }} type="button">Close</button></div>{sessionResult ? <div className="session-result" role="status">{sessionResult.nextTopic ? <><p>This session is complete. Continue with the next topic today?</p><button className="button button-dark" onClick={() => void openLesson(sessionResult.nextTopic as Topic)} type="button">Next topic</button></> : <p>Today's session is done.</p>}<button className="button button-outline" onClick={() => { setSessionResult(null); setActiveTopic(null); }} type="button">Close session</button></div> : lesson ? <LessonReader key={activeTopic.id} lesson={lesson} topic={activeTopic} sourcePages={sourcePages} onStatusChange={(status) => void setTopicStatus(status)} status={activeStatus} notes={notes.filter((note) => note.topic_id === activeTopic.id)} onSaveNote={saveNote} onSavePassage={savePassage} onComplete={completeTopic} /> : lessonLoading ? <p className="learning-muted" aria-live="polite">Loading lesson…</p> : lessonJob ? <section className="job-progress" aria-live="polite"><p>Generating lesson · {lessonJob.progress_pct}%</p><div role="progressbar" aria-label="Lesson progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={lessonJob.progress_pct}><span style={{ width: lessonJob.progress_pct + "%" }} /></div></section> : needsGeneration ? <div className="lesson-gate"><p>This lesson uses the book’s cited pages and requires consent to send those pages to Groq.</p><label className="lesson-consent"><input checked={consent} onChange={(event) => setConsent(event.target.checked)} type="checkbox" />I consent to sending cited source text to Groq for this lesson.</label><button className="button button-dark" disabled={!consent || working} onClick={() => void generateLesson()} type="button">{working ? "Starting…" : "Generate lesson"}</button></div> : <p className="learning-muted">Choose a topic to open its lesson.</p>}</section>}
  </section>;
}
