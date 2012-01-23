import itertools
from operator import attrgetter
from tempfile import NamedTemporaryFile

from penchy.compat import unittest, write
from penchy.jobs.filters import DacapoHarness, WrongInputError
from penchy.tests.util import get_json_data


class DacapoHarnessTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        d = get_json_data('DacapoHarnessFilter')
        cls.multiple_iterations = d['multiple_iterations']
        cls.single_iterations = d['single_iterations']
        cls.failed_single = d['failed_single']
        cls.wrong_input = d['wrong_input']

    def setUp(self):
        super(DacapoHarnessTest, self).setUp()
        self.d = DacapoHarness()

        self.mi = write_to_tempfiles(DacapoHarnessTest.multiple_iterations)
        self.si = write_to_tempfiles(DacapoHarnessTest.single_iterations)
        self.failed = write_to_tempfiles(DacapoHarnessTest.failed_single)
        self.wrong_input = write_to_tempfiles(DacapoHarnessTest.wrong_input)

    def tearDown(self):
        for f in itertools.chain(self.mi, self.si, self.failed, self.wrong_input):
            f.close()

    def test_multi_iteration_path(self):
        invocations = len(self.mi)
        exit_codes = [0] * invocations
        stderr = map(attrgetter('name'), self.mi)
        self.d.run(exit_code=exit_codes, stderr=stderr)

        self._assert_correct_out(invocations)

    def test_single_iteration_path(self):
        invocations = len(self.si)
        exit_codes = [0] * invocations
        stderr = map(attrgetter('name'), self.si)
        self.d.run(exit_code=exit_codes, stderr=stderr)
        self._assert_correct_out(invocations)

    def test_failed(self):
        invocations = len(self.failed)
        exit_codes = [0] * invocations
        stderr = map(attrgetter('name'), self.failed)
        self.d.run(exit_code=exit_codes, stderr=stderr)
        self.assertListEqual(self.d.out['failures'], [1] * invocations)

    def test_wrong_input(self):
        stderr = map(attrgetter('name'), self.wrong_input)
        for e in stderr:
            with self.assertRaises(WrongInputError):
                self.d.run(exit_code=[0], stderr=[e])

    def _assert_correct_out(self, invocations):
        self.assertSetEqual(set(self.d.out), self.d._output_names)
        self.assertEqual(len(self.d.out['failures']), invocations)
        self.assertEqual(len(self.d.out['times']), invocations)
        self.assertEqual(len(self.d.out['valid']), invocations)


def write_to_tempfiles(data):
    files = []
    for d in data:
        # itentially not closing, do in tearDown
        f = NamedTemporaryFile(prefix='penchy')
        write(f, d)
        f.seek(0)
        files.append(f)

    return files
