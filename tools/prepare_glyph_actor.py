"""Snapshot one validated Glyph occurrence and prepare a static Cinema stage."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from flamoris_cinema.glyph_prepare import prepare_asset, stage_take
from flamoris_cinema.io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--occurrence', required=True)
    parser.add_argument('--out', type=Path, required=True, help='new self-contained take JSON')
    parser.add_argument('--metres-per-unit', type=float, default=0.003)
    parser.add_argument('--depth', type=float, default=0.12)
    args = parser.parse_args()
    try:
        asset, color = prepare_asset(args.bundle, args.occurrence)
        write_json(args.out, stage_take(asset, color, metres_per_unit=args.metres_per_unit, depth=args.depth))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
