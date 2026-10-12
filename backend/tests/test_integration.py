"""Needs a running Postgres with db/init.sql applied (CI provides one). Skips otherwise."""
import uuid

import httpx
import pytest

from app import db
from app.config import settings
from app.main import app
from app.services.ingest import ingest_document


@pytest.fixture
async def client(monkeypatch):
    settings.embed_provider, settings.llm_chain = "fake", "fake:fake"
    try:
        await db.init_pool()
    except Exception:
        pytest.skip("database not available")

    async def inline(document_id):
        await ingest_document(document_id)

    monkeypatch.setattr("app.routers.documents.enqueue_ingest", inline)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        c.tag = uuid.uuid4().hex[:8]
        yield c
    await db.pool.execute("DELETE FROM users WHERE email LIKE $1", f"%{c.tag}@test.io")
    await db.close_pool()


async def register(c, name):
    r = await c.post("/auth/register", json={"email": f"{name}{c.tag}@test.io", "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def test_user_isolation(client):
    a, b = await register(client, "a"), await register(client, "b")
    r = await client.post("/documents", headers=a,
                          files={"file": ("secret.txt", b"The launch code is PURPLE-ELEPHANT-42.", "text/plain")})
    assert r.status_code == 202
    doc_id = r.json()["id"]

    assert (await client.get(f"/documents/{doc_id}", headers=a)).json()["status"] == "ready"
    assert (await client.get(f"/documents/{doc_id}", headers=b)).status_code == 404
    assert (await client.get(f"/documents/{doc_id}/file", headers=b)).status_code == 404
    assert (await client.delete(f"/documents/{doc_id}", headers=b)).status_code == 404
    assert (await client.get("/documents", headers=b)).json() == []

    q = {"question": "What is the launch code PURPLE-ELEPHANT?"}
    ra = await client.post("/chat", headers=a, json=q)
    assert doc_id in ra.text and "event: done" in ra.text
    rb = await client.post("/chat", headers=b, json=q)
    assert "PURPLE-ELEPHANT-42" not in rb.text and doc_id not in rb.text


async def test_refuses_without_evidence(client):
    a = await register(client, "c")
    r = await client.post("/chat", headers=a, json={"question": "anything at all?"})
    assert "couldn't find this in your documents" in r.text


async def test_chat_quota_enforced(client):
    a = await register(client, "d")
    await db.pool.execute("UPDATE users SET daily_token_quota = 0 WHERE email = $1", f"d{client.tag}@test.io")
    r = await client.post("/chat", headers=a, json={"question": "hi"})
    assert r.status_code == 429


async def test_doc_quota_enforced(client):
    a = await register(client, "e")
    await db.pool.execute("UPDATE users SET max_documents = 1 WHERE email = $1", f"e{client.tag}@test.io")
    f = {"file": ("x.txt", b"hello world", "text/plain")}
    assert (await client.post("/documents", headers=a, files=f)).status_code == 202
    assert (await client.post("/documents", headers=a, files={"file": ("y.txt", b"again", "text/plain")})).status_code == 429


async def test_requires_auth(client):
    assert (await client.get("/documents")).status_code == 401
