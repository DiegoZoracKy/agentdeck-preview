"""JSON containers that own immutable renderer metadata snapshots."""

import json
from typing import Any


def _immutable(*args, **kwargs):
    raise TypeError("RenderResult metadata is immutable; create a new RenderResult")


class _FrozenDict(dict):
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


class _FrozenList(list):
    __setitem__ = __delitem__ = __iadd__ = __imul__ = _immutable
    append = clear = extend = insert = pop = remove = reverse = sort = _immutable

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


def freeze_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Copy JSON data before freezing it; snapshots never alias caller containers."""
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise TypeError("RenderResult.metadata must be a JSON-serializable dict")
    # A JSON round trip validates cycles, non-JSON values and non-finite numbers,
    # and ensures only JSON-native scalar/container types enter the snapshot.
    snapshot = json.loads(json.dumps(metadata, allow_nan=False))

    def freeze(value):
        if isinstance(value, dict):
            return _FrozenDict({key: freeze(item) for key, item in value.items()})
        if isinstance(value, list):
            return _FrozenList(freeze(item) for item in value)
        return value

    return freeze(snapshot)
