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

        Returns:
            A list of dictionaries; one per instance

        """

        return []

    def instance(self, name):
        instances = self.instances()
        try:
            return filter(lambda i: i["name"] == name, instances)[0]
        except IndexError:
            return None


class MockService(EndpointService):
    """Service for testing

    Attributes:
        SLEEP_DURATION: Fake processing delay, in milliseconds
        NUM_INSTANCES: Fake amount of available instances (max: 2)

    """

    SLEEP_DURATION = 0
    NUM_INSTANCES = 2

    def instances(self):
        instances = [
            {
                "name": "Peter01",
                "objName": "Peter01:pointcache_SEL",
                "family": "napoleon.asset.rig",
                "publish": True,
                "nodes": [
                    {"name": "node1"},
                    {"name": "node2"},
                    {"name": "node3"}
                ],
                "data": {
                    "identifier": "napoleon.instance",
                    "minWidth": 800,
                    "assetSource": "/server/assets/Peter",
                    "destination": "/server/published/assets"
                }
            },

            {
                "name": "Richard05",
                "objName": "Richard05:pointcache_SEL",
                "family": "napoleon.animation.rig",
                "publish": True,
                "nodes": [],
                "data": {}
            }
        ]

        return instances[:self.NUM_INSTANCES]

    def process(self, instance, plugin):
        if self.SLEEP_DURATION:
            log.info("Pretending it takes %s seconds "
                     "to complete.." % self.SLEEP_DURATION)

        increment_sleep = self.SLEEP_DURATION / 3.0

        time.sleep(increment_sleep)
        log.info("Running first pass..")

        time.sleep(increment_sleep)
        log.info("Almost done..")

        time.sleep(increment_sleep)
        log.info("Completed successfully!")

        return True


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
        raise ValueError("An existing service was found: %s, "
                         "use deregister_service to remove it"
                         % type(EndpointService._current).__name__)
    EndpointService._current = service()
    log.info("Registering: %s" % service)


def deregister_service(service=None):
    if service is None or service is EndpointService._current:
        EndpointService._current = None
    else:
        raise ValueError("Could not deregister service")
