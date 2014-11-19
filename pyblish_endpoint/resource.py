"""Endpoint resources

Attributes:
    queue: Logging messages, per process
    threads: Container of threads, stored under their unique ID
    log: Current logger

"""

# Standard library
import uuid
import Queue
import logging
import threading

# Dependencies
import flask.ext.restful
import flask.ext.restful.reqparse

# Local library
from service import current_service

queues = {}
threads = {}

log = logging.getLogger("endpoint")


class MessageHandler(logging.Handler):
    """Intercept logging and store them in a queue per process

    The queue is emptied upon calling GET /processes/<process_id>

    """

    def __init__(self, thread, queue, *args, **kwargs):
        super(MessageHandler, self).__init__(*args, **kwargs)
        self.thread = thread
        self.queue = queue

    def emit(self, record):
        # Do not record server messages
        if record.name in ["werkzeug"]:
            return

        # Only store records from current thread
        # WARNING: This won't work in Maya, because
        # Maya insists on running things in the main thread
        # which causes threadName to always be "MainThread"

        # if record.threadName == self.thread:
        #     self.queue.put(record)

        # As a workaround, record everything.
        # NOTE: This is O(n) and thus much slower
        self.queue.put_nowait(record)


def unique_id():
    """Return a universally unique identifier

    Using as few characters as possible. The condition is
    that a process is typically executed 1 at a time, at
    a given rate of 2/second, and shall remain referencable
    for a short period of time (10-20 minutes) after first
    being created.

    """

    return uuid.uuid4().hex[:5]


class ApplicationShutdownApi(flask.ext.restful.Resource):
    def post(self):
        """Shutdown server

        Utility resource for remotely shutting down server.

        :status 200: Server successfully shutdown
        :status 400: Could not shut down

        :>json bool ok: Operation status, not returned on error
        :>json string message: Error message

        **Example Request**

        .. sourcecode:: http

            POST /shutdown
            Host: localhost
            Accept: application/json

        **Example Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Vary: Accept
            Content-Type: application/json

            {"ok": true}

        """

        log.info("Server shutting down...")

        func = flask.request.environ.get("werkzeug.server.shutdown")
        if func is not None:
            func()
        else:
            return {"message": "Could not shutdown server"}, 400

        log.info("Server stopped")

        return {"ok": True}, 200


class ApplicationApi(flask.ext.restful.Resource):
    """Application API

    GET /application

    """

    def get(self):
        """Return application statistics

        :status 200: Application statistics returned

        :>json string host
        :>json string port
        :>json string pyblishVersion
        :>json string endpointVersion
        :>json string pythonVersion
        :>json string user
        :>json string connectTime

        """

        data = {}

        data.update(current_service().system())
        data.update(current_service().versions())

        return data, 200


class ProcessesListApi(flask.ext.restful.Resource):
    def get(self):
        """Get all currently running processes

        :>jsonarr string process_id: Identifier of process

        :status 200: Processes returned successfully

        **Example response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            [
                {"process_id": 12345},
                {"process_id": 12346},
                {"process_id": 12347},
            ]

        """

        process_ids = []
        for process_id in threads.keys():
            process_ids.append({"process_id": process_id})

        return process_ids, 200

    def post(self):
        """Process instance with plug-in

        :param string instance: Instance to process
        :param string plugin: Plug-in used for processing

        :>json string process_id: Unique id of process
        :>json string _next: Link to where id may be used to
            query about process

        :status 201: Process was successfully created
        :status 400: Missing argument(s)

        """

        parser = flask.ext.restful.reqparse.RequestParser()

        parser.add_argument("instance",
                            type=str,
                            required=True,
                            help="Instance can't be blank")
        parser.add_argument("plugin",
                            type=str,
                            required=True,
                            help="Plugin can't be blank")

        kwargs = parser.parse_args()

        def task(instance, plugin):
            try:
                current_service().process(instance, plugin)
            except ValueError as e:
                log.error("Processing failure for %s|%s: %s"
                          % (instance, plugin, e))

        process_id = unique_id()

        # Spawn task in new thread
        thread = threading.Thread(
            name=process_id,
            target=task,
            kwargs=kwargs)
        thread.deamon = True
        thread.start()

        # Setup logger
        queue = Queue.Queue()
        handler = MessageHandler(thread=thread.name, queue=queue)
        # handler.setLevel(logging.DEBUG)

        # Logger is deleted during GET /processes/<process_id>
        log = logging.getLogger()
        log.addHandler(handler)
        # log.setLevel(logging.DEBUG)

        # Store references
        # Note: This is not stateless and violates REST and possibly
        # web integration as a whole. How else can we do this?
        queues[process_id] = [queue, handler]
        threads[process_id] = thread

        return {"process_id": process_id,
                "_next": "/processes/<process_id>"}, 201


class ProcessesApi(flask.ext.restful.Resource):
    def get(self, process_id=None):
        """Query a process

        :param process_id: Unique process identifier

        :>json string process_id: The identifier passed in
        :>json bool running: Current state of this process
        :>json array messages: List of queued messages

        :status 200: Process existed and was returned
        :status 404: process_id was not found

        The following is the signature of the **messages** array.

        :>jsonarr string name: Name of logger used to log the event
        :>jsonarr string msg: Actual logged message
        :>jsonarr string levelname: Level used for event
        :>jsonarr string filename: Filename in which event was logged
        :>jsonarr string pathname: Absolute path from which event was logged
        :>jsonarr string lineno: Line within filename event was logged
        :>jsonarr string funcName: Function used to log the event
        :>jsonarr string module: Name of module used

        **Example request**

        .. sourcecode:: http

            GET /api/v0.1/process/12345
            Host: localhost
            Accept: application/json

        **Example response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "process_id": 12345,
                "running": true
            }

        """

        try:
            thread = threads[process_id]
        except KeyError:
            return {"message": "%s did not exist" % process_id}, 404

        return {"process_id": process_id,
                "running": thread.is_alive()}, 200

    def put(self, process_id):
        """Modify a process

        :param process_id: Unique process identifier

        :status 200: Process was successfully modified

        :>json bool ok: Operation status

        """

        return {"ok": False, "process_id": process_id}, 501  # Not implemented

    def delete(self, process_id):
        """Kill a currently running process

        :param process_id: Unique process identifier

        :status 200: Process was successfully killed
        :status 404: Process was not found
        :status 406: Process is not currently running

        :>json bool ok: Operation status, not returned upon error
        :>json string message: Error message

        """

        return {"ok": False}, 501  # Not implemented

        try:
            thread = threads.pop(process_id)
        except KeyError:
            return {"message": "Process was not found"}, 404

        if not thread.is_alive():
            return {"message": "Process is not currently running"}, 406

        return {"ok": True}, 200


class ProcessesLogsApi(flask.ext.restful.Resource):
    def get(self, process_id):
        """Get log messages for instance

        :status 200: Log messages returned
        :status 404: process_id was not found

        :>jsonarr string message: Logged message
        :>jsonarr string time: Time of event

        :<json string format: Python format string, e.g.
            '%(level)s %(message)s'

        """

        parser = flask.ext.restful.reqparse.RequestParser()
        parser.add_argument("format", default="%(asctime)s "
                                              "%(levelname)s "
                                              "%(message)s")

        kwargs = parser.parse_args()

        formatter = logging.Formatter(kwargs["format"])

        messages = []

        try:
            process_queue, process_handler = queues[process_id]
        except KeyError:
            return messages, 200

        while not process_queue.empty():
            record = process_queue.get()
            message = formatter.format(record)
            print "Getting %s from queue" % message
            messages.append(message)

        # Clean-up queue in case thread is dead
        thread = threads[process_id]
        if not thread.is_alive():
            queues.pop(process_id)
            log.removeHandler(process_handler)

        return messages, 200


class InstancesListApi(flask.ext.restful.Resource):
    def get(self):
        """Get all available instances

        :status 200: Instances returned successfully

        :>jsonarr string name: Name of instance
        :>jsonarr string objName: Name of instance
        :>jsonarr string family: All contained nodes of instance
        :>jsonarr bool publish: Should instance be published?
        :>jsonarr array nodes: Array of included nodes
        :>jsonarr obj data: Instance metadata

        **Example response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            [
                {
                    "name": "Instance01",
                    "objName": "Instance01_:publish_SEL",
                    "family": "napoleon.asset.rig"
                },
                {
                    "name": "Instance02",
                    "objName": "Instance02_:pointcache_SEL",
                    "family": "napoleon.animation.pointcache"
                },
            ]

        """

        instances = current_service().instances()
        assert isinstance(instances, list)
        return instances, 200


class InstancesApi(flask.ext.restful.Resource):
    def get(self, instance_id):
        """Query links to instance resources

        :status 200: Links returned

        :>json string nodes: Link to nodes of instance
        :>json string data: Link to data of instance

        """

        instance = current_service().instance(instance_id)
        instance["_links"] = [
            {"rel": "/nodes"},
            {"rel": "/data"}
        ]

        return instance, 200


class NodesListApi(flask.ext.restful.Resource):
    def get(self, instance_id):
        """Get nodes of instance `instance_id`

        :status 200: Nodes returned successfully
        :status 404: instance_id was not found

        :>jsonarr name: Name of node

        """

        instance = current_service().instance(instance_id)
        if not instance:
            return {"message": "instance_id %s not found" % instance_id}, 404

        nodes = instance.get("nodes", {})

        return nodes, 200


class DataListApi(flask.ext.restful.Resource):
    """API for instance data

    Each instance contains some amount of additional data, known
    as metadata. This includes both internal data, such as it's
    family, along with external - user customisable - data, such
    as at which frame an animation is to start.

    """

    def get(self, instance_id):
        """Get data of instance

        :status 200: Data was returned successfully
        :status 404: instance_id was not found

        :>json obj data: Available data returned as object

        """

        instance = current_service().instance(instance_id)
        if not instance:
            return {"message": "instance_id %s not found" % instance_id}, 404

        data = instance.get("data", {})

        return data, 200


class DataApi(flask.ext.restful.Resource):
    """API for individual items of data

    GET /instances/<id>/data/<id>
    PUT /instances/<id>/data/</id>
    DELETE /instances/<id>/data/<id>

    """

    def get(self, instance_id, data_id):
        pass
