import re
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.utils.response import ok
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException

logger = get_logger("routers.search")
router = APIRouter(prefix="/api/v1/documents", tags=["search"])


def _sanitize_fts5_query(query: str) -> str:
    """Sanitize user input for FTS5 MATCH query.

    Strategy: Tokenize and use AND + prefix matching.
    If the user explicitly wraps the query in double quotes, use phrase search.
    """
    cleaned = "".join(ch for ch in query if ch in ("\t", "\n", "\r") or (ord(ch) >= 32)).strip()
    
    # If the user explicitly uses double quotes, keep it as phrase search
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
        inner = cleaned[1:-1].replace('"', '""')
        if not inner.strip():
            raise AppException(code=4001, message="Search query is empty or invalid", status_code=400)
        return f'"{inner}"'

    tokens = re.findall(r"[0-9A-Za-z\u4e00-\u9fff]+", cleaned)
    if not tokens:
        raise AppException(code=4001, message="Search query is empty or invalid", status_code=400)
    return " AND ".join(f"{t}*" for t in tokens)


@router.get("/search")
def search_documents(
    q: str = Query(..., min_length=1, max_length=200),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    try:
        safe_query = _sanitize_fts5_query(q)
    except AppException as e:
        raise e

    # Execute 2 queries instead of window function to avoid FTS5 function restrictions
    count_sql = text("""
        SELECT COUNT(*)
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.rowid
        WHERE documents_fts MATCH :query
          AND d.user_id = :user_id
    """)

    data_sql = text("""
        SELECT d.id, d.title, d.file_type, d.status, d.created_at,
               snippet(documents_fts, 1, '...', '...', '...', 64) as snippet
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.rowid
        WHERE documents_fts MATCH :query
          AND d.user_id = :user_id
        ORDER BY bm25(documents_fts)
        LIMIT :limit OFFSET :offset
    """)

    try:
        # Count total
        count_result = db.execute(count_sql, {
            "query": safe_query,
            "user_id": current_user.id
        })
        total = count_result.scalar() or 0

        # fetch items
        result = db.execute(data_sql, {
            "query": safe_query,
            "user_id": current_user.id,
            "limit": limit,
            "offset": offset,
        })
        rows = result.fetchall()
    except DatabaseError as e:
        logger.error(f"Database error during search: {e}")
        raise AppException(code=4002, message="Invalid search query", status_code=400)

    items = []
    for row in rows:
        created = row.created_at
        if created and not isinstance(created, str):
            created = created.isoformat()
        items.append({
            "id": row.id,
            "title": row.title,
            "file_type": row.file_type,
            "status": row.status,
            "snippet": row.snippet or "",
            "created_at": created,
        })

    return ok(data={"items": items, "total": total, "page": page, "limit": limit})
