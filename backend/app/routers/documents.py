from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import db
from ..config import settings
from ..deps import current_user
from ..queue import enqueue_ingest
from ..services.quotas import check_doc_quota

router = APIRouter(prefix="/documents", tags=["documents"])
ALLOWED = {".pdf", ".txt", ".md"}
PUBLIC = "id, filename, size_bytes, status, progress, error, pages, chunk_count, chunk_strategy, created_at"


async def _own_doc(doc_id: UUID, user_id) -> dict:
    row = await db.pool.fetchrow("SELECT * FROM documents WHERE id = $1 AND user_id = $2", doc_id, user_id)
    if not row:
        raise HTTPException(404, "Document not found")  # 404 (not 403) so existence isn't leaked
    return dict(row)


@router.post("", status_code=202)
async def upload(file: UploadFile, user: dict = Depends(current_user)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(415, f"Allowed types: {', '.join(sorted(ALLOWED))}")
    await check_doc_quota(user)

    doc_id = uuid4()
    dest = Path(settings.upload_dir) / str(user["id"]) / f"{doc_id}{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    size, limit = 0, settings.max_upload_mb * 1024 * 1024
    with open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB")
            f.write(chunk)

    row = await db.pool.fetchrow(
        f"INSERT INTO documents (id, user_id, filename, storage_path, size_bytes) VALUES ($1,$2,$3,$4,$5) RETURNING {PUBLIC}",
        doc_id, user["id"], Path(file.filename).name, str(dest), size)
    await enqueue_ingest(str(doc_id))
    return dict(row)


@router.get("")
async def list_documents(user: dict = Depends(current_user)):
    rows = await db.pool.fetch(f"SELECT {PUBLIC} FROM documents WHERE user_id = $1 ORDER BY created_at DESC", user["id"])
    return [dict(r) for r in rows]


@router.get("/{doc_id}")
async def get_document(doc_id: UUID, user: dict = Depends(current_user)):
    doc = await _own_doc(doc_id, user["id"])
    return {k: doc[k] for k in PUBLIC.replace(" ", "").split(",")}


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: UUID, user: dict = Depends(current_user)):
    doc = await _own_doc(doc_id, user["id"])
    await db.pool.execute("DELETE FROM documents WHERE id = $1", doc_id)  # chunks cascade
    Path(doc["storage_path"]).unlink(missing_ok=True)


@router.get("/{doc_id}/file")
async def get_file(doc_id: UUID, user: dict = Depends(current_user)):
    doc = await _own_doc(doc_id, user["id"])
    return FileResponse(doc["storage_path"], filename=doc["filename"])


@router.get("/{doc_id}/chunks/{chunk_id}")
async def get_passage(doc_id: UUID, chunk_id: int, user: dict = Depends(current_user)):
    """Powers 'click a citation -> jump to the passage' (with neighbouring chunks for context)."""
    await _own_doc(doc_id, user["id"])
    row = await db.pool.fetchrow(
        "SELECT id, idx, text, page, char_start, char_end, heading FROM chunks WHERE id = $1 AND document_id = $2 AND user_id = $3",
        chunk_id, doc_id, user["id"])
    if not row:
        raise HTTPException(404, "Passage not found")
    around = await db.pool.fetch(
        "SELECT idx, text FROM chunks WHERE document_id = $1 AND user_id = $2 AND idx IN ($3, $4) ORDER BY idx",
        doc_id, user["id"], row["idx"] - 1, row["idx"] + 1)
    return {**dict(row), "neighbors": [dict(r) for r in around]}
