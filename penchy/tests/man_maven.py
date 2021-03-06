from tempfile import NamedTemporaryFile

from penchy.compat import unittest
from penchy.maven import *


class MavenTest(unittest.TestCase):
    @staticmethod
    def maven_setup(tf, dep_args, dep_kwargs={}):
        dep = MavenDependency(*dep_args, **dep_kwargs)
        dep.pom_path = tf.name
        pom = POM(groupId='a', artifactId='b', version='1')
        pom.add_dependency(dep)
        pom.write(tf.name)

        return dep, pom

    @classmethod
    def setUpClass(cls):
        cls.tf = NamedTemporaryFile()
        cls.dep, cls.pom = cls.maven_setup(cls.tf,
                ['log4j', 'log4j', '1.2.9'])

        cls.tf_cs = NamedTemporaryFile()
        cls.dep_cs, cls.pom_cs = cls.maven_setup(cls.tf_cs,
                ['log4j', 'log4j', '1.2.9'],
                {'checksum': '55856d711ab8b88f8c7b04fd85ff1643ffbfde7c'})

        cls.tf_cs2 = NamedTemporaryFile()
        cls.dep_cs2, cls.pom_cs2 = cls.maven_setup(cls.tf_cs2,
                ['log4j', 'log4j', '1.2.9'],
                {'checksum': 'invalid_checksum'})

    @classmethod
    def tearDownClass(cls):
        cls.tf.close()
        cls.tf_cs.close()
        cls.tf_cs2.close()

    def setUp(self):
        self.dep.pom_path = self.tf.name
        self.dep.filename = None

    def test_get_classpath(self):
        classpath = get_classpath(self.tf.name)
        self.assertTrue(classpath.endswith('log4j-1.2.9.jar'))

    def test_get_filename(self):
        self.assertTrue(self.dep.filename.endswith('log4j-1.2.9.jar'))

    def test_get_filename2(self):
        self.dep.filename = 'log4j-1.2.9.jar'
        self.assertTrue(self.dep.filename.endswith('log4j-1.2.9.jar'))

    def test_get_incorrect_filename(self):
        self.dep.filename = 'foo.jar'
        with self.assertRaises(LookupError):
            self.dep.filename

    def test_pom_not_found(self):
        with self.assertRaises(OSError):
            get_classpath('')

    def test_checksum(self):
        self.assertEqual(self.dep.actual_checksum,
                '55856d711ab8b88f8c7b04fd85ff1643ffbfde7c')

    def test_no_checksum_required(self):
        self.assertTrue(self.dep.check_checksum())

    def test_checksum_required(self):
        self.assertTrue(self.dep_cs.check_checksum())

    def test_checksum_required_fails(self):
        with self.assertRaises(IntegrityError):
            self.dep_cs2.check_checksum()

    def test_setup_dependencies(self):
        setup_dependencies(self.tf_cs.name, [self.dep_cs])

    def test_setup_dependencies_incorrect_checksum(self):
        with self.assertRaises(IntegrityError):
            setup_dependencies(self.tf_cs2.name, [self.dep_cs2])
