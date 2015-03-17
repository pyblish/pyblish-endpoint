"""Endpoint resources

Attributes:
    log: Current logger
    queue: Cache of requests for long-polling; see Client

"""

# Standard library
import sys
import json
import Queue
import logging
import traceback

# Dependencies
import flask.ext.restful
import flask.ext.restful.reqparse

# Local library
import service as service_mod

log = logging.getLogger("endpoint")
queue = Queue.Queue()


class ClientApi(flask.ext.restful.Resource):
    """Client API

    Send requests from server to client.
    A heartbeat is emitted once every second.

    GET /client
    POST /client

    """

    def get(self):
        dequeue = [str(item) for item in queue.queue]
        return {"ok": True, "queue": dequeue}, 200

    def post(self):
        try:
            message = queue.get(timeout=1)
        except Queue.Empty:
            return {"ok": True, "message": "heartbeat"}, 200

        return {"ok": True, "message": message}, 200


class StateApi(flask.ext.restful.Resource):
    """State API between host and client

    GET /state
    POST /state
    PUT /state
    DELETE /state

    """

    def get(self):
        """Return state; do not modify

        :>jsonarr array context: Context, incl. data and children
        :>jsonarr array plugins: Available plug-ins

        :status 200: Plug-ins returned

        """

        state = service_mod.current().state
        state.compute()
        return {"ok": True, "state": state}

    def put(self):
        """Advance state

        :>jsonarr string ok: Status message

        :status 200: Advance ok
        :status 404: Nothing left to advance to

        """

        service = service_mod.current()
        state = service.advance()

        if state:
            return {"ok": True, "state": state}, 200

        return {"ok": True}, 404

    def post(self):
        """Update state

        Given a `state`, update the host. Else re-evaluate
        current state of host and return it.

        :<jsonarr array state: Changes from client
        :>jsonarr array state: Applied changes
        :>jsonarr string message: Error message when status == 500

        :status 200: State returned
        :status 500: Internal error; see `message` for information.

        """

        parser = flask.ext.restful.reqparse.RequestParser()
        parser.add_argument("state", type=str)

        kwargs = parser.parse_args()
        service = service_mod.current()

        if kwargs["state"] is None:
            service.init()

        else:
            try:
                state = json.loads(kwargs["state"])
                service.state.update(state)

            except ValueError:
                message = "Could not de-serialise state: %r" % kwargs
                log.error(message)
                return {"ok": False, "message": message}, 500

            except Exception as e:
                try:
                    _, _, exc_tb = sys.exc_info()
                    message = traceback.format_tb(exc_tb)[-1]
                except:
                    message = str(e)

                log.error(message)
                return {"ok": False, "message": str(message)}, 500

            return {"ok": True, "state": state}, 200

        return {"ok": True}, 200

    def delete(self):
        """Delete state

        Clears the current state; must POST to re-initialise.

        :>json bool ok: Status message

        :status 200: State deleted successfully
        :status 500: Internal error

        """

        try:
            service_mod.current().reset()

        except Exception as e:
            return {"ok": False, "message": str(e)}, 500

        return {"ok": True}, 200
