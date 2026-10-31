"""Write one data-only Flamenco proposal; does not submit or execute a job."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from flamoris_cinema.flamenco import render_job
from flamoris_cinema.interchange import validate_take
from flamoris_cinema.io import read_json,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--take',type=Path,required=True)
    parser.add_argument('--shared-root',type=Path,required=True)
    parser.add_argument('--blend-file',type=Path,required=True)
    parser.add_argument('--render-output',type=Path,required=True)
    parser.add_argument('--scene-name',required=True)
    parser.add_argument('--name',required=True)
    parser.add_argument('--type-etag',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:
        take=validate_take(read_json(args.take))
        write_json(args.out,render_job(take['scene'],shared_root=args.shared_root,blend_file=args.blend_file,
                   output_root=args.render_output,scene_name=args.scene_name,name=args.name,type_etag=args.type_etag))
    except (ValueError,OSError) as exc:parser.error(str(exc))


if __name__=='__main__':main()
