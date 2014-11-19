import logging
from .version import *

# Initialise default logger
formatter = logging.Formatter("%(levelname)s %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)

log = logging.getLogger("endpoint")
log.addHandler(handler)
log.setLevel(logging.WARNING)
