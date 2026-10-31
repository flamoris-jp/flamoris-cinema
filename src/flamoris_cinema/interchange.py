"""One self-contained portable take: scene plus authoritative sampled motion."""
from copy import deepcopy
from .contracts import validate_animation, validate_scene, fields, motion_id


def make_take(scene, animation):
    validate_animation(animation, scene)
    # Legacy prototype animations are accepted and upgraded when bundled.
    animation = deepcopy(animation)
    animation["motion_id"] = motion_id(scene)
    return {"format": "flamoris-cinema-take", "version": scene['schema_version'],
            "scene": deepcopy(scene), "animation": animation}


def validate_take(take):
    fields(take, ("format", "version", "scene", "animation"), path="take")
    if take["format"] != "flamoris-cinema-take" or type(take["version"]) is not int or take["version"] not in (1, 2):
        raise ValueError("unsupported take format")
    validate_scene(take["scene"])
    if take['version'] != take['scene']['schema_version']:
        raise ValueError('take and scene version differ')
    validate_animation(take["animation"], take["scene"])
    return take
