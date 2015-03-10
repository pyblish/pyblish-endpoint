"""Pyblish Endpoint Server"""

# Standard library
import os
import logging
import threading

# Dependencies
import flask
import flask.ext.restful

# Local library
import service as service_mod
import resource
import mocking

log = logging.getLogger("endpoint")

prefix = "/pyblish/v1"
resource_map = {
    "/application": resource.ApplicationApi,
    "/application/shutdown": resource.ApplicationShutdownApi,
    "/plugins": resource.PluginsListApi,
    "/session": resource.SessionApi,
    "/instances": resource.InstancesListApi,
    "/instances/<instance_id>": resource.InstancesApi,
    "/instances/<instance_id>/nodes": resource.NodesListApi,
    "/instances/<instance_id>/data": resource.DataListApi,
    "/instances/<instance_id>/data/<data_id>": resource.DataApi,
    "/state": resource.StateApi,
    "/next": resource.NextApi,
    "/dispatch": resource.Dispatch,
}

endpoint_map = {
    "/application":                     "application",
    "/application/shutdown":            "application.shutdown",
    "/instances/<instance_id>":         "instance",
    "/instances":                       "instances",
    "/instances/<instance_id>/nodes":   "instance.nodes",
    "/instances/<instance_id>/data":    "instance.data",
    "/state":                           "state",
    "/next":                            "next",
    "/dispatch":                        "dispatch",
}


def create_app():
    log.debug("Creating app")
    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    api = flask.ext.restful.Api(app)

    log.debug("Mapping URIs")
    for uri, _resource in resource_map.items():
        endpoint = endpoint_map.get(uri)
        api.add_resource(_resource, prefix + uri, endpoint=endpoint)

    log.debug("App created")
    return app, api


def start_production_server(port, service, **kwargs):
    """Start production server

    Arguments:
        port (int): Port at which to listen for requests
        service (EndpointService): Service exposed at port.
            Each host implements its own service.

    """

    # Lessen web-server output
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    service_mod.register_service(service, force=True)
    app, api = create_app()
    app.run(port=port, threaded=True)


def start_async_production_server(port, service):
    """Start production server in a separate thread

    For arguments, see func:`start_production_server`

    """

    def worker():
        start_production_server(port, service, threaded=True)

    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()


def start_debug_server(port, **kwargs):
    """Start debug server

    This server uses a mocked up service to fake the actual
    behaviour and data of a generic host; incuding faked time
    it takes to perform a task.

    Arguments:
        port (int): Port at which to listen for requests

    """

    # Log to console
    formatter = logging.Formatter("%(levelname)-8s %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    os.environ["ENDPOINT_PORT"] = str(port)

    Service = mocking.MockService
    Service.SLEEP_DURATION = .5
    Service.PERFORMANCE = Service.FAST
    service_mod.register_service(Service)

    # Expose vendor libraries to external Python process
    # triggered by running Flask in debug-mode.
    package_dir = os.path.dirname(__file__)
    vendor_dir = os.path.join(package_dir, "vendor")
    if not os.environ["PYTHONPATH"]:
        os.environ["PYTHONPATH"] = ""

    os.environ["PYTHONPATH"] += os.pathsep + vendor_dir

    app, api = create_app()
    app.run(debug=True, port=port, threaded=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6000, help="Port to use")

    args = parser.parse_args()

    start_debug_server(**args.__dict__)
