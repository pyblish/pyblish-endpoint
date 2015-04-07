import os
import sys

# Expose vendor packages to PYTHONPATH
repo_dir = os.path.dirname(__file__)
package_dir = os.path.join(repo_dir, "pyblish_endpoint")
vendor_dir = os.path.join(package_dir, "vendor")
sys.path.insert(0, vendor_dir)

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
    argv.extend(['--exclude=vendor', '--with-doctest', '--verbose'])
    nose.main(argv=argv)
