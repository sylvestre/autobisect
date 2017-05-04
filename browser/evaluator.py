#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import logging
import os
import shutil
import subprocess
import time

from ffpuppet import FFPuppet

log = logging.getLogger('browser-bisect')


class BisectBrowser:
    def __init__(self, args):
        self.repo_dir = args.repo_dir
        self.build_dir = args.build_dir
        self.start_repo = args.start_rev
        self.end_repo = args.end_rev
        self.testcase = args.testcase

        self.moz_config = args.mozconfig

        # FFPuppet arguments
        self.binary = os.path.join(self.build_dir, 'firefox')
        self.extension = args.extension
        self.launch_timeout = args.timeout
        self.prefs = args.prefs
        self.memory = args.memory
        self.gdb = args.gdb
        self.valgrind = args.valgrind
        self.windbg = args.windbg
        self.xvfb = args.xvfb

    def try_compile(self):
        assert os.path.isdir(self.repo_dir)
        assert os.path.isfile(self.moz_config)

        env = os.environ.copy()
        env['MOZCONFIG'] = self.moz_config
        env['MOZ_OBJDIR'] = self.build_dir

        mach = os.path.join(self.repo_dir, 'mach')

        try:
            subprocess.check_call([mach, 'build'], cwd=self.repo_dir, env=env, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            return False

        if not os.path.exists(self.build_dir):
            return False

        return True

    def test_rev(self, rev):
        if os.path.exists(self.build_dir):
            log.info('Clobbering build dir: {0}'.format(self.build_dir))
            shutil.rmtree(self.build_dir)

        log.info('Attempting to compile revision: {0}'.format(rev))
        if not self.try_compile():
            return 'skip'
        else:
            log.info('Compilation succeeded!')

        log.info('Attempting to launch browser with testcase...')
        result = self.launch()

        # Why sleep?
        time.sleep(8)

        return result

    def launch(self):
        ffp = FFPuppet(
            use_gdb=self.gdb,
            use_valgrind=self.valgrind,
            use_windbg=self.windbg,
            use_xvfb=self.xvfb)

        try:
            log.info('Attempting to launch browser with testcase: {0}'.format(self.testcase))
            ffp.launch(
                self.binary,
                location=os.path.abspath(self.testcase),
                launch_timeout=self.timeout,
                memory_limit=self.memory,
                prefs_js=self.prefs,
                extension=self.extension)

            return_code = ffp.wait(self.timeout)

            status = return_code or 'Timeout'
            log.info('Browser execution status: {0}'.format(status))
        finally:
            ffp.close()
            ffp.clean_up()

        return return_code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source', required=True, action='store', help='Path of Mozilla source')
    parser.add_argument('-b', '--build', required=True, action='store', help='Path to store Mozilla build')
    parser.add_argument('-c', '--config', required=True, action='store', help='Path to .mozconfig file')
    parser.add_argument('-r', '--rev', required=True, action='store', help='Revision to test')

    args = parser.parse_args()
    bisector = BisectBrowser()
    bisector.test_rev(args.source, args.build, args.config, args.rev)


if __name__ == '__main__':
    main()
