"""blender -b input.blend --python-exit-code 1 --python blender/export_scene.py -- edited.take.json"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from flamoris_cinema.blender_bridge import export_main, script_args

if __name__ == "__main__":
    export_main(script_args())
