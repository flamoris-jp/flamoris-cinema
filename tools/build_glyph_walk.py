"""Prepare the fixed three-second seven-stroke Glyph walk as a new v3 take."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from flamoris_cinema.glyph_walk import walk_take
from flamoris_cinema.io import read_json,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,default=Path(__file__).resolve().parents[1]/'examples/red_glyph.take.json')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:write_json(args.out,walk_take(read_json(args.stage)))
    except (ValueError,OSError) as exc:parser.error(str(exc))


if __name__=='__main__':main()
