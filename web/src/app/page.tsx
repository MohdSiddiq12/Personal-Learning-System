"use client";

import {
  ArrowRight,
  BookOpen,
  Check,
  CircleHelp,
  FilePlus2,
  FileText,
  Library,
  LockKeyhole,
  LogOut,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent, ChangeEvent } from "react";
import { apiRequest, type Book, type BookPage } from "@/lib/api";
import { getSupabaseClient } from "@/lib/supabase";
import { LearningLoop } from "@/components/learning/LearningLoop";
import { ShelfBookCard } from "@/components/learning/ShelfBookCard";

const maxUploadMb = 50;
const emptyPages: BookPage[] = [];
type ShelfBook = { id: string; path_percent: number; core_percent: number; topics_understood: number; topics_total: number; next_day: number | null; next_minutes: number };

function formatBytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
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
  const [shelf, setShelf] = useState<ShelfBook[]>([]);
  const [selectedBookId, setSelectedBookId] = useState("");
  const [pageState, setPageState] = useState<{ bookId: string; pages: BookPage[] } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedBook = books.find((book) => book.id === selectedBookId) ?? null;
  const pages = pageState?.bookId === selectedBookId ? pageState.pages : emptyPages;
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
    if (!accessToken) return;
    let active = true;
    void apiRequest<ShelfBook[]>("/api/shelf", accessToken)
      .then((result) => { if (active) setShelf(result); })
      .catch(() => { if (active) setShelf([]); });
    return () => { active = false; };
  }, [accessToken, books.length]);

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
      setMessage(saved.duplicate ? "Already in your library. Picking up where you left it." : "Saved to your private library.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not upload this PDF.");
    } finally {
      setUploading(false);
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
            {books.map((book, index) => {
              const progress = shelf.find((item) => item.id === book.id);
              return (
                <ShelfBookCard
                  key={book.id}
                  index={index}
                  selected={selectedBookId === book.id}
                  onSelect={() => setSelectedBookId(book.id)}
                  book={{
                    id: book.id,
                    title: book.title || "Untitled book",
                    page_count: book.page_count,
                    path_percent: progress?.path_percent ?? 0,
                    topics_understood: progress?.topics_understood ?? 0,
                    topics_total: progress?.topics_total ?? 0,
                    next_day: progress?.next_day ?? null,
                    next_minutes: progress?.next_minutes ?? null,
                  }}
                />
              );
            })}
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
                      {selectedBook.needs_ocr && <p className="scan-note" role="status">This PDF appears scanned. Text recognition is not available, so learning generation is paused.</p>}
                    </div>
                    <div className="book-actions">
                      <button className="small-action" onClick={() => void openStoredPdf()} type="button"><BookOpen size={15} /> Open PDF</button>
                      <button className="small-action small-action-danger" onClick={() => void handleDelete()} type="button"><Trash2 size={15} /> Delete all</button>
                    </div>
                  </section>

                  {!selectedBook.needs_ocr && <LearningLoop
                    bookId={selectedBook.id}
                    accessToken={accessToken}
                    pages={pages}
                    refreshKey={selectedBook.summary_json?.overview ?? ""}
                  />}
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
