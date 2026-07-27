#!/usr/bin/env python3
"""Validate the CT input before segmentation.

The repository copy may contain a Git LFS pointer rather than the TIFF
payload. This script refuses to generate analysis outputs in that case.
"""

from pathlib import Path
import argparse


def is_lfs_pointer(path: Path) -> bool:
    try:
        head = path.read_bytes()[:256]
    except OSError:
        return False
    return head.startswith(b"version https://git-lfs.github.com/spec/v1\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    if not args.input.exists():
        print(f"Input not found: {args.input}")
        return 2
    if is_lfs_pointer(args.input):
        print("Input is a Git LFS pointer; segmentation requires the hydrated TIFF payload.")
        return 3
    print("Input is not recognized as a Git LFS pointer; segmentation workflow may proceed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
