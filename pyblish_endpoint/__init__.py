import logging
from .version import *

# Initialise default logger
log = logging.getLogger("endpoint")
log.propagate = True
