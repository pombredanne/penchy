import itertools
import json
import os
import tempfile
from numpy import average, std
from numpy.random import random_integers, random_sample
from tempfile import NamedTemporaryFile

from penchy.compat import unittest, write
from penchy.jobs.filters import *
from penchy.jobs.typecheck import Types
from penchy.util import tempdir
from penchy.tests.util import get_json_data, make_system_composition


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
        for f in itertools.chain(self.mi, self.si, self.failed,
                                 self.wrong_input):
            f.close()

    def test_multi_iteration_path(self):
        invocations = len(self.mi)
        stderr = [i.name for i in self.mi]
        self.d.run(stderr=stderr)

        self._assert_correct_out(invocations)

    def test_single_iteration_path(self):
        invocations = len(self.si)
        stderr = [i.name for i in self.si]
        self.d.run(stderr=stderr)
        self._assert_correct_out(invocations)

    def test_failed(self):
        invocations = len(self.failed)
        stderr = [i.name for i in self.failed]
        self.d.run(stderr=stderr)
        self.assertListEqual(self.d.out['failures'], [1] * invocations)

    def test_wrong_input(self):
        stderr = [i.name for i in self.wrong_input]
        for e in stderr:
            with self.assertRaises(WrongInputError):
                self.d.run(stderr=[e])

    def _assert_correct_out(self, invocations):
        self.assertSetEqual(set(self.d.out), self.d._output_names)
        self.assertEqual(len(self.d.out['failures']), invocations)
        self.assertEqual(len(self.d.out['times']), invocations)
        self.assertEqual(len(self.d.out['valid']), invocations)


class HProfCpuTimesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        h = get_json_data('HProfCpuTimesFilter')
        cls.single_iterations = h['single_iterations']
        cls.wrong_input = h['wrong_input']

    def setUp(self):
        super(HProfCpuTimesTest, self).setUp()
        self.h = HProfCpuTimes()

        self.si = write_to_tempfiles(HProfCpuTimesTest.single_iterations)
        self.wrong_input = write_to_tempfiles(HProfCpuTimesTest.wrong_input)

    def tearDown(self):
        for f in itertools.chain(self.si, self.wrong_input):
            f.close()

    def test_single_iteration_path(self):
        invocations = len(self.si)
        hprof_file = [i.name for i in self.si]
        self.h.run(hprof=hprof_file)
        self._assert_correct_out(invocations)

    def test_wrong_input(self):
        hprof_files = [i.name for i in self.wrong_input]
        for hprof_file in hprof_files:
            with self.assertRaises(WrongInputError):
                self.h.run(hprof=[hprof_file])

    def _assert_correct_out(self, invocations):
        self.assertSetEqual(set(self.h.out), self.h._output_names)
        for k in self.h.out.keys():
            self.assertEqual(len(self.h.out[k]), invocations)


class TamiflexTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        h = get_json_data('TamiflexFilter')
        cls.single_iterations = h['single_iterations']
        cls.wrong_input = h['wrong_input']

    def setUp(self):
        super(TamiflexTest, self).setUp()
        self.h = Tamiflex()

        self.si = write_to_tempfiles(TamiflexTest.single_iterations)
        self.wrong_input = write_to_tempfiles(TamiflexTest.wrong_input)

    def tearDown(self):
        for f in itertools.chain(self.si, self.wrong_input):
            f.close()

    def test_single_iteration_path(self):
        invocations = len(self.si)
        ref_log = [i.name for i in self.si]
        self.h.run(reflection_log=ref_log)
        self._assert_correct_out(invocations)

    def test_wrong_input(self):
        ref_logs = [i.name for i in self.wrong_input]
        for ref_log in ref_logs:
            with self.assertRaises(WrongInputError):
                self.h.run(reflection_log=[ref_log])

    def _assert_correct_out(self, invocations):
        self.assertSetEqual(set(self.h.out), self.h._output_names)
        for k in self.h.out.keys():
            self.assertEqual(len(self.h.out[k]), invocations)


def write_to_tempfiles(data):
    files = []
    for d in data:
        # itentionally not closing, do in tearDown
        f = NamedTemporaryFile(prefix='penchy')
        write(f, d)
        f.seek(0)
        files.append(f)

    return files


class HProfTest(unittest.TestCase):
    def test_wrong_outputs(self):
        with self.assertRaises(ValueError):
            HProf(outputs=Types(('a', list, int), ('b', list, int)),
                  start_marker='', end_marker='',
                  skip=1, data_re=None, start_re=None)


class ExtractTest(unittest.TestCase):
    def setUp(self):
        self.results = {1: {'a': 42,
                            'b': 32},
                        2: {'b': 0,
                            'c': 21}}

    def test_implicit(self):
        f = Extract('a', 'b')
        f._run(results=self.results)
        self.assertEqual(f.out, {'a': 42, 'b': 32})

    def test_explicit(self):
        f = Extract((1, 'a'), (2, 'b'))
        f._run(results=self.results)
        self.assertEqual(f.out, {'a': 42, 'b': 0})

    def test_implicit_fail(self):
        f = Extract('a', 'd')
        with self.assertRaises(WrongInputError):
            f._run(results=self.results)

    def test_explicit_fail_column(self):
        f = Extract((1, 'a'), (2, 'd'))
        with self.assertRaises(WrongInputError):
            f._run(results=self.results)

    def test_explicit_fail_composition(self):
        f = Extract((1, 'a'), (3, 'c'))
        with self.assertRaises(WrongInputError):
            f._run(results=self.results)

    def test_no_arguments(self):
        with self.assertRaises(ValueError):
            Extract()

    def test_malformed_argument(self):
        with self.assertRaises(ValueError):
            Extract('a', (1, 'a', 'b'))


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.results = {1: {'a': 42,
                            'b': 32},
                        2: {'b': 0,
                            'c': 21}}

    def test_implicit(self):
        f = Merge(('col1', 'col2'), [('a', Value('id1')), ('b', Value('id2'))])
        f._run(results=self.results)
        self.assertEqual(f.out, {'col1': [42, 32], 'col2': ['id1', 'id2']})

    def test_explicit(self):
        f = Merge(('col1', 'col2'), [(1, 'a', Value('id1')), (2, 'b', Value('id2'))])
        f._run(results=self.results)
        self.assertEqual(f.out, {'col1': [42, 0], 'col2': ['id1', 'id2']})

    def test_implicit_fail(self):
        f = Merge(('col1', 'col2'), [('a', Value('id1')), ('d', Value('id2'))])
        with self.assertRaises(WrongInputError):
            f._run(results=self.results)

    def test_explicit_fail_column(self):
        f = Merge(('col1', 'col2'), [(1, 'a', Value('id1')), (2, 'd', Value('id2'))])
        with self.assertRaises(WrongInputError):
            f._run(results=self.results)

    def test_explicit_fail_composition(self):
        f = Merge(('col1', 'col2'), [(1, 'a', Value('id1')), (3, 'c', Value('id2'))])
        with self.assertRaises(WrongInputError):
            f._run(results=self.results)

    def test_malformed_arguments_type(self):
        with self.assertRaises(ValueError):
            Merge(('col1', 'col2'), [(1, 42, Value('id1')), (2, 'c', Value('id2'))])

    def test_malformed_arguments_length_too_small(self):
        with self.assertRaises(ValueError):
            Merge(('col1', 'col2'), [(1, 'b'), (2, 'c', Value('id2'))])

    def test_malformed_arguments_length_too_big(self):
        with self.assertRaises(ValueError):
            Merge(('col1', 'col2'), [(1, 'b', Value('id1'), Value('foo')), (2, 'c', Value('id2'))])


class MergingReceiveTest(unittest.TestCase):
    def setUp(self):
        environment = {'receive': lambda: self.results}
        self.kwargs = {':environment:' : environment}
        self.results = {1: {'a': 42,
                            'b': 32},
                        2: {'b': 0,
                            'c': 21}}

    def test_implicit(self):
        f = MergingReceive(('col1', 'col2'), [('a', Value('id1')), ('b', Value('id2'))])
        f._run(**self.kwargs)
        self.assertEqual(f.out, {'col1': [42, 32], 'col2': ['id1', 'id2']})

    def test_explicit(self):
        f = MergingReceive(('col1', 'col2'), [(1, 'a', Value('id1')), (2, 'b', Value('id2'))])
        f._run(**self.kwargs)
        self.assertEqual(f.out, {'col1': [42, 0], 'col2': ['id1', 'id2']})

    def test_implicit_fail(self):
        f = MergingReceive(('col1', 'col2'), [('a', Value('id1')), ('d', Value('id2'))])
        with self.assertRaises(WrongInputError):
            f._run(**self.kwargs)

    def test_explicit_fail_column(self):
        f = MergingReceive(('col1', 'col2'), [(1, 'a', Value('id1')), (2, 'd', Value('id2'))])
        with self.assertRaises(WrongInputError):
            f._run(**self.kwargs)

    def test_explicit_fail_composition(self):
        f = MergingReceive(('col1', 'col2'), [(1, 'a', Value('id1')), (3, 'c', Value('id2'))])
        with self.assertRaises(WrongInputError):
            f._run(**self.kwargs)


class ExtractingReceiveTest(unittest.TestCase):
    def setUp(self):
        environment = {'receive': lambda: self.results}
        self.kwargs = {':environment:' : environment}
        self.results = {1: {'a': 42,
                            'b': 32},
                        2: {'b': 0,
                            'c': 21}}

    def test_implicit(self):
        f = ExtractingReceive('a', 'b')
        f._run(**self.kwargs)
        self.assertEqual(f.out, {'a': 42, 'b': 32})

    def test_explicit(self):
        f = ExtractingReceive((1, 'a'), (2, 'b'))
        f._run(**self.kwargs)
        self.assertEqual(f.out, {'a': 42, 'b': 0})

    def test_implicit_fail(self):
        f = ExtractingReceive('a', 'd')
        with self.assertRaises(WrongInputError):
            f._run(**self.kwargs)

    def test_explicit_fail_column(self):
        f = ExtractingReceive((1, 'a'), (2, 'd'))
        with self.assertRaises(WrongInputError):
            f._run(**self.kwargs)

    def test_explicit_fail_composition(self):
        f = ExtractingReceive((1, 'a'), (3, 'c'))
        with self.assertRaises(WrongInputError):
            f._run(**self.kwargs)


class SendTest(unittest.TestCase):
    def test_send(self):
        a = [1]
        f = Send()
        f._run(payload=42,
               **{':environment:' : {'send' : lambda data: a.__setitem__(0, data)}})
        self.assertEqual(a, [{'payload': 42}])


class StatisticRuntimeEvaluationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        t = get_json_data('StatisticRuntimeEvaluationFilter')
        cls.times = t['times']
        cls.expected = t['expected']

    def test_statistics(self):
        f = StatisticRuntimeEvaluation()
        keys = ['averages', 'maximals', 'minimals',
                'positive_deviations', 'negative_deviations']
        for times, results in zip(StatisticRuntimeEvaluationTest.times,
                                 StatisticRuntimeEvaluationTest.expected):
            # output is correctly cleaned up?
            self.assertDictEqual(f.out, {})
            f._run(times=times)
            # contains the right keys?
            self.assertItemsEqual(f.out.keys(), keys)
            for key in keys:
                for actual, expected in zip(f.out[key], results[key]):
                    self.assertAlmostEqual(actual, expected)
            f.reset()


class EvaluationTest(unittest.TestCase):

    def test_default_input(self):
        e = Evaluation(lambda input: {'result' : input})
        e._run(input=42)
        self.assertDictEqual(e.out, {'result' : 42})

    def test_missing_default_input(self):
        e = Evaluation(lambda x: None)
        with self.assertRaises(ValueError):
            e._run()

    def test_missing_input(self):
        e = Evaluation(lambda x: x, Types(('value', int)), Types(('value', int)))
        with self.assertRaises(ValueError):
            e._run()


class BackupTest(unittest.TestCase):
    def test_copy(self):
        s = "'tis a test string"
        with NamedTemporaryFile(delete=False) as f:
            path = f.name
            write(f, s)
        self.assertTrue(os.path.exists(path))
        backup_path = '/tmp/penchy-backup-test'
        b = BackupFile(backup_path)
        b.run(filename=path, **{':environment:' : {}})

        # did backup?
        with open(backup_path) as f:
            self.assertEqual(f.read(), s)

        # did not modify backuped file?
        with open(path) as f:
            self.assertEqual(f.read(), s)

        os.remove(path)
        os.remove(backup_path)

    def test_relative_copy(self):
        s = "'tis a test string"
        comp = make_system_composition()
        comp.node_setting.path = '/tmp'

        with NamedTemporaryFile(delete=False) as f:
            path = f.name
            write(f, s)
        self.assertTrue(os.path.exists(path))
        backup_file = 'penchy-backup-test'
        backup_path = os.path.join(comp.node_setting.path, backup_file)
        b = BackupFile(backup_file)
        b.run(filename=path, **{':environment:' : {'current_composition' : comp}})

        # did backup?
        with open(backup_path) as f:
            self.assertEqual(f.read(), s)

        # did not modify backuped file?
        with open(path) as f:
            self.assertEqual(f.read(), s)

        os.remove(path)
        os.remove(os.path.join(comp.node_setting.path, backup_path))

    def test_not_existing_path(self):
        # create unique not existing path
        with NamedTemporaryFile() as f:
            path = f.name

        b = BackupFile('/tmp/penchy-backup-test')
        with self.assertRaises(WrongInputError):
            b.run(filename=path, **{':environment:' : {}})


class SaveTest(unittest.TestCase):
    def test_save_relative(self):
        s = "'tis a test string"
        save_file = 'penchy-save-test'
        comp = make_system_composition()
        comp.node_setting.path = '/tmp'
        save_path = os.path.join(comp.node_setting.path, save_file)

        save = Save(save_file)
        save.run(data=s, **{':environment:' : {'current_composition': comp}})
        with open(save_path) as f:
            self.assertEqual(f.read(), s)

        os.remove(save_path)

    def test_save_absolute(self):
        s = "'tis a test string"
        save_path = '/tmp/penchy-save-test'
        save = Save(save_path)
        save.run(data=s, **{':environment:' : {}})
        with open(save_path) as f:
            self.assertEqual(f.read(), s)

        os.remove(save_path)


class ReadTest(unittest.TestCase):
    def test_read(self):
        s = "'tis a test string"
        with NamedTemporaryFile() as f:
            write(f, s)
            f.flush()

            r = Read('utf8')
            r.run(paths=[f.name])
            self.assertListEqual(r.out['data'], [s])


class ServerFlowSystemFilterTest(unittest.TestCase):
    def setUp(self):
        self.env = {
            'job' : 'no file',
            'current_composition' : None
        }

    def test_dump(self):
        numbers = [23, 42]
        strings = ['a', 'b', 'c']
        d = Dump()
        d._run(numbers=numbers, strings=strings, **{':environment:' : self.env})

        dump = json.loads(d.out['dump'])
        self.assertIn('job', dump['system'])
        self.assertNotIn('jvm', dump['system'])
        self.assertIn('numbers', dump['data'])
        self.assertIn('strings', dump['data'])
        self.assertItemsEqual(numbers, dump['data']['numbers'])
        self.assertItemsEqual(strings, dump['data']['strings'])

    def test_save_and_backup(self):
        data = "'tis the end"
        with tempdir(delete=True):
            s = Save('save')
            s._run(data=data, **{':environment:' : self.env})
            b = BackupFile('backup')
            b._run(filename='save', **{':environment:' : self.env})
            with open('save') as f:
                self.assertEqual(f.read(), data)
            with open('backup') as f:
                self.assertEqual(f.read(), data)


class MeanTest(unittest.TestCase):
    def test_against_numpy_integers(self):
        rnd = random_integers(-20, 20, 50)
        f = Mean()
        f._run(values=rnd)
        self.assertAlmostEqual(f.out['mean'], average(rnd))

    def test_against_numpy_floats(self):
        rnd = random_sample(20)
        f = Mean()
        f._run(values=rnd)
        self.assertAlmostEqual(f.out['mean'], average(rnd))


class StandardDeviationTest(unittest.TestCase):
    def test_against_numpy_integes(self):
        rnd = random_integers(-20, 20, 50)
        f = StandardDeviation(ddof=1)
        f._run(values=rnd)
        self.assertAlmostEqual(f.out['standard_deviation'], std(rnd, ddof=1))

    def test_against_numpy_floats(self):
        rnd = random_sample(20)
        f = StandardDeviation(ddof=1)
        f._run(values=rnd)
        self.assertAlmostEqual(f.out['standard_deviation'], std(rnd, ddof=1))


class SumTest(unittest.TestCase):
    def test_integers(self):
        rnd = random_integers(-20, 20, 50)
        f = Sum()
        f._run(values=rnd)
        self.assertEqual(f.out['sum'], sum(rnd))

    def test_against_numpy_floats(self):
        rnd = random_sample(20)
        f = Sum()
        f._run(values=rnd)
        self.assertAlmostEqual(f.out['sum'], sum(rnd))


class EnumerateTest(unittest.TestCase):
    def test_preserves_input(self):
        f = Enumerate()
        f._run(values=[1, 2, 3])
        self.assertEqual(f.out['values'], [1, 2, 3])

    def test_enumerate(self):
        f = Enumerate(start=3, step=2)
        f._run(values=['a', 'b', 'c'])
        self.assertEqual(f.out['numbers'], [3, 5, 7])


class UnpackTest(unittest.TestCase):
    def test_valid(self):
        f = Unpack()
        f._run(singleton=[1])
        self.assertEqual(f.out['result'], 1)

    def test_list_too_long(self):
        f = Unpack()
        with self.assertRaises(WrongInputError):
            f._run(singleton=[1, 2, 3])

    def test_list_too_short(self):
        f = Unpack()
        with self.assertRaises(WrongInputError):
            f._run(singleton=[])


class MapTest(unittest.TestCase):
    def test_idenity(self):
        identity = Evaluation(lambda x: {'x': x}, Types(('x', object)), Types(('x', object)))
        f = Map(identity)
        f._run(values=[1, 2, 3])
        self.assertEqual(f.out['values'], [1, 2, 3])

    def test_multidimensional(self):
        multi = Evaluation(lambda x: {'x': [x]}, Types(('x', object)), Types(('x', object)))
        f = Map(multi)
        f._run(values=[1, 2, 3])
        self.assertEqual(f.out['values'], [[1], [2], [3]])

    def test_wrong_inputs(self):
        wrong = Evaluation(lambda x, y: {'x': x}, Types(('x', object), ('y', object)), Types(('x', object)))
        with self.assertRaises(TypeCheckError):
            Map(wrong)

    def test_wrong_outputs(self):
        wrong = Evaluation(lambda x: {'x': x, 'y': x}, Types(('x', object)), Types(('x', object), ('y', object)))
        with self.assertRaises(TypeCheckError):
            Map(wrong)

    def test_with_all_arguments(self):
        identity = Evaluation(lambda c: {'d': c}, Types(('c', object)), Types(('d', object)))
        f = Map(identity, 'a', 'b', 'c', 'd')
        f._run(a=[1, 2, 3])
        self.assertEqual(f.out['b'], [1, 2, 3])


class DecorateTest(unittest.TestCase):
    def test_valid(self):
        f = Decorate("{0}")
        f._run(values=[1, 2, 3])
        self.assertEqual(f.out['values'], ["1", "2", "3"])

    def test_nothing_to_interplolate(self):
        f = Decorate("")
        f._run(values=[1, 2, 3])
        self.assertEqual(f.out['values'], ["", "", ""])


class DropFirstTest(unittest.TestCase):
    def test_valid(self):
        f = DropFirst()
        f._run(values=[1, 2, 3])
        self.assertEqual(f.out['values'], [2, 3])


class ZipTest(unittest.TestCase):
    def test_valid(self):
        f = Zip()
        f._run(values=[[1, 2], [3, 4], [5, 6]])
        self.assertEqual(f.out['values'], [[1, 3, 5], [2, 4, 6]])


class SliceTest(unittest.TestCase):
    def test_slice1(self):
        f = Slice(0, 2)
        f._run(values=[1, 2, 3])
        self.assertEqual(f.out['values'], [1, 2])

    def test_reverse(self):
        f = Reverse()
        f._run(values=[1, 2, 3])
        self.assertEqual(f.out['values'], [3, 2, 1])


class ReduceTest(unittest.TestCase):
    def test_reduce(self):
        f = Reduce(lambda x, y: x + y, 0)
        f._run(values=[1, 2, 3])
        self.assertEqual(f.out['values'], 6)


class SteadyStateTest(unittest.TestCase):
    def test_one_invocation(self):
        f = SteadyState(k=5, threshold=0.3)
        f._run(values=[[30, 33, 4, 16, 29, 34, 10, 44, 12, 25, 22, 25, 36, 49, 32, 24, 39, 36, 34, 38]])
        self.assertEqual(f.out['values'], [[36, 49, 32, 24, 39]])

    def test_two_invocations(self):
        f = SteadyState(k=5, threshold=0.3)
        f._run(values=[[30, 33, 4, 16, 29, 34, 10, 44, 12, 25, 22, 25, 36, 49, 32, 24, 39, 36, 34, 38],
                       [15, 36, 21, 1, 2, 15, 47, 7, 19, 28, 39, 29, 32, 17, 15, 18, 14, 8, 39, 0]])
        self.assertEqual(f.out['values'], [[36, 49, 32, 24, 39], [19, 28, 39, 29, 32] ])


class ConfidenceIntervalMeanTest(unittest.TestCase):
    def test_small_sample_set(self):
        f = ConfidenceIntervalMean(significance_level=0.9)
        f._run(values=[1, 2, 3])
        for actual, expected in zip(f.out['interval'], (1.9179390061550845, 2.0820609938449155)):
            self.assertAlmostEqual(actual, expected)

    def test_large_sample_set(self):
        f = ConfidenceIntervalMean(significance_level=0.9)
        f._run(values=range(31))
        for actual, expected in zip(f.out['interval'], (14.794795879876117, 15.205204120123883)):
            self.assertAlmostEqual(actual, expected)


class CI2AlternativesTest(unittest.TestCase):
    def test_small_sample_set(self):
        f = CI2Alternatives(significance_level=0.9)
        f._run(xs=[1, 2, 3], ys=range(31))
        for actual, expected in zip(f.out['interval'], (-13.219442204882425, -12.780557795117575)):
            self.assertAlmostEqual(actual, expected)

    def test_large_sample_set(self):
        f = CI2Alternatives(significance_level=0.9)
        f._run(xs=range(31), ys=range(31))
        for actual, expected in zip(f.out['interval'], (-0.29020244973403198, 0.29020244973403198)):
            self.assertAlmostEqual(actual, expected)


class SortTest(unittest.TestCase):
    def test_valid(self):
        f = Sort("values")
        f._run(values=[1, 3, 2], names=['a', 'c', 'b'])
        self.assertEqual(f.out['values'], [1, 2, 3])
        self.assertEqual(f.out['names'], ['a', 'b', 'c'])

    def test_sort_by_multiple_cols(self):
        f = Sort(["a", "b"])
        f._run(a=[3, 1, 1], b=['b', 'c', 'a'], c=[1, 2, 3])
        self.assertEqual(f.out['a'], [1, 1, 3])
        self.assertEqual(f.out['b'], ['a', 'c', 'b'])
        self.assertEqual(f.out['c'], [3, 2, 1])


class AccumulateTest(unittest.TestCase):
    def test_valid(self):
        f = Accumulate('a')
        f._run(a=[1, 2, 3])
        self.assertEqual(f.out['accum'], [1, 3, 6])


class NormalizeTest(unittest.TestCase):
    def test_valid(self):
        f = Normalize()
        f._run(values=[67, 22, 7, 5, 3, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], norm=126)
        self.assertAlmostEqual(1.0 - sum(f.out['values']), 0.0)


class ComposerTest(unittest.TestCase):
    def setUp(self):
        self.dacapo = DacapoHarness()
        self.composed = Composer(self.dacapo, Print, 'a', Print, ('a', 'b'))
        self.composed2 = Composer(self.dacapo, (Slice, 42, {'step' : 2}),
                                  'a', Print, ('a', 'b'))

    @staticmethod
    def elements_of(pipeline):
        elements = set()
        for edge in pipeline.edges:
            elements.add(edge.source)
            elements.add(edge.sink)
        return elements

    def test_unchanged_instance(self):
        self.assertIn(self.dacapo, self.elements_of(self.composed >> Print()))

    def test_new_generated_instances(self):
        self.assertNotEqual(id((self.composed >> Print()).edges[0].sink),
                            id((self.composed >> Print()).edges[0].sink))

    def test_generation_with_arguments(self):
        slice = (self.composed2 >> Print()).edges[0].sink
        self.assertEqual(slice.start, 42)
        self.assertEqual(slice.step, 2)

    def test_passing_of_maps(self):
        maps = [edge.map_ for edge in (self.composed >> Print()).edges]
        self.assertItemsEqual([None, [('a', 'a')], [('a', 'b')]], maps)


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.tempfile = tempfile.mkstemp()[1]

    def test_simple(self):
        f = Export(self.tempfile, ['test1', 'test2', 'values'],
                   [['v1', 'v2'].__getitem__, ['z1', 'z2'].__getitem__])
        f._run(values=[[1, 2], [3, 4]])
        expected = "test1\ttest2\tvalues\r\n" \
            "v1\tz1\t1\r\n" \
            "v1\tz2\t2\r\n" \
            "v2\tz1\t3\r\n" \
            "v2\tz2\t4\r\n"
        actual = open(self.tempfile).read()
        try:
            self.assertMultiLineEqual(actual, expected)
        finally:
            os.remove(self.tempfile)

    def test_function_for_value(self):
        f = Export(self.tempfile, ['test1', 'test2', 'values'],
                   [['v1', 'v2'].__getitem__, ['z1', 'z2'].__getitem__],
                    lambda x: "small" if x < 2 else "big")
        f._run(values=[[1, 2], [3, 4]])
        expected = "test1\ttest2\tvalues\r\n" \
            "v1\tz1\tsmall\r\n" \
            "v1\tz2\tbig\r\n" \
            "v2\tz1\tbig\r\n" \
            "v2\tz2\tbig\r\n"
        actual = open(self.tempfile).read()
        try:
            self.assertMultiLineEqual(actual, expected)
        finally:
            os.remove(self.tempfile)

    def test_without_functions(self):
        f = Export(self.tempfile, ['test1', 'test2', 'values'])
        f._run(values=[[1, 2], [3, 4]])
        expected = "test1\ttest2\tvalues\r\n" \
            "0\t0\t1\r\n" \
            "0\t1\t2\r\n" \
            "1\t0\t3\r\n" \
            "1\t1\t4\r\n"
        actual = open(self.tempfile).read()
        try:
            self.assertMultiLineEqual(actual, expected)
        finally:
            os.remove(self.tempfile)

    def test_short_function_list(self):
        f = Export(self.tempfile, ['bench', 'iteration', 'times'],
                   [['batik', 'fop'].__getitem__])
        f._run(values=[[1, 2], [3, 4]])
        expected = "bench\titeration\ttimes\r\n" \
            "batik\t0\t1\r\n" \
            "batik\t1\t2\r\n" \
            "fop\t0\t3\r\n" \
            "fop\t1\t4\r\n"
        actual = open(self.tempfile).read()
        try:
            self.assertMultiLineEqual(actual, expected)
        finally:
            os.remove(self.tempfile)

    def test_unbalanced_values(self):
        f = Export(self.tempfile, ['test1', 'test2', 'values'],
                   [['v1', 'v2'].__getitem__, ['z1', 'z2'].__getitem__])
        with self.assertRaises(ValueError):
            f._run(values=[[1, [2]], [3, 4]])
