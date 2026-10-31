"""blender -b --python-exit-code 1 --python blender/import_scene.py -- scene.json animation.json output.blend"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from flamoris_cinema.blender_bridge import import_main, script_args

if __name__ == "__main__":
    import_main(script_args())
