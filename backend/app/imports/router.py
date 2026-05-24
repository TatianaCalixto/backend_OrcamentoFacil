"""Rotas /imports (Sprint 9). Upload de CSV com criacao em batch."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database.session import get_db
from app.imports.schemas import ImportResult
from app.imports.service import CsvImportOwnershipError, CsvImportService
from app.users.models import User

router = APIRouter(prefix="/imports", tags=["imports"])

# limite generoso: 2 MB (extratos bancarios costumam ser pequenos)
MAX_CSV_BYTES = 2 * 1024 * 1024

_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",  # alguns sistemas exportam csv com este mime
    "text/plain",
    "application/octet-stream",  # cliente pode enviar sem mime correto
}


@router.post("/csv", response_model=ImportResult)
async def import_csv(
    account_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImportResult:
    # validacao de extensao e MIME
    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="arquivo precisa ter extensao .csv",
        )
    if file.content_type and file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"content-type nao suportado: {file.content_type}",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="arquivo vazio",
        )
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"arquivo excede {MAX_CSV_BYTES} bytes",
        )

    try:
        return CsvImportService(db).import_csv(current_user.id, account_id, content)
    except CsvImportOwnershipError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
