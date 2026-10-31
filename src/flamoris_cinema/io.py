"""Bounded JSON input and exclusive output; never execute scene content."""
import json
from pathlib import Path

MAX_JSON_BYTES = 64 * 1024 * 1024


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON property: {key}")
        result[key] = value
    return result


def read_json(path):
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_JSON_BYTES + 1)
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("JSON exceeds 64 MiB")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON number: {value}")))
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("invalid JSON document") from exc


def write_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    if len(payload.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("JSON exceeds 64 MiB")
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
