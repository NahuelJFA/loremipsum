import random
from typing import Optional


def run_raffle(
    comments: list[dict],
    mention_filter: Optional[str] = None,
    exclude_duplicates: bool = True,
    num_winners: int = 1,
) -> list[dict]:
    pool = list(comments)

    if mention_filter:
        handle = mention_filter.lstrip("@").lower()
        pool = [c for c in pool if handle in [m.lower() for m in c.get("mentions", [])]]

    if exclude_duplicates:
        seen: set[str] = set()
        unique: list[dict] = []
        for c in pool:
            uname = c.get("username", "").lower()
            if uname not in seen:
                seen.add(uname)
                unique.append(c)
        pool = unique

    if not pool:
        return []

    num_winners = min(num_winners, len(pool))
    winners = random.sample(pool, num_winners)

    return [{"username": w.get("username"), "comment": w} for w in winners]
