"""JSON Schema utilities

Attributes:
    _cache: Cache of previously loaded schemas

Resources:
    http://json-schema.org/
    http://json-schema.org/latest/json-schema-core.html
    http://spacetelescope.github.io/understanding-json-schema/index.html

"""

import os
import json

from vendor import jsonschema

_cache = {}
module_dir = os.path.dirname(__file__)


def load(schema):
    if schema not in _cache:
        path = os.path.join(module_dir,
                            "schema_%s.json" % schema)
        with open(path, "r") as f:
            _cache[schema] = f.read()

    return json.loads(_cache[schema])


def validate(data, schema):
    schema = load(schema)
    return jsonschema.validate(
        data, schema, types={"array": (list, tuple)})


ValidationError = jsonschema.ValidationError

__all__ = ["validate",
           "ValidationError"]
