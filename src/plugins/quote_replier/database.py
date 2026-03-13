import os
import threading
import sqlite3
from dataclasses import dataclass
from venv import logger

from .config import Config


@dataclass
class QuoteRecord:
    id: int
    group_id: int
    user_id: int
    message_id: int
    image_path: str
    text: str
    created_time: str


class QuoteDatabase:
    def __init__(self, database_path: str, image_path: str):
        if not database_path or not image_path:
            raise ValueError("Database path and image path must be provided.")
        self.database_path = database_path
        self.image_path = image_path
        self._lock = threading.Lock()

    def init_database(self):
        with self._lock:
            conn = sqlite3.connect(self.database_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quote_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_quote_images_group_created
                ON quote_images (group_id, created_time DESC)
                """
            )
            conn.commit()

    def add_quote(self, group_id: int, user_id: int, message_id: int, image_path: str, text: str):
        with self._lock:
            conn = sqlite3.connect(self.database_path)
            conn.execute(
                """
                INSERT INTO quote_images (group_id, user_id, message_id, image_path, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (group_id, user_id, message_id, image_path, text),
            )
            conn.commit()

    def count_by_group(self, group_id: int):
        with self._lock:
            conn = sqlite3.connect(self.database_path)
            count = conn.execute(
                """
                SELECT COUNT(*) FROM quote_images WHERE group_id = ?
                """,
                (group_id,),
            ).fetchone()[0]
            return count

    def select_by_group(self, group_id: int):
        with self._lock:
            conn = sqlite3.connect(self.database_path)
            records = conn.execute(
                """
                SELECT id, group_id, user_id, message_id, image_path, text, created_time
                FROM quote_images
                WHERE group_id = ?
                ORDER BY created_time DESC
                """,
                (group_id,),
            ).fetchall()
            return [QuoteRecord(*record) for record in records]

    def select_by_text(self, group_id: int, search_text: str):
        with self._lock:
            conn = sqlite3.connect(self.database_path)
            records = conn.execute(
                """
                SELECT id, group_id, user_id, message_id, image_path, text, created_time
                FROM quote_images
                WHERE group_id = ? AND text LIKE ?
                ORDER BY created_time DESC
                """,
                (group_id, f"%{search_text}%"),
            ).fetchall()
            return [QuoteRecord(*record) for record in records]

    def list_page_by_group(self, group_id: int, page: int, page_size: int):
        with self._lock:
            conn = sqlite3.connect(self.database_path)
            records = conn.execute(
                """
                SELECT id, group_id, user_id, message_id, image_path, text, created_time
                FROM quote_images
                WHERE group_id = ?
                ORDER BY created_time DESC
                LIMIT ? OFFSET ?
                """,
                (group_id, page_size, (page - 1) * page_size),
            ).fetchall()
            return [QuoteRecord(*record) for record in records]

    def delete_quote(self, quote_id: int):
        with self._lock:
            conn = sqlite3.connect(self.database_path)
            # 先得到图片路径以便删除文件
            image_paths = conn.execute(
                """
                SELECT image_path FROM quote_images WHERE id = ?
                """,
                (quote_id,),
            ).fetchall()
            if image_paths:
                try:
                    for image_path in image_paths:
                        os.remove(image_path[0])
                except Exception as e:
                    logger.error(f"Failed to delete image file: {image_paths}, error: {e}")
            conn.execute(
                """
                DELETE FROM quote_images WHERE id = ?
                """,
                (quote_id,),
            )
            conn.commit()
