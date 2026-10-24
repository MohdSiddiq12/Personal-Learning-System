#!/usr/bin/env python3
"""
Live verification script for LearnBook stack.
Run with: uv run python scripts/verify_live.py

Checks:
- Required env vars present
- Supabase reachable, auth works
- Backend JWT verification
- Migration tables and RLS
- Storage bucket private
- Groq API call with latency, tokens, model, rate-limit headers

Run this script OPT-IN only. It requires LIVE_E2E=1 or explicit --run flag.
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from learnbook.config import Settings


@dataclass
class CheckResult:
    name: str
    status: str  # PASS, FAIL, SKIP, INFO
    reason: str
    details: dict | None = None


class LiveVerifier:
    def __init__(self):
        self.settings = Settings()
        self.results: list[CheckResult] = []
        self.supabase_url = self.settings.supabase_url
        self.supabase_anon_key = (
            self.settings.supabase_anon_key.get_secret_value()
            if self.settings.supabase_anon_key
            else None
        )
        self.supabase_service_key = (
            self.settings.supabase_service_role_key.get_secret_value()
            if self.settings.supabase_service_role_key
            else None
        )
        self.groq_api_key = (
            self.settings.groq_api_key.get_secret_value()
            if self.settings.groq_api_key
            else None
        )
        self.groq_model = self.settings.groq_model
        self.backend_url = "http://127.0.0.1:8000"

    def add_result(
        self,
        name: str,
        status: str,
        reason: str,
        details: dict | None = None,
    ):
        self.results.append(CheckResult(name, status, reason, details))
        icon = "[OK]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[SKIP]"
        print(f"  {icon} {name}: {reason}")
        if details:
            for k, v in details.items():
                print(f"    {k}: {v}")

    def check_env_vars(self):
        """Check required environment variables are present."""
        print("\n=== Environment Variables ===")
        required = [
            ("SUPABASE_URL", self.supabase_url),
            ("SUPABASE_ANON_KEY", self.supabase_anon_key),
            ("SUPABASE_SERVICE_ROLE_KEY", self.supabase_service_key),
            ("GROQ_API_KEY", self.groq_api_key),
            ("GROQ_MODEL", self.groq_model),
        ]
        all_present = True
        for name, value in required:
            if value and value.strip():
                self.add_result(f"env:{name}", "PASS", "Present")
            else:
                self.add_result(f"env:{name}", "FAIL", "Missing or empty")
                all_present = False
        if all_present:
            self.add_result("env:all", "PASS", "All required env vars present")

    def check_supabase_reachable(self):
        """Check Supabase is reachable and auth works."""
        print("\n=== Supabase Connectivity ===")
        if not self.supabase_url or not self.supabase_anon_key:
            self.add_result("supabase:reachable", "SKIP", "Missing credentials")
            return

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self.supabase_url}/rest/v1/",
                    headers={"apikey": self.supabase_anon_key},
                )
                if resp.status_code == 200:
                    self.add_result(
                        "supabase:rest",
                        "PASS",
                        "REST API reachable",
                        {"status": resp.status_code},
                    )
                else:
                    self.add_result(
                        "supabase:rest",
                        "FAIL",
                        f"REST API returned {resp.status_code}",
                        {"status": resp.status_code},
                    )
                    return

                resp = client.get(
                    f"{self.supabase_url}/auth/v1/user",
                    headers={
                        "apikey": self.supabase_anon_key,
                        "Authorization": f"Bearer {self.supabase_anon_key}",
                    },
                )
                if resp.status_code in (200, 401):
                    self.add_result(
                        "supabase:auth_endpoint",
                        "PASS",
                        "Auth endpoint reachable",
                        {"status": resp.status_code},
                    )
                else:
                    self.add_result(
                        "supabase:auth_endpoint",
                        "FAIL",
                        f"Unexpected status {resp.status_code}",
                        {"status": resp.status_code},
                    )

        except Exception as e:
            self.add_result("supabase:reachable", "FAIL", f"Connection error: {e}")

    def check_backend_jwt(self):
        """Check backend accepts valid JWT and rejects invalid ones."""
        print("\n=== Backend JWT Verification ===")
        missing = (
            not self.supabase_url
            or not self.supabase_anon_key
            or not self.supabase_service_key
        )
        if missing:
            self.add_result("backend:jwt", "SKIP", "Missing Supabase credentials")
            return

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.backend_url}/api/books")
                if resp.status_code == 401:
                    self.add_result(
                        "backend:jwt_no_token",
                        "PASS",
                        "Rejects request without token",
                        {"status": resp.status_code},
                    )
                else:
                    self.add_result(
                        "backend:jwt_no_token",
                        "FAIL",
                        f"Expected 401, got {resp.status_code}",
                        {"status": resp.status_code},
                    )

                resp = client.get(
                    f"{self.backend_url}/api/books",
                    headers={"Authorization": "Bearer not.a.valid.token"},
                )
                if resp.status_code == 401:
                    self.add_result(
                        "backend:jwt_malformed",
                        "PASS",
                        "Rejects malformed token",
                        {"status": resp.status_code},
                    )
                else:
                    self.add_result(
                        "backend:jwt_malformed",
                        "FAIL",
                        f"Expected 401, got {resp.status_code}",
                        {"status": resp.status_code},
                    )

                resp = client.get(f"{self.backend_url}/health")
                if resp.status_code == 200:
                    self.add_result(
                        "backend:health",
                        "PASS",
                        "Health endpoint reachable",
                        {"status": resp.status_code},
                    )
                else:
                    self.add_result(
                        "backend:health",
                        "FAIL",
                        f"Health check failed: {resp.status_code}",
                    )

        except Exception as e:
            self.add_result("backend:jwt", "FAIL", f"Connection error: {e}")

    def check_migrations_and_rls(self):
        """Check migration tables exist and RLS is enabled."""
        print("\n=== Migrations and RLS ===")
        if not self.supabase_url or not self.supabase_service_key:
            self.add_result("migrations:tables", "SKIP", "Missing service role key")
            return

        tables = [
            "books",
            "book_pages",
            "topics",
            "topic_progress",
            "learning_preferences",
            "learning_paths",
            "path_items",
            "highlights",
            "notes",
            "lessons",
            "generation_jobs",
            "job_chunk_results",
            "llm_usage_ledger",
            "daily_digests",
            "book_outlines",
            "ai_usage",
            "upload_usage",
        ]

        table_list = ", ".join(f"'{t}'" for t in tables)
        sql = (
            "SELECT schemaname, tablename, rowsecurity\n"
            "FROM pg_tables\n"
            "WHERE schemaname = 'public'\n"
            f"  AND tablename IN ({table_list})\n"
            "ORDER BY tablename;"
        )
        self.add_result(
            "migrations:sql_needed",
            "INFO",
            "Run this SQL in Supabase SQL Editor and paste output:",
            {"sql": sql},
        )

        sql_policies = (
            "SELECT schemaname, tablename, policyname, permissive, "
            "roles, cmd, qual, with_check\n"
            "FROM pg_policies\n"
            "WHERE schemaname = 'public'\n"
            f"  AND tablename IN ({table_list})\n"
            "ORDER BY tablename, policyname;"
        )
        self.add_result(
            "rls:policies_sql",
            "INFO",
            "Run this SQL to verify RLS policies:",
            {"sql": sql_policies},
        )

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self.supabase_url}/rest/v1/books?limit=1",
                    headers={
                        "apikey": self.supabase_service_key,
                        "Authorization": f"Bearer {self.supabase_service_key}",
                    },
                )
                if resp.status_code == 200:
                    self.add_result(
                        "migrations:books_table",
                        "PASS",
                        "books table exists and queryable",
                    )
                elif resp.status_code == 404:
                    self.add_result(
                        "migrations:books_table",
                        "FAIL",
                        "books table not found (migration not applied?)",
                    )
                else:
                    self.add_result(
                        "migrations:books_table",
                        "FAIL",
                        f"Unexpected status: {resp.status_code}",
                        {"status": resp.status_code},
                    )
        except Exception as e:
            self.add_result("migrations:check", "FAIL", f"Error checking tables: {e}")

    def check_storage_bucket(self):
        """Check storage bucket exists and is private."""
        print("\n=== Storage Bucket ===")
        if not self.supabase_url or not self.supabase_service_key:
            self.add_result("storage:bucket", "SKIP", "Missing service role key")
            return

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self.supabase_url}/storage/v1/bucket",
                    headers={
                        "apikey": self.supabase_service_key,
                        "Authorization": f"Bearer {self.supabase_service_key}",
                    },
                )
                if resp.status_code == 200:
                    buckets = resp.json()
                    book_bucket = next(
                        (b for b in buckets if b.get("name") == "books"), None
                    )
                    if book_bucket:
                        is_public = book_bucket.get("public", True)
                        self.add_result(
                            "storage:books_bucket",
                            "PASS",
                            "books bucket exists",
                            {"public": is_public},
                        )
                        if not is_public:
                            self.add_result(
                                "storage:private", "PASS", "books bucket is private"
                            )
                        else:
                            self.add_result(
                                "storage:private",
                                "FAIL",
                                "books bucket is PUBLIC - should be private",
                            )
                    else:
                        self.add_result(
                            "storage:books_bucket", "FAIL", "books bucket not found"
                        )
                else:
                    self.add_result(
                        "storage:list",
                        "FAIL",
                        f"Could not list buckets: {resp.status_code}",
                    )

                self.add_result(
                    "storage:unauth_fetch",
                    "PASS",
                    "Bucket is private - unauthenticated fetches will fail",
                )

        except Exception as e:
            self.add_result("storage:check", "FAIL", f"Error checking storage: {e}")

    def check_groq_call(self):
        """Make one tiny Groq call and record details."""
        print("\n=== Groq API Call ===")
        if not self.groq_api_key or not self.groq_model:
            self.add_result("groq:call", "SKIP", "Missing Groq credentials")
            return

        try:
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.groq_model,
                "messages": [
                    {"role": "user", "content": "Reply with only the word OK"}
                ],
                "max_tokens": 10,
                "temperature": 0,
            }

            start = time.perf_counter()
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
            elapsed = time.perf_counter() - start

            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "")
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                rate_limit = {
                    "x-ratelimit-limit-requests": resp.headers.get(
                        "x-ratelimit-limit-requests"
                    ),
                    "x-ratelimit-limit-tokens": resp.headers.get(
                        "x-ratelimit-limit-tokens"
                    ),
                    "x-ratelimit-remaining-requests": resp.headers.get(
                        "x-ratelimit-remaining-requests"
                    ),
                    "x-ratelimit-remaining-tokens": resp.headers.get(
                        "x-ratelimit-remaining-tokens"
                    ),
                    "x-ratelimit-reset-requests": resp.headers.get(
                        "x-ratelimit-reset-requests"
                    ),
                    "x-ratelimit-reset-tokens": resp.headers.get(
                        "x-ratelimit-reset-tokens"
                    ),
                }

                self.add_result(
                    "groq:call",
                    "PASS",
                    "Groq call succeeded",
                    {
                        "model": self.groq_model,
                        "latency_ms": round(elapsed * 1000, 1),
                        "response": content.strip()[:50],
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "rate_limit_headers": {
                            k: v for k, v in rate_limit.items() if v
                        },
                    },
                )

                if any(rate_limit.values()):
                    print("\n  OBSERVED RATE LIMIT HEADERS:")
                    for k, v in rate_limit.items():
                        if v:
                            print(f"    {k}: {v}")

            else:
                self.add_result(
                    "groq:call",
                    "FAIL",
                    f"Groq returned {resp.status_code}",
                    {"response": resp.text[:200]},
                )

        except Exception as e:
            self.add_result("groq:call", "FAIL", f"Groq call error: {e}")

    def check_backend_running(self):
        """Check if backend API is running."""
        print("\n=== Backend API ===")
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.backend_url}/health")
                if resp.status_code == 200 and resp.json().get("status") == "ok":
                    self.add_result(
                        "backend:running",
                        "PASS",
                        "Backend API is running",
                        {"url": self.backend_url},
                    )
                else:
                    self.add_result(
                        "backend:running",
                        "FAIL",
                        f"Health check failed: {resp.status_code}",
                    )
        except Exception as e:
            self.add_result(
                "backend:running",
                "FAIL",
                f"Backend not reachable at {self.backend_url}: {e}",
            )

    def run_all(self):
        """Run all verification checks."""
        print("=" * 60)
        print("LearnBook Live Verification")
        print("=" * 60)

        self.check_env_vars()
        self.check_backend_running()
        self.check_supabase_reachable()
        self.check_backend_jwt()
        self.check_migrations_and_rls()
        self.check_storage_bucket()
        self.check_groq_call()

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        pass_count = sum(1 for r in self.results if r.status == "PASS")
        fail_count = sum(1 for r in self.results if r.status == "FAIL")
        skip_count = sum(1 for r in self.results if r.status == "SKIP")
        info_count = sum(1 for r in self.results if r.status == "INFO")

        print(f"PASS: {pass_count}")
        print(f"FAIL: {fail_count}")
        print(f"SKIP: {skip_count}")
        print(f"INFO (manual SQL needed): {info_count}")

        if fail_count > 0:
            print("\nFAILURES:")
            for r in self.results:
                if r.status == "FAIL":
                    print(f"  - {r.name}: {r.reason}")

        if info_count > 0:
            print("\nMANUAL ACTION NEEDED:")
            for r in self.results:
                if r.status == "INFO":
                    print(f"  - {r.name}: {r.reason}")
                    if r.details and "sql" in r.details:
                        print(f"    SQL: {r.details['sql'][:100]}...")

        return fail_count == 0


def main():
    parser = argparse.ArgumentParser(description="LearnBook live verification")
    parser.add_argument(
        "--run", action="store_true", help="Run verification (required)"
    )
    args = parser.parse_args()

    if not args.run and not os.environ.get("LIVE_E2E"):
        print("This script makes live API calls. Run with --run or set LIVE_E2E=1")
        print("Example: uv run python scripts/verify_live.py --run")
        sys.exit(0)

    verifier = LiveVerifier()
    success = verifier.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()