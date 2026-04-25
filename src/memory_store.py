import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationTurn:
    turn_id: str
    role: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class SessionMemory:
    session_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    current_params: Optional[Dict[str, Any]] = None


class MemoryStore:
    def __init__(self):
        self._sessions: Dict[str, SessionMemory] = {}
        self._next_turn_id = 1

    def get_session(self, session_id: Optional[str] = None) -> SessionMemory:
        session_id = session_id or "default"
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionMemory(session_id=session_id)
        return self._sessions[session_id]

    def add_turn(self, session_id: str, role: str, text: str, metadata: Dict[str, Any]) -> ConversationTurn:
        session = self.get_session(session_id)
        turn_id = f"t_{self._next_turn_id:03d}"
        self._next_turn_id += 1
        turn = ConversationTurn(turn_id=turn_id, role=role, text=text, metadata=metadata)
        session.turns.append(turn)
        return turn

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return [token for token in text.split() if token]

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        a_tokens = set(MemoryStore._tokenize(a))
        b_tokens = set(MemoryStore._tokenize(b))
        if not a_tokens or not b_tokens:
            return 0.0
        intersection = a_tokens.intersection(b_tokens)
        union = a_tokens.union(b_tokens)
        return len(intersection) / len(union)

    def retrieve_similar_turns(self, session_id: str, query: str, k: int = 3) -> List[Dict[str, Any]]:
        session = self.get_session(session_id)
        scored = []
        for turn in session.turns:
            score = self._jaccard_similarity(query, turn.text)
            scored.append((score, turn))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, turn in scored[:k]:
            results.append({
                "turn_id": turn.turn_id,
                "role": turn.role,
                "text": turn.text,
                "metadata": turn.metadata,
                "similarity_score": round(score, 4),
            })
        return results
