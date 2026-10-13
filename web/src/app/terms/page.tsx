import Link from "next/link";
import "./terms.css";

export default function TermsPage() {
  const takedownEmail = process.env.NEXT_PUBLIC_TAKEDOWN_EMAIL;

  return (
    <main className="terms-shell">
      <Link href="/" className="terms-back">← Back to LearnBook</Link>
      <p className="eyebrow">PUBLIC LAUNCH DRAFT</p>
      <h1>Terms, privacy & copyright</h1>
      <p className="terms-warning">This is product copy, not legal advice. Have qualified counsel review it before public launch.</p>
      <section>
        <h2>Use books you are entitled to study</h2>
        <p>Upload only material you own or are otherwise entitled to use for personal study. Do not upload books to share or redistribute them. LearnBook stores your PDF privately for your account, plus extracted page text and the guide you request.</p>
      </section>
      <section>
        <h2>Your data</h2>
        <p>Your library is account-scoped. You can delete an individual book or clear the whole library, including stored PDFs, extracted pages, and generated guides. AI guide generation is optional and sends extracted text to Google Gemini only after you enter a key and confirm the provider notice.</p>
      </section>
      <section>
        <h2>Copyright and takedown</h2>
        <p>For a copyright concern or takedown request, contact {takedownEmail || "the site operator (takedown email not configured)"}. Configure NEXT_PUBLIC_TAKEDOWN_EMAIL before publishing.</p>
      </section>
    </main>
  );
}