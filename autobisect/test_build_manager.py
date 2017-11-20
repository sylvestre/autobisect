import configparser
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

from .build_manager import BuildManager, DatabaseManager
from .config import BisectionConfig

class TestCase(unittest.TestCase):

    if sys.version_info.major == 2:

        def assertRegex(self, *args, **kwds):
            return self.assertRegexpMatches(*args, **kwds)

        def assertRaisesRegex(self, *args, **kwds):
            return self.assertRaisesRegexp(*args, **kwds)


def _create_test_config(fname, storage_path):
    with open(fname, 'w') as out_fp:
        out_fp.write('[autobisect]\n')
        out_fp.write('storage-path: %s\n' % storage_path)
        out_fp.write('persist: true\n')
        out_fp.write('persist-limit: 30000\n')


class DatabaseManagerTests(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='dbm_test_')

    def tearDown(self):
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_01(self):
        'test simple DatabaseManager'
        db_file = os.path.join(self.tmpdir, 'a.db')
        self.assertFalse(os.path.isfile(db_file))
        # create new db
        db = DatabaseManager(db_file)
        db.close()
        self.assertTrue(os.path.isfile(db_file))
        # open existing db
        db = DatabaseManager(db_file)
        try:
            res = db.cur.execute('SELECT name FROM sqlite_master WHERE type="table";')
            tables = [name for tbl in res.fetchall() for name in tbl]  # flatten list of tuples
        finally:
            db.close()  # triggers calling close() 2x, one here and once on delete
        self.assertIn('download_queue', tables)
        self.assertIn('in_use', tables)


class BisectionConfigTests(TestCase):
    
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='bc_test_')

    def tearDown(self):
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_01(self):
        'test simple BisectionConfig'
        test_ini = os.path.join(self.tmpdir, 'test.ini')
        _create_test_config(test_ini, self.tmpdir)
        bc = BisectionConfig(config_file=test_ini)
        self.assertTrue(bc.persist)
        self.assertEqual(bc.persist_limit, 30000 * 1024 * 1024)
        self.assertEqual(bc.store_path, self.tmpdir)
        self.assertEqual(bc.db_path, os.path.join(bc.store_path, 'autobisect.db'))

    def test_02(self):
        'test BisectionConfig with missing .ini file'
        with self.assertRaisesRegex(IOError, 'Invalid configuration file specified'):
            BisectionConfig(config_file='missing.ini')


class BuildManagerTests(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='bm_test_')
        self.test_ini = os.path.join(self.tmpdir, 'test.ini')
        _create_test_config(self.test_ini, self.tmpdir)

    def tearDown(self):
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_01(self):
        'test simple BuildManager'
        build_string = "foo111"
        bm = BuildManager(self.test_ini, build_string)
        self.assertEqual(bm.build_prefix, build_string)
        self.assertTrue(os.path.isdir(bm.build_dir))
        self.assertEqual(bm.current_build_size, 0)
        self.assertFalse(bm.enumerate_builds())
        bm.remove_old_builds()

