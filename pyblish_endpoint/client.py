"""Client API

The server may send requests to client from here, but only if client
has signalled that it is receiving them.

"""

import resource


def request(data):
    """Send request to client"""
    resource.queue.put(data)
