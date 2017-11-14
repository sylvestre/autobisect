#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import, division, print_function

import argparse
import logging
import os
import re
import time
from datetime import datetime, timedelta

from core.bisect import Bisector

log = logging.getLogger('autobisect')


class ExpandPath(argparse.Action):
    """
    Expand user and relative-paths
    """
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Autobisection tool for Mozilla Firefox and Spidermonkey',
        usage='%(prog)s <command> [options]')

    global_args = argparse.ArgumentParser(add_help=False)
    global_args.add_argument('testcase', action=ExpandPath, help='Path to testcase')

    boundary_args = global_args.add_argument_group('boundary arguments (YYYY-MM-DD or SHA1 revision')
    boundary_args.add_argument('--start', default=(datetime.utcnow()-timedelta(days=364)).strftime('%Y-%m-%d'),
                               help='Start revision (default: earliest available TC build)')
    boundary_args.add_argument('--end', default=datetime.utcnow().strftime('%Y-%m-%d'),
                               help='End revision (default: latest available TC build)')

    bisection_args = global_args.add_argument_group('bisection arguments')
    bisection_args.add_argument('--count', type=int, default=1, help='Number of times to evaluate testcase (per build)')
    bisection_args.add_argument('--find-fix', action='store_true', help='Indentify fix date')
    bisection_args.add_argument('--verify', action='store_true', help='Verify boundaries')
    bisection_args.add_argument('--config', action=ExpandPath, help='Path to optional config file')

    branch_args = global_args.add_argument_group('Branch')
    branch_selector = branch_args.add_mutually_exclusive_group()
    branch_selector.add_argument('--inbound', action='store_const', const='inbound', dest='branch',
                                 help='Download from mozilla-inbound')
    branch_selector.add_argument('--central', action='store_const', const='central', dest='branch',
                                 help='Download from mozilla-central (default)')
    branch_selector.add_argument('--release', action='store_const', const='release', dest='branch',
                                 help='Download from mozilla-release')
    branch_selector.add_argument('--beta', action='store_const', const='beta', dest='branch',
                                 help='Download from mozilla-beta')
    branch_selector.add_argument('--esr', action='store_const', const='esr52', dest='branch',
                                 help='Download from mozilla-esr52')

    build_args = global_args.add_argument_group('build arguments')
    build_args.add_argument('--asan', action='store_true', help='Test asan builds')
    build_args.add_argument('--debug', action='store_true', help='Test debug builds')
    build_args.add_argument('--fuzzing', action='store_true', help='Test --enable-fuzzing builds')
    build_args.add_argument('--coverage', action='store_true', help='Test --coverage builds')
    build_args.add_argument('--32', dest='arch_32', action='store_true',
                            help='Test 32 bit version of browser on 64 bit system.')

    subparsers = parser.add_subparsers(dest='target')
    firefox_sub = subparsers.add_parser('firefox', parents=[global_args], help='Perform bisection for Firefox builds')
    ffp_args = firefox_sub.add_argument_group('launcher arguments')
    ffp_args.add_argument('--timeout', type=int, default=60,
                          help='Maximum iteration time in seconds (default: %(default)s)')
    ffp_args.add_argument('--launch-timeout', type=int, default=300,
                          help='Maximum launch time in seconds (default: %(default)s)')
    ffp_args.add_argument('--ext', action=ExpandPath, help='Path to fuzzPriv extension')
    ffp_args.add_argument('--prefs', action=ExpandPath, help='Path to preference file')
    ffp_args.add_argument('--profile', action=ExpandPath, help='Path to profile directory')
    ffp_args.add_argument('--memory', type=int, help='Process memory limit in MBs')
    ffp_args.add_argument('--gdb', action='store_true', help='Use GDB')
    ffp_args.add_argument('--valgrind', action='store_true', help='Use valgrind')
    ffp_args.add_argument('--xvfb', action='store_true', help='Use xvfb (Linux only)')

    js_args = subparsers.add_parser('js', parents=[global_args], help='Perform bisection for SpiderMonkey builds')
    js_args.add_argument('--foo', required=True, help='Foo')

    args = parser.parse_args()

    if not re.match(r'^[0-9[a-f]{12,40}$|^[0-9]{4}-[0-9]{2}-[0-9]{2}$', args.start):
        parser.error('Invalid start value supplied')
    if not re.match(r'^[0-9[a-f]{12,40}$|^[0-9]{4}-[0-9]{2}-[0-9]{2}$', args.end):
        parser.error('Invalid end value supplied')

    if args.branch is None:
        args.branch = 'central'

    return args


def main(args):
    bisector = Bisector(args)
    start_time = time.time()
    bisector.bisect()
    end_time = time.time()
    elapsed = timedelta(seconds=(int(end_time - start_time)))
    log.info('Bisection completed in: %s' % elapsed)


if __name__ == '__main__':
    log_level = logging.INFO
    log_fmt = "[%(asctime)s] %(levelname).4s: %(message)s"
    if bool(os.getenv("DEBUG")):
        log_level = logging.DEBUG
        log_fmt = "%(levelname)s %(name)s [%(asctime)s] %(message)s"
    logging.basicConfig(format=log_fmt, datefmt="%Y-%m-%d %H:%M:%S", level=log_level)

    main(parse_arguments())
