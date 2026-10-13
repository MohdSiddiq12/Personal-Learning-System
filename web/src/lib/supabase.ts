import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | undefined;

export function getSupabaseClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key || url.includes("your-project") || key.includes("your-supabase")) {
    throw new Error("Add the Supabase URL and public key to web/.env.local.");
  }
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(url);
  } catch {
    throw new Error("The Supabase URL is invalid. Use the Project URL from Supabase Project Settings > API.");
  }
  if (
    parsedUrl.protocol !== "https:" && parsedUrl.hostname !== "localhost" && parsedUrl.hostname !== "127.0.0.1"
  ) {
    throw new Error("The Supabase URL must use HTTPS. Copy the Project URL from Supabase Project Settings > API.");
  }
  if (parsedUrl.username || parsedUrl.password || parsedUrl.search || parsedUrl.hash || parsedUrl.pathname !== "/") {
    throw new Error("The Supabase URL must be the project API base URL only, with no dashboard, auth, or REST path.");
  }
  if (!key.trim()) {
    throw new Error("Add the Supabase public key to web/.env.local.");
  }
  client ??= createClient(parsedUrl.origin, key.trim(), {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });
  return client;
}
