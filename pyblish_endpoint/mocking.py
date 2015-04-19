import time
import logging
import random

import tests.lib


log = logging.getLogger("endpoint")


class MockService(tests.lib.TestService):
    SLEEP_DURATION = 0


def sleeper(func):
    def wrapper(*args, **kwargs):
        duration = random.random() * MockService.SLEEP_DURATION
        time.sleep(duration)
        return func(*args, **kwargs)
    return wrapper


for plugin in tests.lib.PLUGINS:
    plugin.process_instance = sleeper(plugin.process_instance)
    plugin.process_context = sleeper(plugin.process_context)
