import os
import sys
import hashlib
import random
from tempfile import NamedTemporaryFile

from penchy import util
from penchy.compat import unittest, write, update_hasher, StringIO


class TempdirTest(unittest.TestCase):
    def test_change(self):
        cwd = os.getcwd()
        with util.tempdir(delete=True):
            self.assertNotEqual(cwd, os.getcwd())
        self.assertEqual(cwd, os.getcwd())


class HashTest(unittest.TestCase):
    def setUp(self):
        self.paths_to_delete = []

    def tearDown(self):
        for f in self.paths_to_delete:
            os.remove(f)

    def test_sha1sum(self):
        text = 'sha1 checksum test'
        hasher = hashlib.sha1()
        with NamedTemporaryFile(delete=False) as tf:
            write(tf, text)
            tf.flush()
            self.assertEqual(util.sha1sum(tf.name),
                             update_hasher(hasher, text).hexdigest())
            self.paths_to_delete.append(tf.name)


class MemoizedTest(unittest.TestCase):
    def test_cache(self):
        @util.memoized
        def func():
            return random.randint(0, 1000)

        self.assertEqual(func(), func())

    def test_docstring(self):
        @util.memoized
        def func():
            """this is a docstring"""
            pass

        self.assertEqual(func.__doc__, "this is a docstring")

    def test_invalid_argument(self):
        @util.memoized
        def func(lst):
            return lst

        self.assertEqual(func([1, 2]), [1, 2])
        self.assertEqual(func([1, 2]), [1, 2])

    def test_kwargs_arguments(self):
        # using two different seeds guarantees we will get different values, at
        # least for these two
        random.seed(42)
        f = util.memoized(lambda n: random.randint(0, 1000))
        a = f(n=23)
        random.seed(23)
        b = f(n=23)
        self.assertEqual(a, b)


class MiscTest(unittest.TestCase):
    def test_make_bootstrap_client(self):
        with util.make_bootstrap_client() as bclient:
            self.assertTrue(os.path.exists(bclient.name))


class ImportTest(unittest.TestCase):
    def test_load_config(self):
        i = 5
        self.assertFalse('config' in sys.modules)
        with NamedTemporaryFile() as tf:
            # save for writing after close, assures file does not exist
            fname = tf.name
            write(tf, 'foo = %s' % i)
            write(tf, os.linesep)
            tf.flush()
            config = util.load_config(tf.name)
            self.assertEqual(config.foo, i)

        self.assertTrue('config' in sys.modules)
        with self.assertRaises(IOError):
            util.load_config(fname)

    def test_load_job(self):
        j = 'world dominance'
        with NamedTemporaryFile() as tf:
            write(tf, 'job = "%s"' % j)
            write(tf, os.linesep)
            tf.flush()
            job = util.load_job(tf.name)
            self.assertEqual(job.job, j)

    def test_load_job_without_config(self):
        if 'config' in sys.modules:
            del sys.modules['config']

        with self.assertRaises(AssertionError):
            self.test_load_job()

    def test_get_config_attrib(self):
        class Config:
            def __init__(self):
                self.foo = 'bar'
        c = Config()
        self.assertEqual(util.get_config_attribute(c, 'foo', 'yep'), 'bar')
        self.assertEqual(util.get_config_attribute(c, 'bar', 'yep'), 'yep')


class DieTest(unittest.TestCase):
    def test_dying(self):
        io = StringIO()
        s = 'Die!'
        err, sys.stderr = sys.stderr, io
        with self.assertRaises(SystemExit):
            util.die(s)
        io.seek(0)
        self.assertEqual(io.read(), s + os.linesep)
        sys.stderr = err


class UnifyTest(unittest.TestCase):
    def test_unify(self):
        self.assertEqual(util.unify([1, 2, 2, 3, 3]), [1, 2, 3])
