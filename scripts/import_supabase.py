"""
Step 6 of the knowledge pipeline: copy verified records into the Supabase `knowledge` table.

    backend/.venv/Scripts/python scripts/import_supabase.py

Uses the backend's secret key (knowledge is write-protected from browsers by RLS). Upserts by a
deterministic UUID derived from the record id, so re-running updates instead of duplicating.
Requires migration 20260924010000_knowledge_sources.sql (source_url, retrieved_at, verification_status…).
"""
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.database.supabase import get_supabase_client  # noqa: E402

IN = ROOT / "data" / "verified" / "knowledge.jsonl"
NAMESPACE = uuid.UUID("7f3c1a52-2b8e-4a55-9c1d-6f0e1b2a3c4d")


def to_row(r: dict) -> dict:
    return {
        "id": str(uuid.uuid5(NAMESPACE, r["id"])),
        "external_id": r["id"],
        "pair_id": r.get("pair_id"),
        "crop": r["crop"],
        "topic": r["topic"],
        "subtopic": r.get("subtopic"),
        "language": r["language"],
        "title": r["title"],
        "content": r["content"],
        "keywords": [k for k in r.get("keywords", []) if k],
        "source": r["source"],
        "publisher": r["publisher"],
        "source_url": r["source_url"],
        "retrieved_at": r["retrieved_at"],
        "verification_status": r["verification_status"],
        "verification_required": r["verification_status"] != "expert_verified",
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    client = get_supabase_client()
    if client is None:
        raise SystemExit("Supabase is not configured (backend/.env).")
    rows = [to_row(json.loads(l)) for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]
    for start in range(0, len(rows), 200):
        client.table("knowledge").upsert(rows[start : start + 200], on_conflict="id").execute()
    count = client.table("knowledge").select("id", count="exact", head=True).execute().count
    print(f"upserted {len(rows)} records; knowledge table now holds {count}")


if __name__ == "__main__":
    main()
