from __future__ import annotations
import json
import os
import hashlib
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List, Tuple

@dataclass
class Account:
    username: str
    password_hash: str
    games: int = 0
    wins: int = 0

class AccountRepository:
    def __init__(self, path: str = "accounts.json"):
        self.path = path
        self._users: Dict[str, Account] = {}
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            self._users = {}
            self.save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            users = obj.get("users", {})
            self._users = {}
            for uname, rec in users.items():
                self._users[uname] = Account(
                    username=uname,
                    password_hash=rec.get("password_hash", ""),
                    games=int(rec.get("stats", {}).get("games", rec.get("games", 0))),
                    wins=int(rec.get("stats", {}).get("wins", rec.get("wins", 0))),
                )
        except Exception:
            # fallback to empty
            self._users = {}

    def save(self):
        data = {"users": {}}
        for uname, acc in self._users.items():
            data["users"][uname] = {
                "password_hash": acc.password_hash,
                "stats": {"games": acc.games, "wins": acc.wins},
            }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, username: str) -> Optional[Account]:
        return self._users.get(username)

    def exists(self, username: str) -> bool:
        return username in self._users

    def upsert(self, account: Account):
        self._users[account.username] = account
        self.save()

    def list_all(self) -> List[Account]:
        return list(self._users.values())

class AccountService:
    def __init__(self, repo: Optional[AccountRepository] = None):
        self.repo = repo or AccountRepository()
        self._current: Optional[str] = None

    @staticmethod
    def _hash_password(pw: str) -> str:
        return hashlib.sha256((pw or "").encode("utf-8")).hexdigest()

    def register(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        username = (username or "").strip()
        if not username:
            return False, "用户名不能为空"
        if self.repo.exists(username):
            return False, "用户名已存在"
        pw_hash = self._hash_password(password or "")
        acc = Account(username=username, password_hash=pw_hash, games=0, wins=0)
        self.repo.upsert(acc)
        return True, None

    def login(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        acc = self.repo.get((username or "").strip())
        if not acc:
            return False, "用户不存在"
        if acc.password_hash != self._hash_password(password or ""):
            return False, "密码错误"
        self._current = acc.username
        return True, None

    def logout(self):
        self._current = None

    def current_user(self) -> Optional[str]:
        return self._current

    def get_stats(self, username: str) -> Optional[Dict[str, int]]:
        acc = self.repo.get(username)
        if not acc:
            return None
        return {"games": acc.games, "wins": acc.wins}

    def update_stats(self, black_user: Optional[str], white_user: Optional[str], winner: Optional[str]):
        """
        winner: "BLACK" | "WHITE" | None
        仅对已登录的用户名写回统计；游客/AI 不计入。
        """
        def inc(u: Optional[str], win: bool):
            if not u:
                return
            acc = self.repo.get(u)
            if not acc:
                return
            acc.games += 1
            if win:
                acc.wins += 1
            self.repo.upsert(acc)

        if winner is None:
            # 平局：双方 games+1
            inc(black_user, False)
            inc(white_user, False)
        elif winner == "BLACK":
            inc(black_user, True)
            inc(white_user, False)
        elif winner == "WHITE":
            inc(black_user, False)
            inc(white_user, True)