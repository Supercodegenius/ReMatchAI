from __future__ import annotations

import argparse
import os
import random
import sys
import time
from statistics import mean

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from Myrepo.name_matching import match_names


FIRST_NAMES = [
    "john",
    "jane",
    "maria",
    "mohamed",
    "sarah",
    "david",
    "li",
    "ana",
    "chris",
    "alex",
    "pat",
    "sam",
    "nina",
    "oliver",
    "emma",
    "noah",
    "mia",
    "aaron",
    "zoe",
    "lucas",
]

LAST_NAMES = [
    "smith",
    "johnson",
    "williams",
    "brown",
    "jones",
    "miller",
    "davis",
    "garcia",
    "rodriguez",
    "wilson",
    "martinez",
    "anderson",
    "taylor",
    "thomas",
    "hernandez",
    "moore",
    "martin",
    "jackson",
    "thompson",
    "white",
]


def _random_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _mutate_name(name: str, rng: random.Random) -> str:
    first, last = name.split(" ", 1)
    roll = rng.random()

    if roll < 0.25 and len(first) > 3:
        first = first[:-1]
    elif roll < 0.50 and len(last) > 4:
        last = last[:-1]
    elif roll < 0.75:
        first = first.replace("ph", "f").replace("v", "w")
    else:
        first, last = last, first

    return f"{first} {last}"


def build_dataset(
    source_size: int,
    target_size: int,
    overlap_ratio: float,
    seed: int,
) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)

    target = [_random_name(rng) for _ in range(target_size)]
    overlap_count = min(source_size, int(source_size * overlap_ratio))

    source: list[str] = []
    for _ in range(overlap_count):
        source.append(_mutate_name(rng.choice(target), rng))

    while len(source) < source_size:
        source.append(_random_name(rng))

    return source, target


def run_once(
    method: str,
    source: list[str],
    target: list[str],
    threshold: int,
    lev_max_distance: int,
) -> tuple[float, int]:
    t0 = time.perf_counter()
    df = match_names(
        source,
        target,
        method=method,  # type: ignore[arg-type]
        fuzzy_threshold=threshold,
        lev_max_distance=lev_max_distance,
    )
    elapsed = time.perf_counter() - t0
    matched = int(df["is_match"].sum()) if "is_match" in df.columns else 0
    return elapsed, matched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark name matching performance.")
    parser.add_argument(
        "--method",
        choices=["fuzzy", "ai_advanced", "levenshtein", "jaro_winkler"],
        default="fuzzy",
        help="Matching method to benchmark.",
    )
    parser.add_argument("--source-size", type=int, default=20000)
    parser.add_argument("--target-size", type=int, default=50000)
    parser.add_argument("--overlap-ratio", type=float, default=0.75)
    parser.add_argument("--threshold", type=int, default=75)
    parser.add_argument("--lev-max-distance", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source, target = build_dataset(
        source_size=args.source_size,
        target_size=args.target_size,
        overlap_ratio=args.overlap_ratio,
        seed=args.seed,
    )

    timings: list[float] = []
    matches: list[int] = []
    for _ in range(args.repeats):
        elapsed, matched = run_once(
            method=args.method,
            source=source,
            target=target,
            threshold=args.threshold,
            lev_max_distance=args.lev_max_distance,
        )
        timings.append(elapsed)
        matches.append(matched)

    avg_seconds = mean(timings)
    rows_per_second = args.source_size / avg_seconds if avg_seconds else 0.0

    print("Benchmark configuration")
    print(f"  method: {args.method}")
    print(f"  source rows: {args.source_size:,}")
    print(f"  target rows: {args.target_size:,}")
    print(f"  overlap ratio: {args.overlap_ratio:.2f}")
    print(f"  repeats: {args.repeats}")
    print("")
    print("Results")
    print(f"  avg runtime: {avg_seconds:.3f}s")
    print(f"  rows/sec: {rows_per_second:,.1f}")
    print(f"  avg matched rows: {mean(matches):,.1f}")
    print(f"  run timings: {', '.join(f'{x:.3f}s' for x in timings)}")


if __name__ == "__main__":
    main()
