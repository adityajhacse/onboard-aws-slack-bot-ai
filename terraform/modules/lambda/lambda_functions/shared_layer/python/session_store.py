from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any


SESSION_TTL = timedelta(minutes=60)

@dataclass
class ChatSession:
    key: str
    team_id: str
    channel_id: str
    user_id: str
    thread_ts: str
    candidate_intake: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, str]] = field(default_factory=list)
    approval_state: str = "draft"
    approval_token: str = ""
    preview: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.last_activity_at = datetime.now(timezone.utc)


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._lock = Lock()

    def get_or_create(
        self,
        *,
        team_id: str,
        channel_id: str,
        user_id: str,
        thread_ts: str,
    ) -> ChatSession:
        key = build_session_key(team_id, channel_id, user_id, thread_ts)
        with self._lock:
            self._expire_locked()
            session = self._sessions.get(key)
            if session is None:
                session = ChatSession(
                    key=key,
                    team_id=team_id,
                    channel_id=channel_id,
                    user_id=user_id,
                    thread_ts=thread_ts,
                )
                self._sessions[key] = session
            session.touch()
            return session

    def get(self, key: str) -> ChatSession | None:
        with self._lock:
            self._expire_locked()
            session = self._sessions.get(key)
            if session:
                session.touch()
            return session

    def exists(
        self,
        *,
        team_id: str,
        channel_id: str,
        user_id: str,
        thread_ts: str,
    ) -> bool:
        key = build_session_key(team_id, channel_id, user_id, thread_ts)
        with self._lock:
            self._expire_locked()
            return key in self._sessions

    def find_thread_session(
        self,
        *,
        channel_id: str,
        thread_ts: str,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> ChatSession | None:
        with self._lock:
            self._expire_locked()
            for session in self._sessions.values():
                if session.channel_id != channel_id or session.thread_ts != thread_ts:
                    continue
                if user_id and session.user_id != user_id:
                    continue
                if team_id and session.team_id and session.team_id != team_id:
                    continue
                session.touch()
                return session
            return None

    def save(self, session: ChatSession) -> None:
        with self._lock:
            session.touch()
            self._sessions[session.key] = session

    def reset(self, key: str) -> None:
        with self._lock:
            self._sessions.pop(key, None)

    def _expire_locked(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [
            key
            for key, session in self._sessions.items()
            if now - session.last_activity_at > SESSION_TTL
        ]
        for key in expired:
            self._sessions.pop(key, None)


def build_session_key(
    team_id: str,
    channel_id: str,
    user_id: str,
    thread_ts: str | None,
) -> str:
    safe_thread = thread_ts or "default"
    return f"{team_id or 'unknown-team'}:{channel_id}:{safe_thread}:{user_id}"
