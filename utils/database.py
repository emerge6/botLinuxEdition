import os
import time

class Database:
    def __init__(self, chat_id):
        self.file = f"chat_{chat_id}.txt"
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        if not os.path.exists(self.file):
            with open(self.file, 'w') as f:
                f.write("bans:\n\nmutes:\n\nwarns:\n")
    
    def _read_section(self, section):
        with open(self.file, 'r') as f:
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
        return []

    def _write_section(self, section, data):
        with open(self.file, 'r') as f:
            content = f.read().split('\n\n')
        for i, block in enumerate(content):
            if block.startswith(section):
                lines = [f"{user_id} {until}" if until else f"{user_id}" for user_id, until in data]
                content[i] = f"{section}:\n" + "\n".join(lines)
                break
        with open(self.file, 'w') as f:
            f.write('\n\n'.join(content))

    def add_ban(self, user_id, duration=None):
        bans = self._read_section('bans')
        until = int(time.time() + duration) if duration else None
        bans = [(uid, u) for uid, u in bans if uid != user_id]
        bans.append((user_id, until))
        self._write_section('bans', bans)

    def remove_ban(self, user_id):
        bans = self._read_section('bans')
        bans = [(uid, u) for uid, u in bans if uid != user_id]
        self._write_section('bans', bans)

    def get_bans(self):
        return self._read_section('bans')

    def add_mute(self, user_id, duration=None):
        mutes = self._read_section('mutes')
        until = int(time.time() + duration) if duration else None
        mutes = [(uid, u) for uid, u in mutes if uid != user_id]
        mutes.append((user_id, until))
        self._write_section('mutes', mutes)

    def remove_mute(self, user_id):
        mutes = self._read_section('mutes')
        mutes = [(uid, u) for uid, u in mutes if uid != user_id]
        self._write_section('mutes', mutes)

    def get_mutes(self):
        return self._read_section('mutes')

    def add_warn(self, user_id):
        warns = self.get_warns()
        warns[user_id] = warns.get(user_id, 0) + 1
        with open(self.file, 'r') as f:
            content = f.read().split('\n\n')
        for i, block in enumerate(content):
            if block.startswith('warns'):
                content[i] = "warns:\n" + "\n".join(f"{k} {v}" for k, v in warns.items())
                break
        with open(self.file, 'w') as f:
            f.write('\n\n'.join(content))
        return warns[user_id]

    def remove_warn(self, user_id):
        warns = self.get_warns()
        if user_id in warns:
            warns[user_id] = max(0, warns[user_id] - 1)
            if warns[user_id] == 0:
                del warns[user_id]
            with open(self.file, 'r') as f:
                content = f.read().split('\n\n')
            for i, block in enumerate(content):
                if block.startswith('warns'):
                    content[i] = "warns:\n" + "\n".join(f"{k} {v}" for k, v in warns.items())
                    break
            with open(self.file, 'w') as f:
                f.write('\n\n'.join(content))
        return warns.get(user_id, 0)

    def get_warns(self):
        warns = {}
        with open(self.file, 'r') as f:
            lines = f.read().split('\n\n')
            for block in lines:
                if block.startswith('warns'):
                    for line in block.split('\n')[1:]:
                        if line:
                            user_id, count = line.split()
                            warns[int(user_id)] = int(count)
        return warns
