import json
import logging

from .. import server, service
from nose.tools import *

import lib

app, api = server.create_app()
app.config["TESTING"] = True
client = app.test_client()
client.testing = True

log = logging.getLogger()
log.setLevel(logging.WARNING)

service.register_service(lib.TestService, force=True)


# Helper functions

def setup():
    pass


def teardown():
    response = request("DELETE", "/state")
    check_content_type(response)
    check_status(response, 200)


def check_content_type(response):
    """Ensure content type is JSON"""
    eq_(response.headers['Content-Type'], 'application/json')


def check_status(response, status):
    """Ensure response.status_code == `status`"""
    eq_(response.status_code, status)


def check_keys(data, keys):
    """Ensure `keys` are available in `data`"""
    eq_(set(keys).issubset(data.keys()), True)


def load_data(response):
    return json.loads(response.data)


def request(verb, address, *args, **kwargs):
    func = getattr(client, verb.lower())
    return func("/pyblish/v1" + address, *args, **kwargs)


@with_setup(setup, teardown)
def test_get_state():
    """Getting state does not change state"""

    # Getting state, before posting, yields an empty state
    response = request("GET", "/state")
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert "ok" in data
    assert "state" in data

    state = data["state"]
    empty_state = {
        "context": {
            "data": {},
            "children": []
        },
        "plugins": []
    }

    assert_equal(state, empty_state)

    # Posting for the first time yields a *new* state
    response = request("POST", "/state")
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert "ok" in data

    # Getting it now yields identical results
    response = request("GET", "/state")
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert "ok" in data
    assert "state" in data

    state = data["state"]

    assert_not_equal(state, empty_state)


@with_setup(setup, teardown)
def test_post_state():
    """Posting state updates it"""

    # Initialise state
    response = request("POST", "/state")
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)

    # Make a change
    _instance = lib.INSTANCES[1]

    # BEFORE
    response = request("GET", "/state")
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert_true(data.get("ok"))
    assert "state" in data, data

    # Change
    instance = data["state"]["context"]["children"][1]
    assert_equal(instance["name"], _instance)
    current_value = instance["data"]["publish"]
    assert_true(isinstance(current_value, bool))
    changed_value = not current_value

    changes = {
        "context": {
            _instance: {
                "publish": {
                    "new": changed_value,
                    "old": current_value
                }
            }
        }
    }

    s_changes = json.dumps(changes, indent=4)

    response = request("POST", "/state",
                       data={"changes": s_changes})
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert_true(data.get("ok"))
    assert "changes" in data
    assert_equal(data["changes"], changes)

    # AFTER
    response = request("GET", "/state")
    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert_true(data.get("ok"))
    assert "state" in data, data

    instance = data["state"]["context"]["children"][1]
    assert_equal(instance["name"], _instance)
    assert_true(isinstance(current_value, bool))
    assert_equal(instance["data"]["publish"], changed_value)


@with_setup(setup, teardown)
def test_put_state():
    """PUT to /state processes the given pair"""

    # Initialise state
    response = request("POST", "/state")
    check_content_type(response)
    check_status(response, 200)

    _instance = lib.INSTANCES[1]
    _plugin = lib.PLUGINS[0].__name__

    response = request("PUT", "/state", data={
        "instance": _instance,
        "plugin": _plugin
    })

    check_content_type(response)
    check_status(response, 200)
    data = load_data(response)
    assert "result" in data

    result = data["result"]

    assert_true(result["success"])
    assert_equal(result["instance"], _instance)
    assert_equal(result["plugin"], _plugin)
