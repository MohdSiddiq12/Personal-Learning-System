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
  progress: { status: TopicStatus };
  children: Topic[];
};
export type PathItem = {
  topic_id: string;
  position: number;
  day_number: number;
  is_optional: boolean;
};
export type TopicLesson = {
  body: string;
  recall_questions: { question: string; answer: string }[];
  action: string;
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

export function ProgressVisual({ topics }: { topics: Topic[] }) {
  const { understood, total } = getProgressStats(topics);
  const percent = total ? Math.round((understood / total) * 100) : 0;
  return (
    <section className="learning-progress" aria-labelledby="progress-title">
      <div className="learning-section-heading">
        <div><p className="eyebrow">YOUR BOOK MAP</p><h3 id="progress-title">Core ideas understood: {understood} of {total}</h3></div>
        <span className="progress-percent">{percent}%</span>
      </div>
      <div className="progress-track" role="progressbar" aria-label="Core ideas understood" aria-valuemin={0} aria-valuemax={total || 1} aria-valuenow={understood}>
        <span style={{ width: percent + "%" }} />
      </div>
      {total === 0 && <p className="learning-muted">Core ideas will appear here after a book map is available.</p>}
      <div className="progress-topic-grid">
        {flattenTopics(topics).map((topic) => {
          const status = topic.progress?.status ?? "new";
          return (
            <div className={"progress-topic status-" + status} key={topic.id}>
              <span aria-hidden="true" className="status-mark">{status === "understood" ? "✓" : status === "review" ? "↻" : status === "learning" ? "…" : "○"}</span>
              <span>{topic.title}</span><small>{status}</small>
            </div>
          );
        })}
      </div>
      <p className="learning-muted">Each tile includes a status label as well as a color.</p>
    </section>
  );
}

export function TopicTree({ topics, onOpen }: { topics: Topic[]; onOpen: (topic: Topic) => void }) {
  return (
    <ul className="topic-tree">
      {topics.map((topic) => {
        const status = topic.progress?.status ?? "new";
        return (
          <li key={topic.id}>
            <button className={"topic-map-card status-" + status} onClick={() => onOpen(topic)} type="button">
              <span className="topic-map-title">{topic.title}</span>
              <span className="topic-map-meta">{topic.kind} · importance {topic.importance}/5 · {topic.est_minutes} min</span>
              <span className="topic-status-label">{status}</span>
            </button>
            {topic.children?.length > 0 && <TopicTree topics={topic.children} onOpen={onOpen} />}
          </li>
        );
      })}
    </ul>
  );
}

export function PathView({ items, topics, onOpen }: {
  items: PathItem[];
  topics: Topic[];
  onOpen: (topic: Topic) => void;
}) {
  const byId = new Map(flattenTopics(topics).map((topic) => [topic.id, topic]));
  const required = items.filter((item) => !item.is_optional).sort((a, b) => a.position - b.position);
  const optional = items.filter((item) => item.is_optional).sort((a, b) => a.position - b.position);
  const days = [...new Set(required.map((item) => item.day_number))];
  return (
    <section className="path-view" aria-labelledby="path-title">
      <h3 id="path-title">Your learning path</h3>
      {required.length === 0 && optional.length === 0 && <p className="learning-muted">Build a path after saving your preferences.</p>}
      {days.map((day) => (
        <section className="path-day" key={day} aria-label={"Day " + day}>
          <h4>Day {day}</h4>
          <ol>{required.filter((item) => item.day_number === day).map((item) => {
            const topic = byId.get(item.topic_id);
            return topic ? <li key={item.topic_id}><button type="button" onClick={() => onOpen(topic)}>{topic.title}<small>{topic.est_minutes} min · importance {topic.importance}/5</small></button></li> : null;
          })}</ol>
        </section>
      ))}
      {optional.length > 0 && (
        <section className="path-optional" aria-labelledby="optional-title">
          <h4 id="optional-title">Optional topics</h4>
          <p>These topics do not fit the time limits you chose.</p>
          <ul>{optional.map((item) => {
            const topic = byId.get(item.topic_id);
            return topic ? <li key={item.topic_id}><button type="button" onClick={() => onOpen(topic)}>{topic.title}<small>{topic.est_minutes} min · optional</small></button></li> : null;
          })}</ul>
        </section>
      )}
    </section>
  );
}

export function LessonReader({ lesson, topic, sourcePage, onSelectPage, onStatusChange, status, notes, onSaveNote, onSavePassage }: {
  lesson: TopicLesson;
  topic: Topic;
  sourcePage: BookPage | null;
  onSelectPage: (page: number) => void;
  onStatusChange: (status: TopicStatus) => void;
  status: TopicStatus;
  notes: SavedNote[];
  onSaveNote: (body: string) => Promise<void>;
  onSavePassage: (page: number, text: string) => Promise<void>;
}) {
  const [revealed, setRevealed] = useState<number[]>([]);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  async function submitNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!note.trim()) return;
    setSaving(true);
    setSaveError("");
    try {
      await onSaveNote(note.trim());
      setNote("");
    } catch (reason) {
      setSaveError(reason instanceof Error ? reason.message : "Could not save this note.");
    } finally {
      setSaving(false);
    }
  }
  async function savePassage() {
    if (!sourcePage) return;
    setSaving(true);
    setSaveError("");
    try {
      await onSavePassage(sourcePage.page_number, sourcePage.text.slice(0, 4000));
    } catch (reason) {
      setSaveError(reason instanceof Error ? reason.message : "Could not save this passage.");
    } finally {
      setSaving(false);
    }
  }
  return (
    <article className="lesson-reader" aria-labelledby="lesson-title">
      <div className="learning-section-heading"><div><p className="eyebrow">SHORT LESSON · {topic.est_minutes} MIN</p><h3 id="lesson-title">{topic.title}</h3></div><span className="topic-status-label">{status}</span></div>
      <div className="lesson-body">{lesson.body}</div>
      <div className="lesson-citations"><strong>Source pages</strong>{topic.page_refs.map((page) => <button key={page} type="button" onClick={() => onSelectPage(page)}>View page {page}</button>)}</div>
      {saveError && <p className="learning-error" role="alert">{saveError}</p>}
      {sourcePage && <section className="source-panel" aria-label={"Source page " + sourcePage.page_number}><h4>Source page {sourcePage.page_number}</h4><pre>{sourcePage.text}</pre><button className="button button-outline" disabled={saving || !sourcePage.text.trim()} onClick={() => void savePassage()} type="button">Save passage from page {sourcePage.page_number}</button>{!sourcePage.text.trim() && <p className="learning-muted">This page has no extractable text to save.</p>}</section>}
      <section className="recall-section" aria-labelledby="recall-title">
        <h4 id="recall-title">Check what you remember</h4><p>This is a self-check. Your answers are not graded.</p>
        {lesson.recall_questions.map((item, index) => <div className="recall-card" key={item.question + index}><strong>{item.question}</strong>{revealed.includes(index) ? <p>{item.answer}</p> : <button type="button" onClick={() => setRevealed((current) => [...current, index])}>Reveal answer</button>}</div>)}
      </section>
      <section className="action-card"><strong>One thing to try</strong><p>{lesson.action}</p></section>
      <fieldset className="status-controls"><legend>Topic status</legend>{(["new", "learning", "understood", "review"] as const).map((value) => <button aria-pressed={status === value} className={"status-choice status-" + value} key={value} onClick={() => onStatusChange(value)} type="button">{value}</button>)}</fieldset>
      <section className="lesson-notes">
        <h4>Notes</h4><form onSubmit={(event) => void submitNote(event)}><label htmlFor="topic-note">Add a note for this topic</label><textarea id="topic-note" maxLength={10000} onChange={(event) => setNote(event.target.value)} value={note} /><button className="button button-dark" disabled={!note.trim() || saving} type="submit">{saving ? "Saving…" : "Save note"}</button></form>
        {notes.map((item) => <p className="saved-note" key={item.id}>{item.body}</p>)}
      </section>
    </article>
  );
}
