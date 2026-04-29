from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.utils.response import ok
from backend.utils.logger import get_logger

logger = get_logger("routers.search")
router = APIRouter(prefix="/api/v1/documents", tags=["search"])


def _escape_fts5(query: str) -> str:
    """Escape FTS5 special characters to prevent injection."""
    # Remove FTS5 operators and wrap in quotes for phrase search
    cleaned = query.replace('"', '""').strip()
    if not cleaned:
        return '""'
    return f'"{cleaned}"'


@router.get("/search")
def search_documents(
    q: str = Query(..., min_length=1, max_length=200),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    safe_query = _escape_fts5(q)

    # FTS5 search with snippet
    sql = text("""
        SELECT d.id, d.title, d.file_type, d.status, d.created_at,
               snippet(documents_fts, 1, '...', '...', '...', 64) as snippet
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.rowid
        WHERE documents_fts MATCH :query
          AND d.user_id = :user_id
        ORDER BY rank
        LIMIT :limit OFFSET :offset
    """)

    result = db.execute(sql, {
        "query": safe_query,
        "user_id": current_user.id,
        "limit": limit,
        "offset": offset,
    })
    rows = result.fetchall()

    # Count total
    count_sql = text("""
        SELECT COUNT(*)
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.rowid
        WHERE documents_fts MATCH :query
          AND d.user_id = :user_id
    """)
    total = db.execute(count_sql, {"query": safe_query, "user_id": current_user.id}).scalar()

    items = []
    for row in rows:
        created = row[4]
        if created and not isinstance(created, str):
            created = created.isoformat()
        items.append({
            "id": row[0],
            "title": row[1],
            "file_type": row[2],
            "status": row[3],
            "snippet": row[5] or "",
            "created_at": created,
        })

    return ok(data={"items": items, "total": total, "page": page, "limit": limit})
