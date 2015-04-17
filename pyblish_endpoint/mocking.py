import time
import logging
import random

import tests.lib


log = logging.getLogger("endpoint")


class MockService(tests.lib.TestService):
    """Service for testing"""

    SLEEP_DURATION = 0

    @classmethod
    def sleep(cls):
        duration = random.random() * cls.SLEEP_DURATION
        if duration:
            log.info("Pretending it takes %s ms "
                     "to complete.." % duration * 1000)

            time.sleep(duration)


def sleeper(func):
    def wrapper(*args, **kwargs):
        MockService.sleep()
        return func(*args, **kwargs)
    return wrapper


for plugin in tests.lib.PLUGINS:
    plugin.process_instance = sleeper(plugin.process_instance)
    plugin.process_context = sleeper(plugin.process_context)
