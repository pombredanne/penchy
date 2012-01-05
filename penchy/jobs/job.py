import logging
from collections import namedtuple
from itertools import groupby, ifilter
from operator import attrgetter

from penchy.jobs.dependency import build_keys, edgesort
from penchy.util import tempdir


log = logging.getLogger('job')

def makeJVMNodeConfiguration(jvm, node, name=None):
    """
    Return a JVMNodeConfiguration.

    :param jvm: :class:`JVM` to execute the job
    :param node: :class:`NodeConfiguration` to execute on
    :param name: decorative name of the configuration
    """

    name = name or "{0} @ {1}".format(jvm, node)

    return JVMNodeConfiguration(jvm, node, name)

JVMNodeConfiguration = namedtuple('JVMNodeConfiguration', ['jvm', 'node', 'name'])

class Job(object):
    """
    Represents a job.
    """

    def __init__(self, configurations,
                 client_flow, server_flow,
                 invocations=1):
        """
        :param configurations: :class:`JVMNodeConfiguration` to execute jobs on
        :param client_flow: sequence of :class:`Edge` that describes the
                            execution of the job on nodes
        :param server_flow: sequence of :class:`Edge` that describes the
                            execution of the job on nodes
        :param invocations: number of times to run job on each configuration
        """
        self.configurations = configurations
        self.client_flow = client_flow
        self.server_flow = server_flow
        self.invocations = invocations

    def run(self, configuration):
        """
        Run Job.

        :param configuration: configuration to run.
        """
        starts = ifilter(bool, (configuration.workload, configuration.tool))
        _, edge_order = edgesort(starts, self.client_flow)
        for i in self.invocations:
            log.info('Run invocation {0}'.format(i))
            with tempdir():
                configuration.jvm.run()
                for sink, group in groupby(edge_order, attrgetter('sink')):
                    kwargs = build_keys(group)
                    sink.run(**kwargs)

    def check(self):
        """
        Check job for plausibility.

        :returns: if job is plausible, i.e. no failure is expected.
        :rtype: bool
        """
        # FIXME: implement me!
        pass
