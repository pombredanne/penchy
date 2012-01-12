import os
import unittest2

from tempfile import NamedTemporaryFile

from penchy import util


class ClasspathTest(unittest2.TestCase):

    def test_valid_options(self):
        expected = 'foo:bar:baz'
        options = ['-cp', expected]
        self.assertEquals(util.extract_classpath(options), expected)
        expected = 'foo:bar:baz'
        options = ['-classpath', expected]
        self.assertEquals(util.extract_classpath(options), expected)

    def test_multiple_classpaths(self):
        expected = 'foo:bar:baz'
        options = ['-cp', 'com:org:de', '-cp', expected]
        self.assertEquals(util.extract_classpath(options), expected)

    def test_only_option(self):
        options = ['-cp']
        self.assertEquals(util.extract_classpath(options), '')


class TempdirTest(unittest2.TestCase):
    def test_change(self):
        cwd = os.getcwd()
        with util.tempdir():
            self.assertNotEquals(cwd, os.getcwd())
        self.assertEquals(cwd, os.getcwd())


class MiscTest(unittest2.TestCase):
    def test_sha1sum(self):
        with NamedTemporaryFile(delete=False) as tf:
            tf.write('sha1 checksum test')
            tf.flush()
            self.assertEquals(util.sha1sum(tf.name),
                    '14eb73d6e6e404471f7c71dc2ad114609c51c579')
