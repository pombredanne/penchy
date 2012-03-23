from random import randint
from tempfile import NamedTemporaryFile
from xml.etree.ElementTree import ElementTree as ET

from penchy.compat import unittest, write
from penchy.maven import *


_ATTRIBS = {'groupId': 'a', 'artifactId': 'b', 'version': '1'}


class PomTest(unittest.TestCase):
    """
    A POM generated by :class:`POM` should look something like::

        <project>
          <dependencies>
            <dependency>
              <version>version</version>
              <groupId>groupId</groupId>
              <artifactId>artifactId</artifactId>
            </dependency>
          </dependencies>
          <repositories>
            <repository>
              <url>repo</url>
              <id>repo</id>
            </repository>
          </repositories>
          <modelVersion>4.0.0</modelVersion>
        </project>

    """
    def test_pom_attribs(self):
        for attrib in ('a', 'b', 'c', 'd'):
            with NamedTemporaryFile() as tf:
                rand = str(randint(0, 1000))
                d = {attrib: rand}
                d.update(_ATTRIBS)
                p = POM(**d)
                p.write(tf.name)
                tree = ET()
                tree.parse(tf.name)
                self.assertEqual(tree.getroot().find(attrib).text, rand)

    def test_pom_dependency(self):
        dep = MavenDependency('groupId', 'artifactId', 'version', 'repo')

        with NamedTemporaryFile() as tf:
            p = POM(**_ATTRIBS)
            p.add_dependency(dep)
            p.write(tf.name)
            tree = ET()
            tree.parse(tf.name)
            root = tree.getroot()
            xdep = root.find('dependencies/dependency')
            for attrib in ('groupId', 'artifactId', 'version'):
                self.assertEqual(xdep.find(attrib).text, attrib)

            self.assertEqual(root.find('repositories/repository/url').text, 'repo')

    def test_bootstrap_pom(self):
        with NamedTemporaryFile() as tf:
            p = BootstrapPOM()
            p.write(tf.name)
            for f in [tf, make_bootstrap_pom()]:
                tree = ET()
                tree.parse(f.name)
                root = tree.getroot()
                from penchy import __version__ as penchy_version

                self.assertEqual(root.find('artifactId').text, 'penchy-bootstrap')
                self.assertEqual(root.find('version').text, penchy_version)

    def test_penchy_pom(self):
        with NamedTemporaryFile() as tf:
            p = PenchyPOM()
            p.write(tf.name)
            tree = ET()
            tree.parse(tf.name)
            root = tree.getroot()
            from penchy import __version__ as penchy_version

            self.assertEqual(root.find('artifactId').text, 'penchy')
            self.assertEqual(root.find('version').text, penchy_version)

    def test_penchy_pom2(self):
        with NamedTemporaryFile() as tf:
            write_penchy_pom([MavenDependency('a', 'b', '1')], tf.name)
            tree = ET()
            tree.parse(tf)
            root = tree.getroot()
            from penchy import __version__ as penchy_version

            self.assertEqual(root.find('artifactId').text, 'penchy')
            self.assertEqual(root.find('version').text, penchy_version)


class MavenTest(unittest.TestCase):
    def setUp(self):
        self.d1 = MavenDependency(
                'org.scalabench.benchmarks',
                'scala-benchmark-suite',
                '0.1.0-20110908.085753-2',
                'http://repo.scalabench.org/snapshots/')

        self.d2 = MavenDependency(
                'org.scalabench.benchmarks',
                'scala-benchmark-suite',
                '0.1.0-20110908.085753-2',
                'http://repo.scalabench.org/snapshots/')

        self.d3 = MavenDependency(
                'org.scalabench.benchmarks',
                'scala-benchmark-suite2',
                '0.1',
                'http://repo.scalabench.org/snapshots/')

    def test_mavendep_equal(self):
        self.assertEqual(self.d1, self.d2)

    def test_mavendep_duplicates(self):
        p = POM(**_ATTRIBS)
        p.add_dependency(self.d1)
        p.add_dependency(self.d2)
        self.assertEqual(p.dependencies, set((self.d1,)))

    def test_mavendep_repo_duplicates(self):
        p = POM(**_ATTRIBS)
        p.add_repository('foo')
        p.add_repository('foo')
        self.assertEqual(p.repositories, set(('foo',)))

        p = POM(**_ATTRIBS)
        p.add_dependency(self.d1)
        p.add_dependency(self.d2)
        self.assertEqual(p.repositories, set((self.d1.repo,)))

    def test_required_keywords(self):
        self.assertRaises(POMError, POM)


class MavenUtilTest(unittest.TestCase):
    def setUp(self):
        self.tf = NamedTemporaryFile()
        write(self.tf, """
            <settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                                http://maven.apache.org/xsd/settings-1.0.0.xsd">
                <servers>
                    <server>
                        <id>server001</id>
                        <username>my_login</username>
                        <password>my_password</password>
                    </server>
                </servers>
            </settings>
            """)
        self.tf.flush()

    def tearDown(self):
        self.tf.close()

    def test_extract_password(self):
        username, password = extract_maven_credentials('server001', self.tf.name)
        self.assertEqual(username, 'my_login')
        self.assertEqual(password, 'my_password')

    def test_extract_no_credentials(self):
        with self.assertRaises(ValueError):
            extract_maven_credentials('server002', self.tf.name)
