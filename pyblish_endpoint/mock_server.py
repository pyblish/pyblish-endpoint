"""Mock-server of Endpoint

The purpose of this module is to emulate an externally running host
with Endpoint booted up. For example, Endpoint is typically running
from within Autodesk Maya; but Maya is a heavy process and takes a
few seconds to boot up. During development, it can be tedious to
boot/reboot a heavy process; instead, you can run the mock_server
which will attempt to emulate what would happen if Endpoint did
indeed run from within a host.

Mocked behaviour:
    - A fixed number of instances
    - Processing takes a random amount of time

"""

import time
import logging

# Local library
import service
import server

log = logging.getLogger()

# Output logging to console.
formatter = logging.Formatter("%(levelname)-8s %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)

log.addHandler(handler)
log.setLevel(logging.DEBUG)


class EndpointService(service.EndpointService):
    def instances(self):
        instances = [
            {
                "instance": "Peter01",
                "objName": "Peter01:pointcache_SEL",
                "family": "napoleon.asset.rig"
            },
            {
                "instance": "Richard05",
                "objName": "Richard05:pointcache_SEL",
                "family": "napoleon.animation.rig"
            }
        ]

        return instances

    def process(self, instance, plugin, sleep=5):
        log.info("Pretending it takes 5 seconds to complete..")

        increment_sleep = sleep / 3.0

        time.sleep(increment_sleep)
        log.info("Running first pass..")

        time.sleep(increment_sleep)
        log.info("Almost done..")

        time.sleep(increment_sleep)
        log.info("Completed successfully!")

        return True


def run():
    import os
    os.environ["ENDPOINT_PORT"] = "6000"

    service.register_service(EndpointService)
    server.app.run(debug=True, port=6000)


if __name__ == '__main__':
    run()
