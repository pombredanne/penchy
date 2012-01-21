from tempfile import TemporaryFile
from contextlib import contextmanager

from penchy.compat import unittest, nested


class NestedTest(unittest.TestCase):
    def test_reraising_exception(self):
        e = Exception('reraise this')
        with self.assertRaises(Exception) as raised:
            with nested(TemporaryFile(), TemporaryFile()) as (a, b):
                raise e

        self.assertEqual(raised.exception, e)

    def test_raising_on_exit(self):
        @contextmanager
        def raising_cm(exception):
            yield
            raise exception

        on_exit = Exception('throw on exit')
        with self.assertRaises(Exception) as raised:
            with nested(raising_cm(on_exit)):
                pass
        self.assertEqual(raised.exception, on_exit)
