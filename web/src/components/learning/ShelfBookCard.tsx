import { BookOpen, ChevronRight } from "lucide-react";

export type ShelfBookCardData = {
  id: string;
  title: string;
  page_count: number;
  path_percent: number;
  topics_understood: number;
  topics_total: number;
  next_day: number | null;
  next_minutes: number | null;
};

export function ShelfBookCard({
  book,
  index,
  selected,
  onSelect,
}: {
  book: ShelfBookCardData;
  index: number;
  selected: boolean;
  onSelect: () => void;
}) {
  const title = book.title || "Untitled book";
  const progress = Math.max(0, Math.min(100, Math.round(book.path_percent)));
  return (
    <button
      aria-current={selected ? "true" : undefined}
      className={`book-link ${selected ? "book-link-active" : ""}`}
      onClick={onSelect}
      type="button"
    >
      <span className={`book-cover cover-${index % 4}`} aria-hidden="true"><BookOpen size={18} /></span>
      <span className="book-link-copy">
        <strong>{title}</strong>
        <small>{book.page_count} pages</small>
        <span
          className="shelf-progress-track"
          role="progressbar"
          aria-label={`${title} path progress`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
        ><span style={{ width: `${progress}%` }} /></span>
        <small>{progress}% path completed</small>
        <small>Core ideas {book.topics_understood} of {book.topics_total}</small>
        {book.next_day !== null && book.next_minutes !== null && (
          <small>Continue Day {book.next_day}, {book.next_minutes} min</small>
        )}
      </span>
      {selected && <ChevronRight size={15} aria-hidden="true" />}
    </button>
  );
}
