import json
import logging

from pyblish_endpoint import server, service
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


# @with_setup(setup, teardown)
# def test_get_state():
#     """Getting state does not change state"""

#     # Getting state, before posting, yields an empty state
#     response = request("GET", "/state")
#     check_content_type(response)
#     check_status(response, 200)
#     data = load_data(response)
#     assert "ok" in data
#     assert "state" in data

#     assert_true(data["state"].get("context") is None)
#     assert_true(data["state"].get("plugins") is None)

#     # Posting for the first time yields a *new* state
#     response = request("POST", "/state")
#     check_content_type(response)
#     check_status(response, 200)
#     data = load_data(response)
#     assert "ok" in data

#     # Getting it now yields identical results
#     response = request("GET", "/state")
#     check_content_type(response)
#     check_status(response, 200)
#     data = load_data(response)
#     assert "ok" in data
#     assert "state" in data

#     assert_true(data["state"].get("context") is not None)
#     assert_true(data["state"].get("plugins") is not None)


# @with_setup(setup, teardown)
# def test_post_state():
#     """Posting state updates it"""

#     # Initialise state
#     response = request("POST", "/state")
#     check_content_type(response)
#     check_status(response, 200)
#     data = load_data(response)

#     # Make some changes; do not publish "Richard05"
#     _instance = lib.INSTANCES[1]

#     # BEFORE
#     response = request("GET", "/state")
#     check_content_type(response)
#     check_status(response, 200)
#     data = load_data(response)
#     assert_true(data.get("ok"))
#     assert "state" in data, data

#     # Change
#     instance = data["state"]["context"]["children"][1]
#     assert_equal(instance["name"], _instance)
#     current_value = instance["data"]["publish"]
#     assert_true(isinstance(current_value, bool))
#     changed_value = not current_value

#     changes = {
#         "context": {
#             "children": [
#                 {
#                     "name": _instance,
#                     "data": {"publish": changed_value}
#                 }
#             ]
#         }
#     }

#     s_changes = json.dumps(changes, indent=4)

#     response = request("POST", "/state",
#                        data={"state": s_changes})
#     check_content_type(response)
#     check_status(response, 200)
#     data = load_data(response)
#     assert_true(data.get("ok"))
#     assert "state" in data
#     assert_equal(data["state"], changes)

#     # AFTER
#     response = request("GET", "/state")
#     check_content_type(response)
#     check_status(response, 200)
#     data = load_data(response)
#     assert_true(data.get("ok"))
#     assert "state" in data, data

#     instance = data["state"]["context"]["children"][1]
#     assert_equal(instance["name"], _instance)
#     assert_true(isinstance(current_value, bool))
#     assert_equal(instance["data"]["publish"], changed_value)


# @with_setup(setup, teardown)
# def test_put_state():
#     """PUT to /state advances state to next item"""

#     # Initialise state
#     response = request("POST", "/state")
#     check_content_type(response)
#     check_status(response, 200)

#     c_service = service.current()

#     for plugin in c_service.plugins:
#         data = None

#         for instance in c_service.context:

#             # Peter01 of lib.INSTANCES is skipped
#             if instance.data("name") == "Peter01":
#                 continue

#             # Advance
#             response = request("PUT", "/state")
#             check_content_type(response)
#             check_status(response, 200)
#             data = load_data(response)

#             assert_equal(
#                 instance.data("name"),
#                 data["state"]["current_instance"])

#         if data:
#             assert_equal(plugin.__name__,
#                          data["state"]["current_plugin"])

#         print "Plugin: %s" % plugin.__name__

#     # Advance
#     # At this point, all plug-ins and instances have been
#     # processed and we should be getting a 404.
#     response = request("PUT", "/state")
#     data = load_data(response)
#     print json.dumps(data, indent=4)
#     check_content_type(response)
#     check_status(response, 404)
