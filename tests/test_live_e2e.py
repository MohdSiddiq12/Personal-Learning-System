import asyncio
import os
import sys
import time
from pathlib import Path

import httpx
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))



# Skip unless explicitly enabled
pytestmark = pytest.mark.skipif(
    not os.environ.get("LIVE_E2E"),
    reason="Live E2E test requires LIVE_E2E=1 environment variable",
)


LIVE_E2E = os.environ.get("LIVE_E2E") == "1"
BACKEND_URL = "http://127.0.0.1:8000"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")


class LiveE2ETest:
    def __init__(self):
        self.access_token = None
        self.user_id = None
        self.book_id = None
        self.topic_ids = []
        self.timings = {}

    async def sign_in(self, email: str, password: str) -> str:
        """Sign in via Supabase Auth and return access token."""
        headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers=headers,
                json={"email": email, "password": password},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Sign in failed: {resp.status_code} {resp.text}")
            data = resp.json()
            self.access_token = data["access_token"]
            return self.access_token

    async def upload_pdf(self, pdf_path: Path) -> str:
        """Upload a PDF and return book_id."""
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(pdf_path, "rb") as f:
                resp = await client.post(
                    f"{BACKEND_URL}/api/books",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    files={"file": (pdf_path.name, f, "application/pdf")},
                )
        elapsed = time.perf_counter() - start
        self.timings["upload"] = elapsed
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Upload failed: {resp.status_code} {resp.text}")
        self.book_id = resp.json()["id"]
        return self.book_id

    async def wait_for_processing(self, max_wait: int = 120) -> dict:
        """Wait for PDF processing to complete."""
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            for _ in range(max_wait):
                resp = await client.get(
                    f"{BACKEND_URL}/api/books/{self.book_id}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                if resp.status_code == 200:
                    book = resp.json()
                    if book.get("page_count", 0) > 0:
                        elapsed = time.perf_counter() - start
                        self.timings["processing"] = elapsed
                        return book
                await asyncio.sleep(1)
        raise RuntimeError("PDF processing timed out")

    async def create_map_job(self) -> str:
        """Create a book map generation job."""
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/books/{self.book_id}/map-jobs",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={"consent": True},
            )
        elapsed = time.perf_counter() - start
        self.timings["map_job_create"] = elapsed
        if resp.status_code != 200:
            raise RuntimeError(
                f"Map job creation failed: {resp.status_code} {resp.text}"
            )
        job_id = resp.json()["id"]
        return job_id

    async def wait_for_map_job(self, job_id: str, max_wait: int = 300) -> dict:
        """Wait for map job to complete."""
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            for _ in range(max_wait):
                resp = await client.get(
                    f"{BACKEND_URL}/api/map-jobs/{job_id}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"Job status check failed: {resp.status_code}")
                job = resp.json()
                if job["status"] == "completed":
                    elapsed = time.perf_counter() - start
                    self.timings["map_job_total"] = elapsed
                    return job
                elif job["status"] == "failed":
                    raise RuntimeError(f"Map job failed: {job.get('error_message')}")
                await asyncio.sleep(2)
        raise RuntimeError("Map job timed out")

    async def get_book_map(self) -> dict:
        """Get the generated book map."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BACKEND_URL}/api/books/{self.book_id}/map",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        if resp.status_code != 200:
            raise RuntimeError(f"Get map failed: {resp.status_code} {resp.text}")
        return resp.json()

    async def set_preferences(
        self, daily_minutes: int = 30, minutes_per_topic: int = 10
    ):
        """Set learning preferences."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        json_data = {
            "daily_minutes": daily_minutes,
            "minutes_per_topic": minutes_per_topic,
            "goal": "understand",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"{BACKEND_URL}/api/books/{self.book_id}/preferences",
                headers=headers,
                json=json_data,
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Set preferences failed: {resp.status_code} {resp.text}"
            )

    async def build_path(self) -> dict:
        """Build learning path."""
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/books/{self.book_id}/path",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        elapsed = time.perf_counter() - start
        self.timings["build_path"] = elapsed
        if resp.status_code != 200:
            raise RuntimeError(f"Build path failed: {resp.status_code} {resp.text}")
        return resp.json()

    async def get_topic_lesson(self, topic_id: str) -> dict:
        """Get or generate a lesson for a topic."""
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Try cached first
            resp = await client.get(
                f"{BACKEND_URL}/api/topics/{topic_id}/lesson",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            if resp.status_code == 200:
                lesson = resp.json()
                elapsed = time.perf_counter() - start
                self.timings[f"lesson_{topic_id}_cached"] = elapsed
                return lesson

            # Generate if not cached
            resp = await client.post(
                f"{BACKEND_URL}/api/topics/{topic_id}/lesson-jobs",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={"target_minutes": 10, "consent": True},
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Lesson job creation failed: {resp.status_code} {resp.text}"
                )
            job_id = resp.json()["id"]

            # Wait for lesson job
            for _ in range(60):
                resp = await client.get(
                    f"{BACKEND_URL}/api/topics/{topic_id}/lesson-jobs/{job_id}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                job = resp.json()
                if job["status"] == "completed":
                    break
                await asyncio.sleep(1)

            # Get the lesson
            resp = await client.get(
                f"{BACKEND_URL}/api/topics/{topic_id}/lesson",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        elapsed = time.perf_counter() - start
        self.timings[f"lesson_{topic_id}_total"] = elapsed
        return resp.json()

    async def add_note(self, topic_id: str, body: str) -> dict:
        """Add a note to a topic."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/books/{self.book_id}/notes",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={"topic_id": topic_id, "body": body},
            )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Add note failed: {resp.status_code} {resp.text}")
        return resp.json()

    async def update_topic_status(self, topic_id: str, status: str):
        """Update topic status."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"{BACKEND_URL}/api/topics/{topic_id}/status",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={"status": status},
            )
        if resp.status_code != 200:
            raise RuntimeError(f"Update status failed: {resp.status_code} {resp.text}")

    async def complete_path_item(self, path_item_id: str):
        """Mark path item as complete."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/path-items/{path_item_id}/complete",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Complete path item failed: {resp.status_code} {resp.text}"
            )

    async def run_full_flow(self, pdf_path: Path, email: str, password: str):
        """Run the complete live E2E flow."""
        print("\n=== LIVE E2E SMOKE TEST ===")
        print(f"PDF: {pdf_path}")
        print(f"User: {email}")

        # 1. Sign in
        print("\n1. Signing in...")
        await self.sign_in(email, password)
        print("   OK - Got access token")

        # 2. Upload PDF
        print("\n2. Uploading PDF...")
        await self.upload_pdf(pdf_path)
        print(f"   OK - Book ID: {self.book_id} ({self.timings['upload']:.1f}s)")

        # 3. Wait for processing
        print("\n3. Waiting for PDF processing...")
        book = await self.wait_for_processing()
        pages = book.get("page_count")
        print(f"   OK - Pages: {pages} ({self.timings['processing']:.1f}s)")

        # 4. Create map job
        print("\n4. Creating map job...")
        job_id = await self.create_map_job()
        print(f"   OK - Job ID: {job_id} ({self.timings['map_job_create']:.1f}s)")

        # 5. Wait for map job
        print("\n5. Waiting for map job completion...")
        await self.wait_for_map_job(job_id)
        print(f"   OK - Job completed ({self.timings['map_job_total']:.1f}s)")

        # 6. Get book map
        print("\n6. Getting book map...")
        book_map = await self.get_book_map()
        topics = book_map.get("topics", [])
        self.topic_ids = [t["id"] for t in topics]
        print(f"   OK - Topics: {len(topics)}")

        # 7. Set preferences
        print("\n7. Setting preferences...")
        await self.set_preferences(daily_minutes=30, minutes_per_topic=10)
        print("   OK")

        # 8. Build path
        print("\n8. Building learning path...")
        path = await self.build_path()
        items = path.get("items", [])
        print(f"   OK - Path items: {len(items)} ({self.timings['build_path']:.1f}s)")

        # 9. Get lesson for first topic
        if self.topic_ids:
            print("\n9. Getting lesson for first topic...")
            lesson = await self.get_topic_lesson(self.topic_ids[0])
            print(f"   OK - Lesson body length: {len(lesson.get('body', ''))}")

        # 10. Add note
        if self.topic_ids:
            print("\n10. Adding note...")
            await self.add_note(self.topic_ids[0], "Live E2E test note")
            print("   OK")

        # 11. Update topic status
        if self.topic_ids:
            print("\n11. Updating topic status...")
            await self.update_topic_status(self.topic_ids[0], "learning")
            print("   OK")

        # 12. Complete first path item
        path_items = path.get("items", [])
        if path_items:
            print("\n12. Completing first path item...")
            await self.complete_path_item(path_items[0]["id"])
            print("   OK")

        # Print summary
        print("\n=== TIMING SUMMARY ===")
        total = sum(self.timings.values())
        for step, t in self.timings.items():
            print(f"  {step}: {t:.1f}s")
        print(f"  TOTAL: {total:.1f}s")

        return self.timings


@pytest.mark.asyncio
async def test_live_e2e_smoke():
    """Run live E2E smoke test against real services."""
    if not LIVE_E2E:
        pytest.skip("LIVE_E2E not set")

    # Check required env vars
    required = {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
        "GROQ_API_KEY": GROQ_API_KEY,
        "LIVE_E2E_EMAIL": os.environ.get("LIVE_E2E_EMAIL"),
        "LIVE_E2E_PASSWORD": os.environ.get("LIVE_E2E_PASSWORD"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        pytest.skip(f"Missing required env vars: {missing}")

    # Use sample PDF
    pdf_path = Path("data/samples/sample_book.pdf")
    if not pdf_path.exists():
        pytest.skip(f"Sample PDF not found at {pdf_path}")

    test = LiveE2ETest()
    timings = await test.run_full_flow(
        pdf_path,
        os.environ["LIVE_E2E_EMAIL"],
        os.environ["LIVE_E2E_PASSWORD"],
    )

    # Assert basic success criteria
    assert timings["upload"] < 30, "Upload took too long"
    assert timings["processing"] < 60, "Processing took too long"
    assert timings.get("map_job_total", 0) < 300, "Map job took too long"
    assert len(test.topic_ids) > 0, "No topics generated"


if __name__ == "__main__":
    # Allow running directly for manual testing
    if os.environ.get("LIVE_E2E"):
        test = LiveE2ETest()
        asyncio.run(
            test.run_full_flow(
                Path("data/samples/sample_book.pdf"),
                os.environ["LIVE_E2E_EMAIL"],
                os.environ["LIVE_E2E_PASSWORD"],
            )
        )