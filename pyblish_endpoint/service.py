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

import os
import sys
import abc
import time
import getpass
import pyblish
import logging

from version import version

log = logging.getLogger("endpoint")


class EndpointService(object):
    """Abstract baseclass for host interfaces towards endpoint"""

    __metaclass__ = abc.ABCMeta
    _current = None

    def system(self):
        """Confirm connection and return system state"""

        executable = sys.executable
        basename = os.path.basename(executable)
        name, _ = os.path.splitext(basename)

        return {
            "host": name,
            "port": int(os.environ.get("ENDPOINT_PORT", -1)),
            "user": getpass.getuser(),
            "connectTime": time.time()
        }

    def versions(self):
        return {
            "pyblishVersion": pyblish.version,
            "endpointVersion": version,
            "pythonVersion": sys.version,
        }

    @abc.abstractmethod
    def instances(self):
        """Return list of instances

        Returns
            A list of dictionaries; one per instance

        """

        return []

    @abc.abstractmethod
    def instance_data(self, instance_id):
        pass

    @abc.abstractmethod
    def instance_nodes(self, instance_id):
        pass


def current_service():
    return EndpointService._current


def register_service(service, force=False):
    """Register service

    The service will be used by the endpoint for host communication
    and represents a host-specific layer inbetween Pyblish and Endpoint.

    Arguments:
        service (EndpointService): Service to register
        force (bool): Overwrite any existing service

    """

    if EndpointService._current is not None and force is False:
        raise ValueError("An existing service was found, "
                         "use deregister_service to remove it")
    EndpointService._current = service()
    log.info("Registering: %s" % service)


def deregister_service(service=None):
    if service is None or service is EndpointService._current:
        EndpointService._current = None
    else:
        raise ValueError("Could not deregister service")
