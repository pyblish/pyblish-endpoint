"""Pyblish Endpoint Server"""

# Standard library
import os
import logging
import threading

# Dependencies
import flask
import flask.ext.restful

# Local library
import mocking
import resource
import service as service_mod

log = logging.getLogger("endpoint")

prefix = "/pyblish/v1"
resource_map = {
    "/state": resource.StateApi,
    "/client": resource.ClientApi,
    "/hello": resource.HelloApi,
}

endpoint_map = {
    "/state":  "state",
    "/client": "client",
    "/hello": "hello",
}

current_server = None
current_server_thread = None


def create_app():
    log.info("Creating app")
    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    api = flask.ext.restful.Api(app)

    log.info("Mapping URIs")
    for uri, _resource in resource_map.items():
        endpoint = endpoint_map.get(uri)
        api.add_resource(_resource, prefix + uri, endpoint=endpoint)

    log.info("App created")
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

    global current_server
    current_server = app


def start_async_production_server(port, service):
    """Start production server in a separate thread

    For arguments, see func:`start_production_server`

    """

    def worker():
        start_production_server(port, service, threaded=True)

    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()

    global current_server_thread
    current_server_thread = t


def start_debug_server(port, delay=0.5, **kwargs):
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
    Service.SLEEP_DURATION = delay
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
    parser.add_argument("--delay", type=float, default=0.5, help="Higher value means slower")

    args = parser.parse_args()

    start_debug_server(**args.__dict__)
