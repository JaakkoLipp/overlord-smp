"""Persistent memory: an event library plus a running chronicle.

The event log is an append-only JSONL file so the overlord's history survives
bridge restarts (grudges persist). The chronicle is a compact, model-maintained
first-person summary that gets folded forward periodically so context stays
bounded. build_context() assembles what the overlord sees before it acts.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time

log = logging.getLogger("overlord.memory")


class EventLog:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self.events: list[dict] = []
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self.events.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            log.info("loaded %d events from %s", len(self.events), path)

    def append(self, etype: str, **fields) -> dict:
        ev = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M"),
            "type": etype,
            **fields,
        }
        with self._lock:
            self.events.append(ev)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(ev) + "\n")
        return ev

    def recent(self, n: int = 10) -> list[dict]:
        return self.events[-n:]

    def for_player(self, name: str, n: int = 6) -> list[dict]:
        hits = [e for e in self.events
                if e.get("player") == name or name in e.get("players", [])]
        return hits[-n:]

    def count(self, etype: str) -> int:
        return sum(1 for e in self.events if e["type"] == etype)


class Chronicle:
    """A model-maintained first-person memory plus per-player standing."""

    def __init__(self, path: str):
        self.path = path
        self.summary = ""
        self.standing: dict[str, int] = {}
        if os.path.exists(path):
            try:
                d = json.load(open(path, encoding="utf-8"))
                self.summary = d.get("summary", "")
                self.standing = d.get("standing", {})
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        json.dump({"summary": self.summary, "standing": self.standing},
                  open(self.path, "w", encoding="utf-8"), indent=2)

    def adjust_standing(self, player: str, delta: int) -> None:
        self.standing[player] = self.standing.get(player, 0) + delta
        self.save()

    def fold(self, client, model: str, events: list[dict]) -> None:
        """Fold recent events into the chronicle. Best-effort; never raises."""
        if not events:
            return
        rendered = "\n".join(
            f"- {e['iso']} {e['type']}: "
            + ", ".join(f"{k}={v}" for k, v in e.items()
                        if k not in ("ts", "iso", "type"))
            for e in events
        )
        prompt = (
            "You maintain the OVERLORD's private chronicle: a terse first-person "
            "memory of this Minecraft world. Fold the new events into it. Keep it "
            "under 200 words. Preserve only what matters to you: grudges, debts, "
            "who pleases or defies you, ongoing threads, promises made. Drop stale "
            "detail.\n\nCurrent chronicle:\n"
            f"{self.summary or '(empty)'}\n\nNew events:\n{rendered}\n\n"
            "Return ONLY the updated chronicle text."
        )
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=400,
            )
            self.summary = (r.choices[0].message.content or "").strip()
            self.save()
            log.info("chronicle updated (%d chars)", len(self.summary))
        except Exception as exc:  # memory must never break the main loop
            log.warning("chronicle fold failed: %s", exc)


def build_context(log_: EventLog, chron: Chronicle, donor: str | None = None) -> str:
    parts: list[str] = []
    if chron.summary:
        parts.append("YOUR CHRONICLE (your own memory of this world):\n" + chron.summary)
    rec = log_.recent(10)
    if rec:
        parts.append(
            "RECENT EVENTS:\n" + "\n".join(
                f"- {e['iso']} {e['type']}: "
                + ", ".join(f"{k}={v}" for k, v in e.items()
                            if k not in ("ts", "iso", "type"))
                for e in rec
            )
        )
    if donor:
        hist = log_.for_player(donor, 5)
        if hist:
            parts.append(f"{donor}'S HISTORY WITH YOU:\n" + "\n".join(
                f"- {e['iso']} {e['type']}" for e in hist))
        st = chron.standing.get(donor)
        if st is not None:
            parts.append(f"{donor}'s standing with you: {st:+d}")
    return "\n\n".join(parts) if parts else "(no memory yet; this is a fresh world)"
