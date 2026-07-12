"""Plan/apply gate decks (Team Paper Lite "计划闸").

A gate decision is split into two physically separate phases, like
`terraform plan` / `terraform apply`:

- PLAN: the agent proposes a *deck of cards* (text only, no execution, no token
  burn on the real work). Each card is a unit the human can KEEP, DROP, or edit.
- APPLY: only after the human edits and commits the deck (under an approver git
  identity) does the loop execute.

Two invariants:
- Cards sourced from the anchor / intake are `locked` — the planner may not drop
  them (they encode the frozen 4-component anchor).
- Apply requires at least one kept card and rejects any dropped locked card.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Card:
    id: str
    title: str
    body: str = ""
    status: str = "keep"      # keep | drop
    source: str = "agent"     # agent | intake
    locked: bool = False

    def to_dict(self) -> dict:
        return {"id": self.id, "source": self.source, "locked": self.locked,
                "status": self.status, "title": self.title, "body": self.body}


@dataclass
class Deck:
    gate: str
    stage: str
    cards: list[Card] = field(default_factory=list)
    authority_evidence: str = "signed_commit"


def deck_path(project_root: Path, gate: str) -> Path:
    slug = (gate or "gate").strip().split()[0]
    slug = "".join(c for c in slug if c.isalnum() or c in "-_") or "gate"
    return project_root / "decisions" / "plans" / f"{slug}.md"


def write_deck(project_root: Path, deck: Deck) -> Path:
    path = deck_path(project_root, deck.gate)
    path.parent.mkdir(parents=True, exist_ok=True)
    front = {"gate": deck.gate, "stage": deck.stage,
             "authority_evidence": deck.authority_evidence,
             "cards": [c.to_dict() for c in deck.cards]}
    lines = ["---", yaml.safe_dump(front, sort_keys=False).strip(), "---", ""]
    lines += [f"# Plan deck: {deck.gate}", "",
              "Proposal only — nothing has executed. Edit the cards above, then (as an",
              "approver) commit this file and run `aeros gate apply`.",
              "",
              "- Keep a card: leave `status: keep`. Drop it: set `status: drop`.",
              "- Edit a card: change its `title`/`body` directly.",
              "- Cards with `locked: true` come from the anchor/intake and may NOT be dropped.",
              "",
              "## Cards", ""]
    for c in deck.cards:
        lock = " 🔒" if c.locked else ""
        lines.append(f"### [{c.status.upper()}] {c.id}: {c.title}{lock}  ({c.source})")
        if c.body:
            lines.append("")
            lines.append(c.body)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def parse_deck(path: Path) -> Deck:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    data = yaml.safe_load(m.group(1)) if m else {}
    data = data if isinstance(data, dict) else {}
    cards = []
    for raw in data.get("cards", []) or []:
        if not isinstance(raw, dict):
            continue
        cards.append(Card(
            id=str(raw.get("id", "?")),
            title=str(raw.get("title", "")),
            body=str(raw.get("body", "")),
            status=str(raw.get("status", "keep")).strip().lower(),
            source=str(raw.get("source", "agent")).strip().lower(),
            locked=bool(raw.get("locked", False)),
        ))
    return Deck(
        gate=str(data.get("gate", "")),
        stage=str(data.get("stage", "")),
        cards=cards,
        authority_evidence=str(data.get("authority_evidence") or "local_authorship").strip(),
    )


def validate_applied(deck: Deck) -> list[str]:
    """Return a list of violations; empty means the deck is safe to apply."""
    problems: list[str] = []
    dropped_locked = [c.id for c in deck.cards if c.locked and c.status == "drop"]
    for cid in dropped_locked:
        problems.append(f"locked card {cid} was dropped — anchor/intake cards may not be dropped")
    if not any(c.status == "keep" for c in deck.cards):
        problems.append("no cards kept — an applied plan must keep at least one card")
    for c in deck.cards:
        if c.status not in {"keep", "drop"}:
            problems.append(f"card {c.id} has invalid status {c.status!r} (use keep|drop)")
    return problems


def kept_cards(deck: Deck) -> list[Card]:
    return [c for c in deck.cards if c.status == "keep"]
