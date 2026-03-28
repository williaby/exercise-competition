"""Rotating jokes for the leaderboard page.

A curated collection of brotherly roasts targeting Nick, the youngest Williams brother.
A random joke is selected on each page load.
"""

from __future__ import annotations

import random

NICK_JOKES: list[str] = [
    # === Youngest child jokes (the bulk) ===
    "Nick's baby photos are still in the 'Recent' folder.",
    "Nick didn't pick his own outfit until he was 27.",
    "Being the youngest means Nick's entire childhood was a hand-me-down experience.",
    "Nick still gets carded — not for alcohol, for the kids' menu.",
    "Nick's first word was 'me too' because that's all youngest kids ever say.",
    "Nick thinks 'hand-me-down' is a clothing brand.",
    "As the youngest, Nick's curfew was whenever his brothers got tired of babysitting.",
    "Nick's childhood nickname was 'Also Coming' as in 'we're bringing the boys — and Nick is also coming.'",
    "Nick learned to run fast. He had to — three older brothers, one bathroom.",
    "The youngest child doesn't have trust issues. They have 'my brothers told me the ice cream truck plays music when it's out of ice cream' issues.",
    "Nick's entire personality was formed by losing arguments to people who could bench press him.",
    "Being the youngest means your first bike was already on its fourth owner.",
    "Nick didn't get a new anything until he had his own paycheck.",
    "As the baby of the family, Nick's toughest workout is still trying to get a word in at dinner.",
    "Nick peaked at age 5 when he could still play the 'I'm telling Mom' card.",
    "The youngest child's superpower is weaponized tattling. Nick went pro.",
    "Nick's childhood was basically a spectator sport — watching his brothers do everything first.",
    "Nick still flinches when someone says 'stop copying me.'",
    "Three older brothers means Nick's pain tolerance is elite. His dignity, not so much.",
    "Nick's origin story is just his parents saying 'might as well try one more time.'",
    "Youngest child privilege is real — Nick got away with everything because his parents were too tired to care.",
    "Nick was raised by three brothers and it shows.",
    "The only thing Nick got first was the blame.",
    "Nick's favorite childhood game was 'Why are you hitting yourself?'",
    # === Endocrinologist jokes ===
    "Nick chose endocrinology because he relates to hormones — always overreacting.",
    "Nick can regulate your thyroid but can't regulate his exercise schedule.",
    "Imagine spending a decade in medical training just to tell people their thyroid is slow. Nick relates.",
    "Nick treats hormone imbalances all day, then goes home and eats ice cream for dinner like a balanced adult.",
    "Nick knows everything about metabolism. Hasn't helped his leaderboard position one bit.",
    # === PA not a real doctor jokes ===
    "Nick introduces himself as 'almost a doctor' and hopes nobody asks follow-up questions.",
    "Nick is a PA, which stands for 'Practically Actual... no wait, not quite.'",
    "Nick went to medical school adjacent. Like how a garage is house adjacent.",
    "Somewhere between a nurse and a doctor, there's Nick, filling out paperwork.",
    "Nick can prescribe medication but not respect. That requires an MD.",
]


def get_random_joke() -> str:
    """Return a random joke from the collection."""
    return random.choice(NICK_JOKES)  # noqa: S311
