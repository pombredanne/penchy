"""
This module provides configured workloads.

 .. moduleauthor:: Michael Markert <markert.michael@googlemail.com>

 :copyright: PenchY Developers 2011-2012, see AUTHORS
 :license: MIT License, see LICENSE
"""

import logging
import shlex

from penchy.jobs.elements import Workload
from penchy.maven import MavenDependency


log = logging.getLogger(__name__)


class Dacapo(Workload):
    """
    This class represents the workload for the `DaCapo Benchmark-Suite
    <http://dacapobench.org/>`_.
    """
    DEPENDENCIES = set((
        MavenDependency(
            'org.scalabench.benchmarks',
            'scala-benchmark-suite',
            '0.1.0-20110908.085753-2',
            'http://repo.scalabench.org/snapshots/',
            filename='scala-benchmark-suite-0.1.0-SNAPSHOT.jar',
            checksum='fb68895a6716cc5e77f62ed7992d027b1dbea355'
        ),
    ))
    BENCHMARKS = set(( 'avrora'
                      , 'batik'
                      , 'eclipse'
                      , 'fop'
                      , 'h2'
                      , 'jython'
                      , 'luindex'
                      , 'lusearch'
                      , 'pmd'
                      , 'sunflow'
                      , 'tomcat'
                      , 'tradebeans'
                      , 'tradesoap'
                      , 'xalan'))

    def __init__(self, benchmark, iterations=1, args='', timeout=0, name=None):
        """
        :param benchmark: benchmark to execute
        :type benchmark: string
        :param iterations: Number of iterations in an invocation.
        :type iterations: int
        :param args: additional arguments for harness (shell escaped)
        :type args: string
        :param timeout: timeout (in seconds) after which this workload should
                        be terminated
        :type timeout: int
        :param name: descriptive name of this workload (defaults to benchmark name)
        :type name: str
        """
        super(Dacapo, self).__init__(timeout, name)

        self.benchmark = benchmark
        self.iterations = iterations

        self.args = args

    @property
    def arguments(self):
        """
        The arguments to call the workload in the current configuration.

        :returns: the arguments for executing
        :rtype: list
        """
        return ['Harness'] + \
               ['-n', str(self.iterations)] + shlex.split(self.args) + \
               [self.benchmark]

    @property
    def information_arguments(self):
        """
        The arguments to collect information about the benchmark.

        :returns: the arguments for information collection
        :rtype: list
        """
        return ['Harness', '-i', self.benchmark]

    def __repr__(self):  # pragma: no cover
        return '{0}({1})'.format(self.__class__.__name__, self.benchmark)

    def __str__(self):  # pragma: no cover
        return self.name or self.benchmark


class ScalaBench(Dacapo):
    """
    This class represents the workload for the `Scalabench Benchmark-Suite
    <http://scalabench.org/>`_.
    """
    BENCHMARKS = set((  # dacapo
                        'avrora'
                      , 'batik'
                      , 'eclipse'
                      , 'fop'
                      , 'h2'
                      , 'jython'
                      , 'luindex'
                      , 'lusearch'
                      , 'pmd'
                      , 'sunflow'
                      , 'tomcat'
                      , 'tradebeans'
                      , 'tradesoap'
                      , 'xalan'
                        # scalabench
                      , 'actors'
                      , 'apparat'
                      , 'dummy'
                      , 'factorie'
                      , 'kiama'
                      , 'scalac'
                      , 'scaladoc'
                      , 'scalap'
                      , 'scalariform'
                      , 'scalatest'
                      , 'scalaxb'
                      , 'specs'
                      , 'tmt'))
