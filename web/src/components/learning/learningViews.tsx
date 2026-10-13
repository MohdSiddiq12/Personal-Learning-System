"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import type { BookPage } from "@/lib/api";

export type TopicStatus = "new" | "learning" | "understood" | "review";
export type LearningGoal = "understand" | "apply" | "review";
export type Topic = {
  id: string;
  parent_id: string | null;
  kind: "topic" | "subtopic" | "framework" | "principle" | "method";
  title: string;
  summary: string;
  importance: number;
  est_minutes: number;
  position: number;
  page_refs: number[];
  key_terms?: string[];
  support?: "ok" | "weak";
  progress: { status: TopicStatus };
  children: Topic[];
};
export type PathItem = {
  id?: string;
  topic_id: string;
  position: number;
  day_number: number;
  is_optional: boolean;
  minutes_allocated?: number;
  is_condensed?: boolean;
  completed_at?: string | null;
};
export type TopicLesson = {
  body: string;
  recall_questions: { question: string; answer: string }[];
  action: string;
  target_minutes?: 5 | 10;
};
export type SavedNote = { id: string; topic_id: string | null; body: string; updated_at: string };

export function flattenTopics(topics: Topic[]): Topic[] {
  return topics.flatMap((topic) => [topic, ...flattenTopics(topic.children ?? [])]);
}

export function getProgressStats(topics: Topic[]) {
  const core = flattenTopics(topics).filter((topic) => topic.importance >= 4);
  return {
    understood: core.filter((topic) => topic.progress?.status === "understood").length,
    total: core.length,
  };
}

export function ProgressVisual({ topics, pathPercent = 0 }: { topics: Topic[]; pathPercent?: number }) {
  const { understood, total } = getProgressStats(topics);
  const corePercent = total ? Math.round((understood / total) * 100) : 0;
  return (
    <section className="learning-progress" aria-labelledby="progress-title">
      <div className="learning-section-heading"><div><p className="eyebrow">SELF-REPORTED</p><h3 id="progress-title">Your progress</h3></div></div>
      <label className="progress-label">Path completed: {pathPercent}%</label>
      <div className="progress-track" role="progressbar" aria-label="Path completed, self-reported" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pathPercent}><span style={{ width: pathPercent + "%" }} /></div>
      <label className="progress-label">Key ideas understood: {understood} of {total} ({corePercent}%)</label>
      <div className="progress-track" role="progressbar" aria-label="Key ideas understood, self-reported" aria-valuemin={0} aria-valuemax={100} aria-valuenow={corePercent}><span style={{ width: corePercent + "%" }} /></div>
      {total === 0 && <p className="learning-muted">No core ideas have been identified yet.</p>}
      <div className="progress-topic-grid">
        {flattenTopics(topics).map((topic) => {
          const status = topic.progress?.status ?? "new";
          return <div className={"progress-topic status-" + status} key={topic.id}><span aria-hidden="true" className="status-mark">{status === "understood" ? "✓" : status === "review" ? "↻" : status === "learning" ? "…" : "○"}</span><span>{topic.title}</span><small>{status}</small></div>;
        })}
      </div>
      <p className="learning-muted">Status uses both labels and color. Progress is self-reported, not graded.</p>
    </section>
  );
}

export function TopicTree({ topics, onOpen }: { topics: Topic[]; onOpen: (topic: Topic) => void }) {
  return <ul className="topic-tree">{topics.map((topic) => {
    const status = topic.progress?.status ?? "new";
    return <li key={topic.id}><button className={"topic-map-card status-" + status} onClick={() => onOpen(topic)} type="button"><span className="topic-map-title">{topic.title}</span><span className="topic-map-meta">{topic.kind} · importance {topic.importance}/5 · {topic.est_minutes} min</span><span className="topic-status-label">Status: {status}</span></button>{topic.children?.length > 0 && <TopicTree topics={topic.children} onOpen={onOpen} />}</li>;
  })}</ul>;
}

export function PathView({ items, topics, onOpen, onStart }: { items: PathItem[]; topics: Topic[]; onOpen: (topic: Topic) => void; onStart?: (topic: Topic) => void }) {
  const byId = new Map(flattenTopics(topics).map((topic) => [topic.id, topic]));
  const required = items.filter((item) => !item.is_optional).sort((a, b) => a.position - b.position);
  const optional = items.filter((item) => item.is_optional).sort((a, b) => a.position - b.position);
  const days = [...new Set(required.map((item) => item.day_number))];
  const current = required.find((item) => !item.completed_at);
  const currentTopic = current ? byId.get(current.topic_id) : undefined;
  return <section className="path-view" aria-labelledby="path-title"><h3 id="path-title">Your learning path</h3>
    {currentTopic && onStart && <button className="button button-dark" onClick={() => onStart(currentTopic)} type="button">Start today’s session</button>}
    {!items.length && <p className="learning-muted">Choose a daily time and build your path.</p>}
    {days.map((day) => {
      const dayItems = required.filter((item) => item.day_number === day);
      const minutes = dayItems.reduce((sum, item) => sum + (item.minutes_allocated ?? 0), 0);
      return <section className="path-day" key={day} aria-label={"Day " + day}><h4>Day {day}, {minutes} min</h4><ol>{dayItems.map((item) => {
        const topic = byId.get(item.topic_id);
        if (!topic) return null;
        return <li key={item.topic_id}><button type="button" onClick={() => onOpen(topic)}>{item.completed_at ? "Done · " : ""}{topic.title}<small>{topic.kind} · {item.minutes_allocated ?? topic.est_minutes} min</small>{item.is_condensed && <span className="item-badge">Short version</span>}{topic.support === "weak" && <span className="item-badge">Check the source</span>}{item.completed_at && <span className="item-badge">Completed</span>}</button></li>;
      })}</ol></section>;
    })}
    {optional.length > 0 && <details className="path-optional"><summary>Bonus topics ({optional.length})</summary><p>These lower-priority topics are optional additions.</p><ul>{optional.map((item) => {
      const topic = byId.get(item.topic_id);
      return topic ? <li key={item.topic_id}><button type="button" onClick={() => onOpen(topic)}>{topic.title}<small>{topic.kind} · {item.minutes_allocated ?? topic.est_minutes} min · optional</small></button></li> : null;
    })}</ul></details>}
  </section>;
}

export function LessonReader({ lesson, topic, sourcePages, onStatusChange, status, notes, onSaveNote, onSavePassage, onComplete }: {
  lesson: TopicLesson;
  topic: Topic;
  sourcePages: BookPage[];
  onStatusChange: (status: TopicStatus) => void;
  status: TopicStatus;
  notes: SavedNote[];
  onSaveNote: (body: string) => Promise<void>;
  onSavePassage: (page: number, text: string) => Promise<void>;
  onComplete: (result: "understood" | "review") => Promise<void>;
}) {
  const [revealed, setRevealed] = useState<number[]>([]);
  const [note, setNote] = useState("");
  const [passagePage, setPassagePage] = useState(sourcePages[0]?.page_number ?? 0);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const selectedPage = sourcePages.find((page) => page.page_number === passagePage);
  async function submitNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!note.trim()) return;
    setSaving(true); setSaveError("");
    try { await onSaveNote(note.trim()); setNote(""); }
    catch (reason) { setSaveError(reason instanceof Error ? reason.message : "Could not save this note."); }
    finally { setSaving(false); }
  }
  async function savePassage() {
    if (!selectedPage) return;
    setSaving(true); setSaveError("");
    try { await onSavePassage(selectedPage.page_number, selectedPage.text.slice(0, 4000)); }
    catch (reason) { setSaveError(reason instanceof Error ? reason.message : "Could not save this passage."); }
    finally { setSaving(false); }
  }
  return <article className="lesson-reader" aria-labelledby="lesson-title"><div className="learning-section-heading"><div><p className="eyebrow">SHORT LESSON · {lesson.target_minutes ?? topic.est_minutes} MIN</p><h3 id="lesson-title">{topic.title}</h3></div><span className="topic-status-label">Status: {status}</span></div>
    <div className="lesson-body">{lesson.body}</div>
    <details className="source-panel"><summary>Check the source ({sourcePages.length} cited pages)</summary>{sourcePages.map((page) => <section key={page.page_number} aria-label={"Cited source page " + page.page_number}><h4>Page {page.page_number}</h4><pre>{page.text}</pre></section>)}
      <label htmlFor="passage-page">Save passage from a cited page</label><select id="passage-page" value={passagePage} onChange={(event) => setPassagePage(Number(event.target.value))}>{sourcePages.map((page) => <option key={page.page_number} value={page.page_number}>Page {page.page_number}</option>)}</select><button className="button button-outline" disabled={saving || !selectedPage?.text.trim()} onClick={() => void savePassage()} type="button">Save passage</button>
    </details>
    {saveError && <p className="learning-error" role="alert">{saveError}</p>}
    <section className="recall-section"><h4>Check what you remember</h4><p>This is a self-check. Your answers are not graded.</p>{lesson.recall_questions.map((item, index) => <div className="recall-card" key={item.question + index}><strong>{item.question}</strong>{revealed.includes(index) ? <p>{item.answer}</p> : <button type="button" onClick={() => setRevealed((current) => [...current, index])}>Reveal answer</button>}</div>)}</section>
    <section className="action-card"><strong>One thing to try</strong><p>{lesson.action}</p></section>
    <fieldset className="status-controls"><legend>Topic status</legend>{(["new", "learning", "understood", "review"] as const).map((value) => <button aria-pressed={status === value} className={"status-choice status-" + value} key={value} onClick={() => onStatusChange(value)} type="button">{value}</button>)}</fieldset>
    <section className="lesson-notes"><h4>Notes</h4><form onSubmit={(event) => void submitNote(event)}><label htmlFor="topic-note">Add a note for this topic</label><textarea id="topic-note" maxLength={10000} onChange={(event) => setNote(event.target.value)} value={note} /><button className="button button-dark" disabled={!note.trim() || saving} type="submit">{saving ? "Saving…" : "Save note"}</button></form>{notes.map((item) => <p className="saved-note" key={item.id}>{item.body}</p>)}</section>
    <div className="lesson-completion"><button className="button button-teal" disabled={saving} onClick={() => void onComplete("understood")} type="button">Got it</button><button className="button button-outline" disabled={saving} onClick={() => void onComplete("review")} type="button">Need review</button></div>
  </article>;
}
