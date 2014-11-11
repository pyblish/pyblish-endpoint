import os
import sys


def register_vendor():
    package_dir = os.path.dirname(__file__)
    vendor_dir = os.path.join(package_dir, "vendor")
    sys.path.insert(0, vendor_dir)
