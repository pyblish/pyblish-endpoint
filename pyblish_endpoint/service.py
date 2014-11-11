"""Endpoint Service

In order to protect Endpoint from the internals or both Pyblish
and each host application, the service acts as a layer inbetween
the two.

Users are encouraged to subclass :class:`EndpointService` and
implement a minimum amount of features along with optionals.

Mandatory features are marked as being abstractmethods, whereas
optional features are not.

Optional features are, as the name implies, not necessary for
overall operation but may provide additional feedback or features
to users.

"""

import abc


class EndpointService(object):
    """Abstract baseclass for host interfaces towards endpoint"""

    __metaclass__ = abc.ABCMeta
    _current = None

    @abc.abstractmethod
    def instances(self):
        """Return list of instances

        Returns
            A list of dictionaries; one per instance

        """

        return []

    @abc.abstractmethod
    def publish(self):
        """Perform publish

        Returns
            A status message

        """

        return {
            "message": "success",
            "status": 200
        }


def current_service():
    return EndpointService._current


def register_service(service):
    """Register service

    The service will be used by the endpoint for host communication
    and represents a host-specific layer inbetween Pyblish and Endpoint.

    Arguments:
        service (EndpointService): Service to register

    """

    print "Registering: %s" % service

    if EndpointService._current is not None:
        raise ValueError("An existing service was found, "
                         "use deregister_service to remove it")
    EndpointService._current = service()


def deregister_service(service=None):
    if service is None or service is EndpointService._current:
        EndpointService._current = None
    else:
        raise ValueError("Could not deregister service")
