"""
Flattens elevation .hgt files from subdirectories into the parent directory.

Before: elevation_data/N40/N40W080.hgt
After:  elevation_data/N40W080.hgt
"""

import shutil
from pathlib import Path

from wayfinder.config.paths import ELEVATION_DIR


def flatten_elevation(elevation_dir: Path = ELEVATION_DIR) -> None:
    hgt_files = [f for f in elevation_dir.rglob("*.hgt") if f.parent != elevation_dir]
    if not hgt_files:
        print("Elevation tiles already flat, nothing to do")
        return

    for f in hgt_files:
        dest = elevation_dir / f.name
        if dest.exists():
            print(f"  Skipping {f.name} — already exists in parent")
        else:
            print(f"  Moving {f.relative_to(elevation_dir)} → {f.name}")
            shutil.move(str(f), str(dest))

    # Remove empty subdirectories
    for d in sorted(elevation_dir.iterdir(), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
                print(f"  Removed empty directory {d.name}")
            except OSError:
                print(f"  Could not remove {d.name} — not empty")

    print(f"Done — {len(hgt_files)} files flattened")


if __name__ == "__main__":
    flatten_elevation()