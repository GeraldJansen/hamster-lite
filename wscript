# -*- python -*-
from subprocess import getstatusoutput
rc, output = getstatusoutput("git describe --tags --always --dirty=+")
VERSION = '0.1.0' if rc else output
APPNAME = 'hamster-lite'
top = '.'
out = 'build'

import os
from waflib import Logs, Utils


def configure(conf):
    conf.load('gnu_dirs')  # for DATADIR

    conf.load('python')
    conf.check_python_version(minver=(3,4,0))

    conf.load('intltool')

    conf.env.ENABLE_NLS = 1
    conf.env.HAVE_BIND_TEXTDOMAIN_CODESET = 1

    conf.env.VERSION = VERSION
    conf.env.GETTEXT_PACKAGE = "hamster-lite"
    conf.env.PACKAGE = "hamster-lite"

    conf.recurse("help")


def options(opt):

    # the waf default value is /usr/local, which causes issues (e.g. #309)
    # opt.parser.set_defaults(prefix='/usr') did not update the help string,
    # hence need to replace the whole option
    opt.parser.remove_option('--prefix')
    default_prefix = '/usr'
    opt.add_option('--prefix', dest='prefix', default=default_prefix,
                   help='installation prefix [default: {}]'.format(default_prefix))


def build(bld):
    bld.install_as('${BINDIR}/hamster-lite', "src/hamster-lite", chmod=Utils.O755)

    bld.install_files('${PREFIX}/share/bash-completion/completion',
                      'src/hamster-lite.bash')

    bld(features='py',
        source=bld.path.ant_glob('src/**/*.py'),
        install_from='src')

    # set correct flags in defs.py
    bld(features="subst",
        source="src/hamster_lite/defs.py.in",
        target="src/hamster_lite/defs.py",
        install_path="${PYTHONDIR}/hamster_lite"
        )

    bld.recurse("po data help")


    def update_icon_cache(ctx):
        """Update the gtk icon cache."""
        if ctx.cmd == "install":
            # adapted from the previous waf gnome.py
            icon_dir = os.path.join(ctx.env.DATADIR, 'icons/hicolor')
            cmd = 'gtk-update-icon-cache -q -f -t {}'.format(icon_dir)
            err = ctx.exec_command(cmd)
            if err:
                Logs.warn('The following  command failed:\n{}'.format(cmd))
            else:
                Logs.pprint('YELLOW', 'Successfully updated GTK icon cache')


    bld.add_post_fun(update_icon_cache)
