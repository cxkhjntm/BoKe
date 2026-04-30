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


def _sanitize_fts5_query(query: str) -> str:
    """Sanitize user input for FTS5 MATCH query.

    Strategy: strip control characters, then wrap in double quotes for phrase search.
    This prevents FTS5 operator injection (AND, OR, NOT, NEAR, *, -, etc.)
    while still allowing the user to search for literal text.

    FTS5 special chars inside quoted strings are treated as literals,
    except for double-quotes which must be escaped as "".
    """
    # Strip null bytes and control characters (except whitespace)
    cleaned = "".join(ch for ch in query if ch in ("\t", "\n", "\r") or (ord(ch) >= 32))
    # Escape double-quotes for FTS5
    cleaned = cleaned.replace('"', '""')
    cleaned = cleaned.strip()
    if not cleaned:
        return '""'
    # Wrap in double quotes for phrase search (treats content as literal text)
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
    safe_query = _sanitize_fts5_query(q)

    # FTS5 search with snippet, count via window function to avoid duplicate MATCH
    sql = text("""
        SELECT id, title, file_type, status, created_at, snippet, total
        FROM (
            SELECT d.id, d.title, d.file_type, d.status, d.created_at,
                   snippet(documents_fts, 1, '...', '...', '...', 64) as snippet,
                   COUNT(*) OVER() as total
            FROM documents_fts
            JOIN documents d ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH :query
              AND d.user_id = :user_id
            ORDER BY rank
        )
        LIMIT :limit OFFSET :offset
    """)

    result = db.execute(sql, {
        "query": safe_query,
        "user_id": current_user.id,
        "limit": limit,
        "offset": offset,
    })
    rows = result.fetchall()

    total = rows[0][6] if rows else 0

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
