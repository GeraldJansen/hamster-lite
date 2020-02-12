from hamster_lite.lib import default_logger


logger = default_logger(__name__)

try:
    # defs.py is created by waf from defs.py.in
    from hamster_lite import defs
    __version__ = defs.VERSION
    installed = True
except ImportError:
    # if defs is not there, we are running from sources
    from subprocess import getstatusoutput
    rc, output = getstatusoutput("git describe --tags --always --dirty=+")
    __version__ = "" if rc else output + " (uninstalled)"
    installed = False
    del getstatusoutput, rc, output
