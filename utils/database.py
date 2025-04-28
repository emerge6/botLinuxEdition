import os
import time
import fcntl
from typing import Dict, List, Tuple, Optional

class Database:
    def __init__(self, chat_id: int):
        self.file = f"chat_{chat_id}.txt"
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        if not os.path.exists(self.file):
            with open(self.file, 'w') as f:
                f.write("bans:\n\nmutes:\n\nwarns:\n")
    
    def _acquire_lock(self, file) -> None:
        try:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        except IOError as e:
            raise IOError(f"Failed to acquire lock on {self.file}: {str(e)}")

    def _release_lock(self, file) -> None:
        try:
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)
        except IOError as e:
            raise IOError(f"Failed to release lock on {self.file}: {str(e)}")

    def _read_section(self, section: str) -> List[Tuple[int, Optional[int]]]:
        with open(self.file, 'r') as f:
            self._acquire_lock(f)
            try:
                lines = f.read().split('\n\n')
                for block in lines:
                    if block.startswith(section):
                        result = []
                        for line in block.split('\n')[1:]:
                            if line:
                                parts = line.split()
                                user_id = int(parts[0])
                                until = int(parts[1]) if len(parts) > 1 and parts[1] else None
                                result.append((user_id, until))
                        return result
            finally:
                self._release_lock(f)
        return []

    def _write_section(self, section: str, data: List[Tuple[int, Optional[int]]]) -> None:
        with open(self.file, 'r') as f:
            self._acquire_lock(f)
            try:
                content = f.read().split('\n\n')
            finally:
                self._release_lock(f)
        
        for i, block in enumerate(content):
            if block.startswith(section):
                lines = [f"{user_id} {until}" if until else f"{user_id}" for user_id, until in data]
                content[i] = f"{section}:\n" + "\n".join(lines)
                break
        
        with open(self.file, 'w') as f:
            self._acquire_lock(f)
            try:
                f.write('\n\n'.join(content))
            finally:
                self._release_lock(f)

    def _read_warns(self) -> Dict[int, Tuple[int, Optional[int]]]:
        warns = {}
        with open(self.file, 'r') as f:
            self._acquire_lock(f)
            try:
                lines = f.read().split('\n\n')
                for block in lines:
                    if block.startswith('warns'):
                        for line in block.split('\n')[1:]:
                            if line:
                                parts = line.split()
                                user_id = int(parts[0])
                                count = int(parts[1]) if len(parts) > 1 else 1
                                until = int(parts[2]) if len(parts) > 2 and parts[2] else None
                                warns[user_id] = (count, until)
            finally:
                self._release_lock(f)
        return warns

    def _write_warns(self, warns: Dict[int, Tuple[int, Optional[int]]]) -> None:
        with open(self.file, 'r') as f:
            self._acquire_lock(f)
            try:
                content = f.read().split('\n\n')
            finally:
                self._release_lock(f)
        
        for i, block in enumerate(content):
            if block.startswith('warns'):
                lines = []
                for user_id, (count, until) in warns.items():
                    if until:
                        lines.append(f"{user_id} {count} {until}")
                    else:
                        lines.append(f"{user_id} {count}")
                content[i] = "warns:\n" + "\n".join(lines)
                break
        
        with open(self.file, 'w') as f:
            self._acquire_lock(f)
            try:
                f.write('\n\n'.join(content))
            finally:
                self._release_lock(f)

    def add_ban(self, user_id: int, duration: Optional[int] = None) -> None:
        bans = self._read_section('bans')
        until = int(time.time() + duration) if duration else None
        bans = [(uid, u) for uid, u in bans if uid != user_id]
        bans.append((user_id, until))
        self._write_section('bans', bans)

    def remove_ban(self, user_id: int) -> None:
        bans = self._read_section('bans')
        bans = [(uid, u) for uid, u in bans if uid != user_id]
        self._write_section('bans', bans)

    def get_bans(self) -> List[Tuple[int, Optional[int]]]:
        return self._read_section('bans')

    def add_mute(self, user_id: int, duration: Optional[int] = None) -> None:
        mutes = self._read_section('mutes')
        until = int(time.time() + duration) if duration else None
        mutes = [(uid, u) for uid, u in mutes if uid != user_id]
        mutes.append((user_id, until))
        self._write_section('mutes', mutes)

    def remove_mute(self, user_id: int) -> None:
        mutes = self._read_section('mutes')
        mutes = [(uid, u) for uid, u in mutes if uid != user_id]
        self._write_section('mutes', mutes)

    def get_mutes(self) -> List[Tuple[int, Optional[int]]]:
        return self._read_section('mutes')

    def add_warn(self, user_id: int, duration: Optional[int] = None) -> int:
        warns = self._read_warns()
        current_count, current_until = warns.get(user_id, (0, None))
        new_count = current_count + 1
        until = int(time.time() + duration) if duration else None
        warns[user_id] = (new_count, until)
        self._write_warns(warns)
        return new_count

    def remove_warn(self, user_id: int) -> int:
        warns = self._read_warns()
        current_count, current_until = warns.get(user_id, (0, None))
        new_count = max(0, current_count - 1)
        if new_count == 0:
            warns.pop(user_id, None)
        else:
            warns[user_id] = (new_count, current_until)
        self._write_warns(warns)
        return new_count

    def get_warns(self) -> Dict[int, int]:
        warns = self._read_warns()
        current_time = int(time.time())
        filtered_warns = {}
        for user_id, (count, until) in warns.items():
            if until and until < current_time:
                continue  
            filtered_warns[user_id] = count
        self._write_warns({uid: (count, warns[uid][1]) for uid, count in filtered_warns.items()})
        return filtered_warns

    def get_warns_with_details(self) -> Dict[int, Tuple[int, Optional[int]]]:
        warns = self._read_warns()
        current_time = int(time.time())
        filtered_warns = {}
        for user_id, (count, until) in warns.items():
            if until and until < current_time:
                continue
            filtered_warns[user_id] = (count, until)
        self._write_warns(filtered_warns)
        return filtered_warns
