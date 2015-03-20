"""Client API

The server may send requests to client from here, but only if client
has signalled that it is receiving them.

"""

import warnings
import resource


def request(data):
    warnings.warn("pyblish_endpoint.client.request() deprecated; use emit()")
    emit(data)


def emit(message):
    """Emit message to client"""
    resource.request_queue.put(message)
