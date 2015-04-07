import time
import logging

import tests.lib


log = logging.getLogger("endpoint")


class MockService(tests.lib.TestService):
    """Service for testing"""

    SLEEP_DURATION = 0

    def process(self, *args, **kwargs):
        self.sleep()
        return super(MockService, self).process(*args, **kwargs)

    def sleep(self):
        if self.SLEEP_DURATION:
            log.info("Pretending it takes %s seconds "
                     "to complete.." % self.SLEEP_DURATION)

            time.sleep(self.SLEEP_DURATION)
