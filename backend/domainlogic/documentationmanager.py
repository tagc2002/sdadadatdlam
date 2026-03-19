from datetime import datetime
import mimetypes
from pathlib import Path
from typing import Self
from sqlalchemy.orm import Session

from database.database import Documentation
from dataobjects.enums import DocType

class DocumentationManager():
    def storeFile(self: Self, name: str, type: DocType, isSeclo: bool, db: Session, importedDate: datetime | None = None, path: Path | None = None, bytes: bytes | None = None, mime: str | None = None) -> Documentation:
        if not (path or bytes): raise ValueError("Trying to save a document without any files")
        if not importedDate: importedDate=datetime.now()
        if path:
            if not mime: mime = mimetypes.guess_file_type(path)[0]
            with open(path, "rb") as file:
                bytes = file.read()
        documentation = Documentation(docName=name, docType=type, importedDate=importedDate, importedFromSeclo=isSeclo, file=bytes, mimeType=mime)
        db.add(documentation)
        return documentation