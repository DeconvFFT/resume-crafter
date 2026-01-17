"""File storage service for document uploads."""

import logging
import os
import shutil
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

import aiofiles
import aiofiles.os

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FileStorage:
    """Local file storage for uploaded documents."""

    def __init__(self, base_path: str | Path | None = None):
        """Initialize file storage.

        Args:
            base_path: Base directory for file storage. Defaults to ./uploads.
        """
        self._base_path = Path(base_path) if base_path else Path("./uploads")
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _get_user_path(self, user_id: UUID) -> Path:
        """Get the storage path for a user.

        Args:
            user_id: User's UUID.

        Returns:
            Path to user's upload directory.
        """
        user_path = self._base_path / str(user_id)
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path

    def _generate_filename(self, original_filename: str) -> str:
        """Generate a unique filename while preserving extension.

        Args:
            original_filename: Original uploaded filename.

        Returns:
            Unique filename with UUID prefix.
        """
        ext = Path(original_filename).suffix.lower()
        return f"{uuid4().hex}{ext}"

    async def save(
        self,
        user_id: UUID,
        file_content: BinaryIO,
        original_filename: str,
    ) -> tuple[Path, int]:
        """Save an uploaded file.

        Args:
            user_id: Owner user ID.
            file_content: File content as binary stream.
            original_filename: Original filename for extension.

        Returns:
            Tuple of (saved file path, file size in bytes).
        """
        user_path = self._get_user_path(user_id)
        filename = self._generate_filename(original_filename)
        file_path = user_path / filename

        # Read content and save
        content = file_content.read()
        file_size = len(content)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        logger.info(f"Saved file {file_path} ({file_size} bytes)")
        return file_path, file_size

    async def save_bytes(
        self,
        user_id: UUID,
        content: bytes,
        original_filename: str,
    ) -> tuple[Path, int]:
        """Save file content from bytes.

        Args:
            user_id: Owner user ID.
            content: File content as bytes.
            original_filename: Original filename for extension.

        Returns:
            Tuple of (saved file path, file size in bytes).
        """
        user_path = self._get_user_path(user_id)
        filename = self._generate_filename(original_filename)
        file_path = user_path / filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        logger.info(f"Saved file {file_path} ({len(content)} bytes)")
        return file_path, len(content)

    async def read(self, file_path: Path | str) -> bytes:
        """Read a file's contents.

        Args:
            file_path: Path to the file.

        Returns:
            File contents as bytes.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, file_path: Path | str) -> bool:
        """Delete a file.

        Args:
            file_path: Path to the file.

        Returns:
            True if deleted, False if file didn't exist.
        """
        path = Path(file_path)
        if path.exists():
            await aiofiles.os.remove(path)
            logger.info(f"Deleted file {file_path}")
            return True
        return False

    async def delete_user_files(self, user_id: UUID) -> int:
        """Delete all files for a user.

        Args:
            user_id: User's UUID.

        Returns:
            Number of files deleted.
        """
        user_path = self._get_user_path(user_id)
        if not user_path.exists():
            return 0

        count = 0
        for file_path in user_path.iterdir():
            if file_path.is_file():
                await aiofiles.os.remove(file_path)
                count += 1

        logger.info(f"Deleted {count} files for user {user_id}")
        return count

    def get_file_url(self, file_path: Path | str) -> str:
        """Get a URL path for a stored file.

        Args:
            file_path: Path to the file.

        Returns:
            URL path for the file.
        """
        # For local storage, return relative path
        # In production, this would return S3 URL or CDN URL
        return f"/files/{Path(file_path).relative_to(self._base_path)}"

    def exists(self, file_path: Path | str) -> bool:
        """Check if a file exists.

        Args:
            file_path: Path to the file.

        Returns:
            True if file exists.
        """
        return Path(file_path).exists()


# Singleton instance
_file_storage: FileStorage | None = None


def get_file_storage() -> FileStorage:
    """Get or create the file storage singleton."""
    global _file_storage
    if _file_storage is None:
        _file_storage = FileStorage()
    return _file_storage
