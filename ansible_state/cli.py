

"""
Usage:
    ansible-state [options] monitor <current-state.yml> <rules.yml>
    ansible-state [options] update-desired-state <new-state.yml>
    ansible-state [options] update-system-state <new-state.yml>

Options:
    -h, --help              Show this page
    --debug                 Show debug logging
    --verbose               Show verbose logging
    --explain               Do not run the rules, only print the ones that would run.
    --ask-become-pass       Ask for the become password
    --project-src=<d>       Copy project files this directory [default: .]
    --inventory=<i>         Inventory to use
    --cwd=<c>               Change working directory on start
"""

from gevent import monkey
monkey.patch_all()
import logging
import sys
import os
from docopt import docopt
FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
logging.basicConfig(filename='ansible_state.log', level=logging.DEBUG, format=FORMAT)  # noqa
logging.debug('Logging started')
logging.debug('Loading runner')
logging.debug('Loaded runner')

FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
logging.basicConfig(filename='ansible_fsm.log', level=logging.DEBUG, format=FORMAT)  # noqa

logger = logging.getLogger('cli')


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parsed_args = docopt(__doc__, args)
    if parsed_args['--debug']:
        logging.basicConfig(level=logging.DEBUG)
    elif parsed_args['--verbose']:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    if parsed_args['--cwd']:
        os.chdir(parsed_args['--cwd'])

    if parsed_args['monitor']:
        return ansible_state_monitor(parsed_args)
    elif parsed_args['update-desired-state']:
        return ansible_state_update_desired_state(parsed_args)
    elif parsed_args['update-system-state']:
        return ansible_state_update_system_state(parsed_args)
    else:
        assert False, 'Update the docopt'


def inventory(parsed_args):

    if not parsed_args['--inventory']:
        return "[all]\nlocalhost ansible_connection=local\n"

    with open(parsed_args['--inventory']) as f:
        return f.read()
