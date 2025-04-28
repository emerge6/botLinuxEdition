# utils/message_stats.py
import sqlite3
import time
from typing import Dict, List, Tuple

class MessageStats:
    def __init__(self):
        self.db_file = "message_stats.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    chat_id INTEGER,
                    user_id INTEGER,
                    username TEXT,
                    timestamp INTEGER
                )
            """)
            conn.commit()

    def add_message(self, chat_id: int, user_id: int, username: str) -> None:
        timestamp = int(time.time())
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (chat_id, user_id, username, timestamp) VALUES (?, ?, ?, ?)",
                (chat_id, user_id, username, timestamp)
            )
            conn.commit()

    def get_stats(self, chat_id: int, start_time: int, end_time: int) -> Dict[int, Tuple[str, int]]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, COUNT(*) as count
                FROM messages
                WHERE chat_id = ? AND timestamp BETWEEN ? AND ?
                GROUP BY user_id, username
            """, (chat_id, start_time, end_time))
            return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    def get_daily_stats(self, chat_id: int, day_start: int, day_end: int) -> Dict[int, Tuple[str, int]]:
        return self.get_stats(chat_id, day_start, day_end)
