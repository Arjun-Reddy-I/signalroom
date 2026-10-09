import hashlib
import os
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequestException


class StorageProvider(ABC):
    @abstractmethod
    async def save_file(self, file: UploadFile, key_prefix: str = "uploads") -> tuple[str, str, int, str]:
        """Saves file payload and returns (storage_key, filename, size_bytes, sha256_checksum)"""
        pass

    @abstractmethod
    async def get_file_path(self, storage_key: str) -> Path:
        """Returns local path or temporary path to file"""
        pass

    @abstractmethod
    async def delete_file(self, storage_key: str) -> bool:
        """Deletes file from storage"""
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = settings.UPLOAD_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file: UploadFile, key_prefix: str = "uploads") -> tuple[str, str, int, str]:
        filename = file.filename or "uploaded_media"
        # Sanitize filename against path traversal
        clean_filename = Path(filename).name
        ext = Path(clean_filename).suffix.lower()

        allowed_extensions = {".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".mov", ".flac"}
        if ext not in allowed_extensions:
            raise BadRequestException(message=f"File extension '{ext}' not allowed. Allowed: {sorted(allowed_extensions)}")

        sub_dir = self.base_dir / key_prefix
        sub_dir.mkdir(parents=True, exist_ok=True)

        random_prefix = os.urandom(8).hex()
        safe_key = f"{key_prefix}/{random_prefix}_{clean_filename}"
        dest_path = self.base_dir / safe_key

        sha256_hash = hashlib.sha256()
        size_bytes = 0

        with dest_path.open("wb") as f:
            while chunk := await file.read(8192):
                size_bytes += len(chunk)
                if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                    dest_path.unlink(missing_ok=True)
                    raise BadRequestException(message=f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB")
                sha256_hash.update(chunk)
                f.write(chunk)

        checksum = sha256_hash.hexdigest()
        return safe_key, clean_filename, size_bytes, checksum

    async def get_file_path(self, storage_key: str) -> Path:
        target_path = (self.base_dir / storage_key).resolve()
        # Path traversal guard
        if not str(target_path).startswith(str(self.base_dir.resolve())):
            raise BadRequestException(message="Invalid storage path")
        if not target_path.exists():
            raise BadRequestException(message="Storage file not found")
        return target_path

    async def delete_file(self, storage_key: str) -> bool:
        try:
            target_path = await self.get_file_path(storage_key)
            target_path.unlink(missing_ok=True)
            return True
        except Exception:
            return False


def get_storage_provider() -> StorageProvider:
    return LocalStorageProvider()
