"use client";

import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  AudioLines,
  BookOpen,
  Check,
  ChevronRight,
  CircleHelp,
  FilePlus2,
  FileText,
  Library,
  LockKeyhole,
  LogOut,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ChangeEvent } from "react";
import { apiRequest, type Book, type BookPage, type BookSummary, type GenerationJob } from "@/lib/api";
import { getSupabaseClient } from "@/lib/supabase";
import { LearningLoop } from "@/components/learning/LearningLoop";

const maxUploadMb = 50;
const emptyPages: BookPage[] = [];

function formatBytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function PageCitations({ pages, onSelect }: { pages: number[]; onSelect: (page: number) => void }) {
  return (
    <div className="citations" aria-label="Source pages">
      {pages.map((page) => (
        <button className="citation" key={page} onClick={() => onSelect(page)} type="button">
          p. {page}
        </button>
      ))}
    </div>
  );
}

function GuidePanel({
  summary,
  onSelectPage,
}: {
  summary: BookSummary;
  onSelectPage: (page: number) => void;
}) {
  return (
    <section className="guide-panel" aria-labelledby="guide-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">YOUR BOOK, MADE USEFUL</p>
          <h2 id="guide-title">The short version</h2>
        </div>
        <span className="source-badge"><ShieldCheck size={14} /> Page-cited</span>
      </div>
      <p className="overview">{summary.overview}</p>

      <div className="guide-grid">
        <section className="guide-column">
          <div className="subhead-row"><Sparkles size={17} /><h3>Ideas worth keeping</h3></div>
          {summary.key_ideas.map((idea, index) => (
            <article className="idea-row" key={`${idea.title}-${index}`}>
              <span className="idea-index">{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h4>{idea.title}</h4>
                <p>{idea.explanation}</p>
                <PageCitations pages={idea.pages} onSelect={onSelectPage} />
              </div>
            </article>
          ))}
        </section>
        <section className="guide-column framework-column">
          <div className="subhead-row"><BookOpen size={17} /><h3>Frameworks</h3></div>
          {summary.frameworks.length ? summary.frameworks.map((idea, index) => (
            <article className="framework-card" key={`${idea.title}-${index}`}>
              <h4>{idea.title}</h4>
              <p>{idea.explanation}</p>
              <PageCitations pages={idea.pages} onSelect={onSelectPage} />
            </article>
          )) : <p className="quiet-copy">No distinct framework was identified.</p>}
        </section>
      </div>

      <section className="practice-section">
        <div className="subhead-row"><Check size={17} /><h3>Try it, don’t just highlight it</h3></div>
        <div className="practice-grid">
          {summary.practice.map((item, index) => (
            <article className="practice-card" key={`${item.question}-${index}`}>
              <span className="practice-label">FIELD NOTE {String(index + 1).padStart(2, "0")}</span>
              <h4>{item.question}</h4>
              <p>{item.suggested_action}</p>
              <PageCitations pages={item.pages} onSelect={onSelectPage} />
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

export default function Home() {
  const configError = !process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    ? "Supabase public URL and key are missing."
    : "";
  const [accessToken, setAccessToken] = useState("");
  const [email, setEmail] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [password, setPassword] = useState("");
  const [books, setBooks] = useState<Book[]>([]);
  const [selectedBookId, setSelectedBookId] = useState("");
  const [pageState, setPageState] = useState<{ bookId: string; pages: BookPage[] } | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [search, setSearch] = useState("");
  const [dataUseConsent, setDataUseConsent] = useState(false);
  const [generationJob, setGenerationJob] = useState<GenerationJob | null>(null);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedBook = books.find((book) => book.id === selectedBookId) ?? null;
  const pages = pageState?.bookId === selectedBookId ? pageState.pages : emptyPages;
  const currentPage = pages.find((page) => page.page_number === pageNumber) ?? null;
  const matchingPages = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    if (!query) return [];
    return pages.filter((page) => page.text.toLocaleLowerCase().includes(query));
  }, [pages, search]);

  useEffect(() => {
    let active = true;
    setBusy(true);
    const sessionTimeout = window.setTimeout(() => {
      if (!active) return;
      setBusy(false);
      setError("Sign-in initialization timed out. Check the Supabase URL and your network, then refresh.");
    }, 12000);
    try {
      const supabase = getSupabaseClient();
      void supabase.auth.getSession().then(({ data, error: sessionError }) => {
        if (!active) return;
        window.clearTimeout(sessionTimeout);
        if (sessionError) setError("Could not check your sign-in. Refresh the page or sign in again.");
        const token = data.session?.access_token ?? "";
        setAccessToken(token);
        setBusy(Boolean(token));
      }).catch(() => {
        if (!active) return;
        window.clearTimeout(sessionTimeout);
        setError("Could not reach the sign-in service. Check your connection and Supabase URL, then retry.");
        setBusy(false);
      });
      const { data } = supabase.auth.onAuthStateChange((event, session) => {
        if (active) {
          const token = session?.access_token ?? "";
          setAccessToken(token);
          setBusy(Boolean(token));
          if (!token || event === "SIGNED_IN") {
            setBooks([]);
            setSelectedBookId("");
            setPageState(null);
            setPageNumber(1);
          }
        }
      });
      return () => {
        active = false;
        window.clearTimeout(sessionTimeout);
        data.subscription.unsubscribe();
      };
    } catch {
      window.clearTimeout(sessionTimeout);
      setBusy(false);
      setError("Supabase is not configured. Set the public project URL and key, then restart the frontend.");
      return () => { active = false; };
    }
  }, []);

  useEffect(() => {
    if (!accessToken) {
      return;
    }
    let active = true;
    void apiRequest<Book[]>("/api/books", accessToken)
      .then((result) => {
        if (!active) return;
        setBooks(result);
        setSelectedBookId((current) => result.some((book) => book.id === current)
          ? current
          : result[0]?.id || "");
        setError("");
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load your library.");
      })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken || !selectedBookId) {
      return;
    }
    let active = true;
    void apiRequest<BookPage[]>(`/api/books/${selectedBookId}/pages`, accessToken)
      .then((result) => { if (active) setPageState({ bookId: selectedBookId, pages: result }); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load pages.");
      });
    return () => { active = false; };
  }, [accessToken, selectedBookId]);

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const supabase = getSupabaseClient();
      const result = authMode === "signup"
        ? await supabase.auth.signUp({ email, password })
        : await supabase.auth.signInWithPassword({ email, password });
      if (result.error) throw result.error;
      if (authMode === "signup" && !result.data.session) {
        setMessage("Check your email to confirm your account, then sign in.");
      }
      setPassword("");
    } catch (reason) {
      const rawMessage = reason instanceof Error ? reason.message : "Could not sign in.";
      const safeMessage = /invalid path specified in request url/i.test(rawMessage)
        ? "Supabase rejected the configured project URL. In your frontend hosting settings, set NEXT_PUBLIC_SUPABASE_URL to the Project URL from Supabase Project Settings > API, then rebuild the frontend."
        : rawMessage;
      setError(safeMessage);
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !accessToken) return;
    setError("");
    setMessage("");
    if (file.size > maxUploadMb * 1024 * 1024) {
      setError(`This PDF is over the ${maxUploadMb} MB upload limit.`);
      return;
    }
    setUploading(true);
    try {
      const form = new FormData();
      form.set("file", file);
      const saved = await apiRequest<Book>("/api/books", accessToken, { method: "POST", body: form });
      const result = await apiRequest<Book[]>("/api/books", accessToken);
      setBooks(result);
      setSelectedBookId(saved.id);
      setPageNumber(1);
      setMessage(saved.duplicate ? "Already in your library. Picking up where you left it." : "Saved to your private library.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not upload this PDF.");
    } finally {
      setUploading(false);
    }
  }

  async function handleSummary() {
    if (!selectedBook || !accessToken || !dataUseConsent) return;
    setError("");
    setGenerating(true);
    try {
      const queued = await apiRequest<GenerationJob>(
        `/api/books/${selectedBook.id}/map-jobs`,
        accessToken,
        {
          method: "POST",
          body: JSON.stringify({ consent: dataUseConsent }),
        },
      );
      setGenerationJob(queued);
      let current = queued;
      while (current.status === "queued" || current.status === "running") {
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        current = await apiRequest<GenerationJob>(`/api/map-jobs/${queued.id}`, accessToken);
        setGenerationJob(current);
      }
      if (current.status === "failed") {
        throw new Error(current.error_message || "The learning service could not complete this book map.");
      }
      const result = await apiRequest<Book[]>("/api/books", accessToken);
      setBooks(result);
      setMessage("Your cited guide is ready.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create this guide.");
    } finally {
      setDataUseConsent(false);
      setGenerating(false);
    }
  }

  async function handleDelete() {
    if (!selectedBook || !accessToken) return;
    if (!window.confirm(`Delete ${selectedBook.title || "this book"} and all saved data?`)) return;
    setBusy(true);
    try {
      await apiRequest<void>(`/api/books/${selectedBook.id}`, accessToken, { method: "DELETE" });
      const remaining = books.filter((book) => book.id !== selectedBook.id);
      setBooks(remaining);
      setSelectedBookId(remaining[0]?.id ?? "");
      setPageState(null);
      setPageNumber(1);
      setMessage("Book, extracted pages, and stored PDF deleted.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete this book.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteLibrary() {
    if (!books.length || !accessToken) return;
    if (!window.confirm(`Delete all ${books.length} books, PDFs, pages, and guides from your account? This cannot be undone.`)) return;
    setBusy(true);
    try {
      await apiRequest<void>("/api/books", accessToken, { method: "DELETE" });
      setBooks([]);
      setSelectedBookId("");
      setPageState(null);
      setPageNumber(1);
      setMessage("Your library and its stored files have been deleted.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete your library.");
    } finally {
      setBusy(false);
    }
  }

  async function openStoredPdf() {
    if (!selectedBook || !accessToken) return;
    try {
      const result = await apiRequest<{ url: string }>(`/api/books/${selectedBook.id}/pdf-url`, accessToken);
      window.open(result.url, "_blank", "noopener,noreferrer");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not open the stored PDF.");
    }
  }

  function downloadText() {
    const content = pages.map((page) => `=== Page ${page.page_number} ===\n${page.text}`).join("\n\n");
    const href = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = "learnbook-page-notes.txt";
    anchor.click();
    URL.revokeObjectURL(href);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#library" aria-label="LearnBook home">
          <span className="brand-mark"><BookOpen size={19} /></span>
          <span>learnbook<span className="brand-period">.</span></span>
        </a>
        <nav className="topnav" aria-label="Primary navigation">
          <a className="nav-active" href="#library">My library</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <div className="account-area">
          {accessToken ? (
            <>
              <span className="account-email">{email}</span>
              <button className="icon-button" aria-label="Sign out" onClick={() => void getSupabaseClient().auth.signOut()} type="button"><LogOut size={17} /></button>
            </>
          ) : <span className="privacy-pill"><LockKeyhole size={13} /> Private by default</span>}
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div className="sidebar-label"><Library size={15} /> YOUR SHELF <span>{books.length.toString().padStart(2, "0")}</span></div>
          <div className="book-list">
            {books.map((book, index) => (
              <button
                className={`book-link ${selectedBookId === book.id ? "book-link-active" : ""}`}
                key={book.id}
                onClick={() => { setSelectedBookId(book.id); setPageNumber(1); }}
                type="button"
              >
                <span className={`book-cover cover-${index % 4}`}><BookOpen size={18} /></span>
                <span className="book-link-copy"><strong>{book.title || "Untitled book"}</strong><small>{book.page_count} pages</small></span>
                {selectedBookId === book.id && <ChevronRight size={15} />}
              </button>
            ))}
            {!books.length && accessToken && <p className="sidebar-empty">Your shelf is ready for its first book.</p>}
          </div>
          <div className="sidebar-bottom">
            <a href="#how-it-works"><CircleHelp size={15} /> The learning loop</a>
            <Link href="/terms"><ShieldCheck size={15} /> Terms & copyright</Link>
            {accessToken && books.length > 0 && <button className="sidebar-delete" onClick={() => void handleDeleteLibrary()} type="button"><Trash2 size={15} /> Delete my library</button>}
          </div>
        </aside>

        <section className="main-content" id="library">
          <div className="page-topline">
            <p className="eyebrow">YOUR READING DESK <span>•</span> PRIVATE MODE</p>
            <span className="storage-note"><LockKeyhole size={13} /> PDFs stay in your private library</span>
          </div>
          <div className="hero-row">
            <div>
              <h1>Read less passively.<br /><span>Keep more of what matters.</span></h1>
              <p className="hero-copy">Bring a book you own. Leave with page-cited ideas, a few questions, and one thing to try.</p>
            </div>
            <div className="hero-stamp"><span>YOUR BOOK</span><strong>→</strong><span>YOUR NEXT MOVE</span></div>
          </div>

          {configError && <div className="notice notice-warning"><CircleHelp size={17} /><span>{configError} Copy <code>web/.env.example</code> to <code>web/.env.local</code> and set the public Supabase values.</span></div>}
          {message && <div className="notice notice-success"><Check size={17} /><span>{message}</span><button aria-label="Dismiss message" onClick={() => setMessage("")} type="button"><X size={15} /></button></div>}
          {error && <div className="notice notice-error" role="alert"><X size={17} /><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError("")} type="button"><X size={15} /></button></div>}

          {!accessToken ? (
            <section className="auth-layout">
              <div className="auth-intro">
                <span className="section-kicker">A BETTER WAY TO KEEP THE GOOD PARTS</span>
                <h2>Books in.<br /><span>Ideas in motion.</span></h2>
                <div className="feature-line"><span className="feature-dot dot-teal" />Page-cited guides, grounded in your copy</div>
                <div className="feature-line"><span className="feature-dot dot-pink" />Short reads, comparisons, and practice</div>
                <div className="feature-line"><span className="feature-dot dot-yellow" />Your files stay in a private account</div>
              </div>
              <form className="auth-card" onSubmit={(event) => void handleAuth(event)}>
                <p className="eyebrow">YOUR ACCOUNT</p>
                <h2>{authMode === "login" ? "Welcome back" : "Make your shelf"}</h2>
                <label>Email<input autoComplete="email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} /></label>
                <label>Password<input autoComplete={authMode === "login" ? "current-password" : "new-password"} minLength={8} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} /></label>
                <button className="button button-dark button-full" type="submit">{authMode === "login" ? "Sign in" : "Create account"}<ArrowRight size={17} /></button>
                <button className="text-button" onClick={() => setAuthMode(authMode === "login" ? "signup" : "login")} type="button">{authMode === "login" ? "New here? Create an account" : "Already have an account? Sign in"}</button>
                <p className="auth-legal">By continuing, you agree to use this for personal study of books you are entitled to access.</p>
              </form>
            </section>
          ) : (
            <>
              <section className="upload-strip">
                <div className="upload-copy"><span className="upload-icon"><FilePlus2 size={19} /></span><div><strong>Add a book to your shelf</strong><small>PDF only · up to {maxUploadMb} MB · saved privately for online access</small></div></div>
                <label className={`button button-teal upload-button ${uploading ? "is-busy" : ""}`}>
                  <Upload size={17} />{uploading ? "Saving…" : "Upload PDF"}
                  <input accept="application/pdf,.pdf" disabled={uploading} onChange={(event) => void handleUpload(event)} type="file" />
                </label>
              </section>

              {busy && <div className="loading-line"><span className="spinner" /> Loading your library…</div>}

              {!selectedBook ? (
                <section className="empty-state" id="how-it-works">
                  <div className="empty-art"><div className="art-book art-book-one" /><div className="art-book art-book-two" /><Sparkles className="art-spark" size={28} /></div>
                  <p className="eyebrow">START WITH A BOOK YOU OWN</p>
                  <h2>Make your next read<br />count for something.</h2>
                  <p>We keep your original PDF in private storage, extract pages for citations, and build a guide only when you ask.</p>
                  <button className="button button-outline" onClick={() => document.getElementById("learning-loop")?.scrollIntoView({ behavior: "smooth" })} type="button">See the learning loop <ArrowRight size={16} /></button>
                </section>
              ) : (
                <>
                  <section className="book-summary-card">
                    <div className="summary-cover"><BookOpen size={27} /><span>YOUR COPY</span></div>
                    <div className="book-info">
                      <p className="eyebrow">IN YOUR PRIVATE LIBRARY</p>
                      <h2>{selectedBook.title || "Untitled book"}</h2>
                      <p className="author-line">{selectedBook.author || "Author not listed"}</p>
                      <div className="book-stats"><span><FileText size={14} />{selectedBook.page_count} pages</span><span>{formatBytes(selectedBook.file_size_bytes)}</span><span>{pages.filter((page) => !page.is_empty).length} pages with text</span></div>
                      {selectedBook.needs_ocr && <p className="scan-note">This looks scanned. Text extraction may be incomplete until OCR is available.</p>}
                    </div>
                    <div className="book-actions">
                      <button className="small-action" onClick={() => void openStoredPdf()} type="button"><BookOpen size={15} /> Open PDF</button>
                      <button className="small-action" onClick={downloadText} type="button"><ArrowDownToLine size={15} /> Export text</button>
                      <button className="small-action small-action-danger" onClick={() => void handleDelete()} type="button"><Trash2 size={15} /> Delete all</button>
                    </div>
                  </section>

                  <section className="reader-layout">
                    <div className="reader-card">
                      <div className="section-heading reader-heading">
                        <div><p className="eyebrow">READ THE ORIGINAL TEXT</p><h2>Page by page</h2></div>
                        <span className="page-counter">{pageNumber} <span>/ {selectedBook.page_count}</span></span>
                      </div>
                      <div className="page-progress"><span style={{ width: `${Math.max(4, pageNumber / selectedBook.page_count * 100)}%` }} /></div>
                      <div className="page-controls">
                        <button aria-label="Previous page" className="round-control" disabled={pageNumber <= 1} onClick={() => setPageNumber((page) => Math.max(1, page - 1))} type="button"><ArrowLeft size={17} /></button>
                        <label className="page-number-control">PAGE<input aria-label="Page number" max={selectedBook.page_count} min={1} onChange={(event) => setPageNumber(Math.max(1, Math.min(selectedBook.page_count, Number(event.target.value) || 1)))} type="number" value={pageNumber} /></label>
                        <button aria-label="Next page" className="round-control" disabled={pageNumber >= selectedBook.page_count} onClick={() => setPageNumber((page) => Math.min(selectedBook.page_count, page + 1))} type="button"><ArrowRight size={17} /></button>
                        <span className="character-count">{currentPage?.char_count.toLocaleString() ?? 0} chars</span>
                      </div>
                      {currentPage?.is_empty && <p className="empty-page-badge">Little or no extractable text</p>}
                      <div className="page-text">{currentPage?.text || (pages.length ? "This page has no extractable text." : "Loading page text…")}</div>
                    </div>
                    <aside className="tools-card">
                      <p className="eyebrow">FIND A SOURCE</p>
                      <h3>Search inside</h3>
                      <div className="search-box"><Search size={16} /><input aria-label="Search book text" onChange={(event) => setSearch(event.target.value)} placeholder="Try a word or phrase" value={search} /></div>
                      {search && <div className="search-results">{matchingPages.length ? matchingPages.slice(0, 8).map((page) => <button key={page.page_number} onClick={() => setPageNumber(page.page_number)} type="button"><span>Page {page.page_number}</span><ChevronRight size={15} /></button>) : <p>No pages found.</p>}</div>}
                      <div className="tool-divider" />
                      <p className="eyebrow">STUDY FORMAT</p>
                      <div className="format-option format-active"><BookOpen size={16} /><span>Read<small>Available now</small></span><Check size={15} /></div>
                      <div className="format-option format-disabled"><AudioLines size={16} /><span>Listen<small>Audio is on the roadmap</small></span><span className="soon-tag">SOON</span></div>
                    </aside>
                  </section>

                  <section className="summary-section">
                    {selectedBook.summary_json ? (
                      <GuidePanel summary={selectedBook.summary_json} onSelectPage={setPageNumber} />
                    ) : (
                      <div className="summary-gate">
                        <div className="summary-gate-heading"><span className="spark-tile"><Sparkles size={20} /></span><div><p className="eyebrow">YOUR PAGE-CITED STUDY GUIDE</p><h2>Turn the book into usable ideas.</h2></div></div>
                        <p className="gate-copy">A concise overview, key ideas, frameworks, and practice prompts. Every insight points back to the pages it came from.</p>
                        <p>Text from this book will be sent to Groq to create a page-cited learning map. Generation uses the site learning service and shared daily capacity.</p>
                        <label className="consent-line"><input checked={dataUseConsent} onChange={(event) => setDataUseConsent(event.target.checked)} type="checkbox" /><span>I understand and consent to sending this book’s text to Groq to create the learning map.</span></label>
                        <button className="button button-dark" disabled={!dataUseConsent || generating} onClick={() => void handleSummary()} type="button"><Sparkles size={16} />{generating ? "Building your map…" : "Build my study guide"}<ArrowRight size={16} /></button>
                        {generationJob && generating && <div className="job-progress" aria-live="polite"><p>{generationJob.step.replaceAll("_", " ")} · {generationJob.progress_pct}%</p><div role="progressbar" aria-label="Learning map progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={generationJob.progress_pct}><span style={{ width: `${generationJob.progress_pct}%` }} /></div><small>This can take a few minutes. You can stay on this page while the map is built.</small></div>}
                        <p className="quota-note">Daily per-user and shared service capacity limits apply.</p>
                      </div>
                    )}
                  </section>
                  <LearningLoop
                    bookId={selectedBook.id}
                    accessToken={accessToken}
                    pages={pages}
                    onSelectPage={setPageNumber}
                    refreshKey={selectedBook.summary_json?.overview ?? ""}
                  />
                </>
              )}

              <section className="learning-loop" id="learning-loop">
                <div className="loop-heading"><div><p className="eyebrow">THE LEARNING LOOP</p><h2>From pages to practice.</h2></div><span className="loop-legend"><i /> Available <i className="legend-future" /> In progress</span></div>
                <div className="loop-track">
                  <div className="loop-step loop-live"><span>01</span><strong>Upload</strong><small>Your PDF, private</small></div><div className="loop-line" />
                  <div className="loop-step loop-live"><span>02</span><strong>Extract</strong><small>Pages stay cited</small></div><div className="loop-line loop-line-future" />
                  <div className="loop-step"><span>03</span><strong>Map</strong><small>Ideas & frameworks</small></div><div className="loop-line loop-line-future" />
                  <div className="loop-step"><span>04</span><strong>Apply</strong><small>Questions & actions</small></div><div className="loop-line loop-line-future" />
                  <div className="loop-step"><span>05</span><strong>Remember</strong><small>Progress, not page views</small></div>
                </div>
              </section>
            </>
          )}
          <footer className="app-footer"><span>LEARNBOOK · BUILT FOR YOUR OWN BOOKS</span><a href="/terms">Privacy & copyright</a><span>Storage: private Supabase bucket</span></footer>
        </section>
      </div>
    </main>
  );
}
