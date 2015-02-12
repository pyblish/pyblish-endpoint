import os
import sys
import logging
from .version import *

# Register vendor packages
package_dir = os.path.dirname(__file__)
vendor_dir = os.path.join(package_dir, "vendor")
sys.path.insert(0, vendor_dir)

# Initialise default logger
# __formatter = logging.Formatter("%(levelname)s - %(message)s")
# __handler = logging.StreamHandler()
# __handler.setFormatter(__formatter)
# __log = logging.getLogger("endpoint")
# __log.propagate = True
# __log.handlers[:] = []
# __log.addHandler(__handler)
# __log.setLevel(logging.DEBUG)
