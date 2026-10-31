"""Data-only proposal for Flamenco's built-in simple-blender-render job.

No network, submission, retry, credentials, Worker control or service mutation.
The operator/controller checks the Manager's actual job-type etag and queue.
"""
from pathlib import Path
import sys
from .contracts import frame_count,identifier,validate_scene


def render_job(scene, *, shared_root, blend_file, output_root, scene_name, name,
               type_etag, chunk_size=24, platform=None):
    validate_scene(scene)
    identifier(name,'job name')
    if not isinstance(scene_name,str) or not 1<=len(scene_name)<=100 or any(ord(c)<32 for c in scene_name):
        raise ValueError('explicit native Blender scene name required')
    if not isinstance(type_etag,str) or not 1<=len(type_etag)<=100:
        raise ValueError('current Manager job-type etag required')
    if type(chunk_size) is not int or not 1<=chunk_size<=1000:
        raise ValueError('chunk_size must be 1..1000')
    root=Path(shared_root).resolve(strict=True)
    blend=Path(blend_file).resolve(strict=True)
    output=Path(output_root).resolve()
    if not root.is_dir() or not blend.is_file() or blend.suffix.lower()!='.blend':
        raise ValueError('shared root and an existing native .blend are required')
    if not blend.is_relative_to(root) or not output.is_relative_to(root) or output==root:
        raise ValueError('input/output must remain inside the explicit shared root')
    if output.exists():
        raise ValueError('output directory must be new; no implicit resume or mixing')
    platform=platform or ('windows' if sys.platform=='win32' else sys.platform)
    if platform not in ('linux','windows','darwin'):
        raise ValueError('unsupported submitter platform')
    return {'name':name,'type':'simple-blender-render','type_etag':type_etag,'priority':50,
            'submitter_platform':platform,'metadata':{'project':'FLAMORIS Cinema'},
            'settings':{'blendfile':str(blend),'scene':scene_name,'frames':f'1-{frame_count(scene)}',
                        'chunk_size':chunk_size,'fps':scene['fps'],'format':'PNG','image_file_extension':'.png',
                        'has_previews':False,'render_output_root':str(output),'add_path_components':0,
                        'render_output_path':str(output/'######')}}
