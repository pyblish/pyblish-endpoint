# Standard library
import threading

# Local library
import lib
lib.register_vendor()

import service as service_
import interface

# Dependencies
import flask
import flask.ext.restful
import requests


app = flask.Flask(__name__)
api = flask.ext.restful.Api(app)

api.add_resource(interface.Instance, "/instance")
api.add_resource(interface.Publish, "/publish")

PORT = 6000


def start(service, port=None, safe=False):
    """Start server

    Arguments:
        service (EndpointService): Host integration
        safe (bool): Ensure there is no existing server already running

    """

    service_.register_service(service)

    if safe:
        stop()

    if port:
        global PORT
        PORT = port

    def run():
        app.run(port=PORT)

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
    print "Running Endpoint @ port %i.." % PORT

    return thread


def stop():
    try:
        requests.post("http://127.0.0.1:%i/shutdown" % PORT)
    except:
        pass


def restart():
    stop()
    start()


def _shutdown_server():
    """Shutdown the currently running server"""
    func = flask.request.environ.get("werkzeug.server.shutdown")
    if func is not None:
        func()


@app.route("/shutdown", methods=["POST"])
def _shutdown():
    """Shutdown server
    Utility endpoint for remotely shutting down server.
    Usage:
        $ curl -X GET http://127.0.0.1:6000/shutdown
    """

    print "Server shutting down..."
    _shutdown_server()
    print "Server stopped"
    return True


if __name__ == '__main__':
    app.run(port=PORT, debug=True)
