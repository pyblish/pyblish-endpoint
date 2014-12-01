import os
import sys

# Expose Pyblish to PYTHONPATH
path = os.path.dirname(__file__)
sys.path.insert(0, path)

import nose

try:
    import mock
except ImportError:
    print "Test-suite requires mock and nose libraries"

# Mock host-dependent modules, as they aren't available
# outside of Maya.
sys.modules['PyQt5'] = mock.Mock()

if __name__ == '__main__':
    argv = sys.argv[:]
    argv.extend(['--exclude=vendor', '--with-doctest'])
    nose.main(argv=argv)
