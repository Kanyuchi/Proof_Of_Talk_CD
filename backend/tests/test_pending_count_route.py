"""Regression test for the /matches/pending-count route shadowing bug.

`GET /matches/{attendee_id}` (attendee_id: UUID) was declared before the
static `GET /matches/pending-count`, so Starlette matched "pending-count" as
an attendee_id, failed UUID validation, and returned 422 — the real
pending-count handler was unreachable. Static routes must precede the
parameterized catch-all.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.core.deps import require_auth
from app.core.database import get_db


async def _fake_db():
    yield None  # handler returns early for attendee_id=None, never touches db


# TestClient WITHOUT the context manager so app lifespan (scheduler.start) never
# runs — we only exercise routing + dependency resolution.
app.dependency_overrides[require_auth] = lambda: SimpleNamespace(attendee_id=None)
app.dependency_overrides[get_db] = _fake_db
# raise_server_exceptions=False: the parameterized route's handler touches the
# (stubbed None) db and 500s — we want that as a response, not a raised error,
# so the 422-vs-not assertion is what's under test.
client = TestClient(app, raise_server_exceptions=False)


def test_pending_count_is_not_shadowed_by_attendee_id_route():
    r = client.get("/api/v1/matches/pending-count")
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
    assert r.json() == {"pending_count": 0}


def test_attendee_id_route_still_works_with_a_uuid():
    # A real UUID path still resolves to the matches list route (not 404),
    # proving the reorder didn't break the parameterized route.
    r = client.get("/api/v1/matches/00000000-0000-0000-0000-000000000000")
    assert r.status_code != 422, f"UUID path should not 422: {r.text}"
