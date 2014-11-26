"""Pyblish Endpoint Server"""

# Standard library
import os
import sys
import logging

# Register vendor packages
package_dir = os.path.dirname(__file__)
vendor_dir = os.path.join(package_dir, "vendor")
sys.path.insert(0, vendor_dir)

# Dependencies
import flask
import flask.ext.restful

# Local library
import service as service_mod
import resource

log = logging.getLogger("endpoint")

prefix = "/pyblish/v1"
resource_map = {
    "/processes": resource.ProcessesListApi,
    "/processes/<process_id>": resource.ProcessesApi,
    "/processes/<process_id>/log": resource.ProcessesLogApi,
    "/application": resource.ApplicationApi,
    "/application/shutdown": resource.ApplicationShutdownApi,
    "/plugins": resource.PluginsListApi,
    "/session": resource.SessionApi,
    "/instances": resource.InstancesListApi,
    "/instances/<instance_id>": resource.InstancesApi,
    "/instances/<instance_id>/nodes": resource.NodesListApi,
    "/instances/<instance_id>/data": resource.DataListApi,
    "/instances/<instance_id>/data/<data_id>": resource.DataApi,
}

endpoint_map = {
    "/processes/<process_id>":          "process",
    "/processes/<process_id>/log":      "process.log",
    "/processes":                       "processes",
    "/application":                     "application",
    "/application/shutdown":            "application.shutdown",
    "/instances/<instance_id>":         "instance",
    "/instances":                       "instances",
    "/instances/<instance_id>/nodes":   "instance.nodes",
    "/instances/<instance_id>/data":    "instance.data",
}


def create_app():
    log.debug("Creating app")
    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    api = flask.ext.restful.Api(app)

    # Map resources to URIs
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

    service_mod.register_service(service)
    app, api = create_app()
    app.run(port=port)


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

    service_mod.MockService.SLEEP_DURATION = 3
    service_mod.register_service(service_mod.MockService)

    app, api = create_app()
    app.run(debug=True, port=port)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6000, help="Port to use")

    args = parser.parse_args()

    start_debug_server(**args.__dict__)
