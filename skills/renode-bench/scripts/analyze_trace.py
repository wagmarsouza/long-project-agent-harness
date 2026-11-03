#!/usr/bin/env python3
"""Summarize a Renode PC trace containing one hexadecimal address per line."""
import argparse
from collections import Counter
from pathlib import Path
import sys


def load_pcs(path):
    pcs = []
    for number, raw in enumerate(Path(path).read_text(encoding="utf-8", errors="strict").splitlines(), 1):
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        try:
            pcs.append(int(value, 16))
        except ValueError as error:
            raise ValueError(f"line {number}: expected one hexadecimal PC, got {value!r}") from error
    return pcs


def collapse_blocks(pcs, jump_threshold=8):
    blocks = []
    start = previous = None
    count = 0
    for pc in pcs:
        if previous is None or abs(pc - previous) > jump_threshold:
            if start is not None:
                blocks.append((start, previous, count))
            start, count = pc, 1
        else:
            count += 1
        previous = pc
    if start is not None:
        blocks.append((start, previous, count))
    return blocks


def summarize(pcs, top=20, blocks=40, tail_blocks=15, jump_threshold=8):
    result = {"total_entries": len(pcs), "unique_pcs": len(set(pcs))}
    if not pcs:
        return result
    counts = Counter(pcs)
    collapsed = collapse_blocks(pcs, jump_threshold)
    result.update({
        "min_pc": min(pcs), "max_pc": max(pcs),
        "top": counts.most_common(top), "total_blocks": len(collapsed),
        "first_blocks": collapsed[:blocks], "last_blocks": collapsed[-tail_blocks:],
        "jump_threshold": jump_threshold,
    })
    return result


def print_summary(result):
    print(f"total trace entries: {result['total_entries']}")
    print(f"unique PC values: {result['unique_pcs']}")
    if not result["total_entries"]:
        print("(empty trace; no execution behavior established)")
        return
    print(f"address range: 0x{result['min_pc']:x} - 0x{result['max_pc']:x}")
    print("most-visited PCs:")
    for pc, count in result["top"]:
        print(f"  0x{pc:08x}: {count}")
    print(f"total jump-delimited blocks: {result['total_blocks']}")
    print("first blocks:")
    for index, (start, end, count) in enumerate(result["first_blocks"]):
        print(f"  [{index:4d}] 0x{start:08x} .. 0x{end:08x} (n={count})")
    print("last blocks:")
    for start, end, count in result["last_blocks"]:
        print(f"  0x{start:08x} .. 0x{end:08x} (n={count})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_path")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--blocks", type=int, default=40)
    parser.add_argument("--tail-blocks", type=int, default=15)
    parser.add_argument("--jump-threshold", type=int, default=8)
    args = parser.parse_args()
    if min(args.top, args.blocks, args.tail_blocks, args.jump_threshold) < 0:
        parser.error("numeric limits must be non-negative")
    try:
        result = summarize(load_pcs(args.log_path), args.top, args.blocks, args.tail_blocks,
                           args.jump_threshold)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"trace error: {error}", file=sys.stderr)
        return 2
    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
