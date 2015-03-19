import os
import json

from vendor import jsonschema

_cache = {}
module_dir = os.path.dirname(__file__)


def parse(schema):
    if schema not in _cache:
        path = os.path.join(module_dir,
                            "schema_%s.json" % schema)
        with open(path, "r") as f:
            _cache[schema] = f.read()

    return json.loads(_cache[schema])


def validate(data, schema):
    schema = parse(schema)
    return jsonschema.validate(
        data, schema, types={"array": (list, tuple)})


ValidationError = jsonschema.ValidationError
