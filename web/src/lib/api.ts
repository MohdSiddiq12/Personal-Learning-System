export type StudyIdea = {
  title: string;
  explanation: string;
  pages: number[];
};

export type PracticeQuestion = {
  question: string;
  suggested_action: string;
  pages: number[];
};

export type BookSummary = {
  overview: string;
  key_ideas: StudyIdea[];
  frameworks: StudyIdea[];
  practice: PracticeQuestion[];
};

export type Book = {
  id: string;
  title: string | null;
  author: string | null;
  page_count: number;
  file_size_bytes: number;
  needs_ocr: boolean;
  created_at: string | null;
  summary_json: BookSummary | null;
  duplicate?: boolean;
};

export type BookPage = {
  page_number: number;
  text: string;
  char_count: number;
  is_empty: boolean;
  has_images: boolean;
};

export type GenerationJob = {
  id: string;
  kind: "map" | "lesson";
  status: "queued" | "running" | "done" | "failed";
  step: string;
  progress_pct: number;
  total_chunks: number;
  done_chunks: number;
  error_code: string | null;
  error_message: string | null;
};

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export async function apiRequest<T>(
  path: string,
  accessToken: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, { ...init, headers });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Could not reach the LearnBook API. Start the backend at the configured NEXT_PUBLIC_API_URL, or check that production setting and redeploy the frontend.",
      );
    }
    throw error;
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail ?? "The request could not be completed.");
  }
  return payload as T;
}
