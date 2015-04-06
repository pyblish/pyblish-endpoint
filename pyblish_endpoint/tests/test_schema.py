import os
from nose.tools import *

from .. import schema
from .. import service


def test_schema_format():
    """All schemas load fine"""
    schemas = list()
    for s in os.listdir(os.path.dirname(schema.__file__)):
        if s.startswith("schema_") and s.endswith(".json"):
            s = s.split("schema_", 1)[-1]
            s = s.rsplit(".json", 1)[0]
            schemas.append(s)

    for s in schemas:
        print "Loading %s" % s
        schema.load(s)


def test_state_alignment():
    """State is aligned with schema"""
    s = service.EndpointService()
    s.init()

    instance = s.context.create_instance("MyInstance")
    instance.set_data("family", "myFamily")

    s.state.compute()

    schema.validate(s.state, "state")


def test_changes_misnamed():
    """Changes are aligned with schema"""
    data = {
        "context": {
            "MyInstance": {
                "startFrame": {
                    "new": 2000,
                    "old": 1000
                },
                "endFrame": {
                    "new": 2100,
                    "old": 1000
                }
            }
        }
    }

    schema.validate(data, schema="changes")

    bad_data = data.copy()
    bad_data["context"]["MyInstance"]["startFrame"].pop("new")
    bad_data["context"]["MyInstance"]["startFrame"]["mew"] = 1000

    assert_raises(schema.ValidationError,
                  schema.validate, bad_data, schema="changes")


def test_changes_malformatted():
    """Missing `plugins` key"""
    changes = {
        "context_bad": {}
    }

    assert_raises(schema.ValidationError,
                  schema.validate, changes, schema="changes"),
