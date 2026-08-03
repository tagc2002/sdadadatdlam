from datetime import datetime
from typing import Optional, Self
import mimetypes
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from database.definitions import Documentation
from dataobjects.enums import DocType


def store_file(
    name: str,
    doctype: DocType,
    is_seclo: bool,
    db: AsyncSession,
    imported_date: Optional[datetime] = datetime.now(),
    path: Optional[Path] = None,
    filebytes: Optional[bytes] = None,
    mime: Optional[str] = None,
) -> Documentation:
    if not (path or filebytes):
        raise ValueError("Trying to save a document without any files")
    if path:
        if not mime:
            mime = mimetypes.guess_file_type(path)[0]
        with open(path, "rb") as file:
            filebytes = file.read()
    documentation = Documentation(
        docName=name,
        docType=doctype,
        importedDate=imported_date,
        importedFromSeclo=is_seclo,
        file=filebytes,
        mimeType=mime,
    )
    db.add(documentation)
    return documentation
