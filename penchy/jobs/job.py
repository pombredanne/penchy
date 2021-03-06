"""
This module provides the foundation to define jobs.

 .. moduleauthor:: Michael Markert <markert.michael@googlemail.com>
 .. moduleauthor:: Fabian Hirschmann <fabian@hirschm.net>

 :copyright: PenchY Developers 2011-2012, see AUTHORS
 :license: MIT License, see LICENSE
"""
import logging
import os
import subprocess
from collections import defaultdict
from functools import partial
from hashlib import sha1
from itertools import groupby, chain
from operator import attrgetter
from tempfile import NamedTemporaryFile

from penchy.compat import update_hasher, write
from penchy.jobs.dependency import build_keys, edgesort
from penchy.jobs.elements import PipelineElement, SystemFilter
from penchy.jobs.filters import Receive, Send, WrongInputError
from penchy.jobs.plots import Plot
from penchy.jobs.hooks import Hook
from penchy.jobs.typecheck import TypeCheckError
from penchy.maven import get_classpath, setup_dependencies
from penchy.util import tempdir, default


log = logging.getLogger(__name__)


class NodeSetting(object):
    """
    Represents a configuration of a node.
    """

    def __init__(self, host, ssh_port, username, path,
                 basepath, description="", password=None,
                 keyfile=None, timeout_factor=1):
        """
        :param host: hostname (or IP) of node
        :type host: string
        :param ssh_port: port number of ssh server on node
        :type ssh_port: int
        :param username: login name for penchy on node
        :type username: string
        :param path: working directory on the node (this is where
                     the job will be uploaded to and where the
                     temporary files and directories will be created)
        :type path: string
        :param basepath: basepath for JVMs on this node
        :type basepath: string
        :param description: Textual description of node
        :type description: string
        :param password: this is either the password for a given username
                         or the passphrase to unlock the keyfile
        :type password: string
        :param keyfile: path to the ssh keyfile to use (defaults to system keyfile)
        :type keyfile: string
        :param timeout_factor: this is either an integer or a function
                               which gets executed client-side and returns
                               an integer. In either case, the resulting
                               integer will get multiplied with the timeout
                               for this node.
        :type timeout_factor: int or function
        """
        self.host = host
        self.ssh_port = ssh_port
        self.username = username
        self.path = path
        self.basepath = basepath
        self.description = description
        self.password = password
        self.keyfile = keyfile
        self._timeout_factor = timeout_factor

    @property
    def identifier(self):
        """
        A unique identifier for this node.
        """
        return self.host

    @property
    def timeout_factor(self):
        """
        The factor by which the timeout should get multiplied with.
        """
        if callable(self._timeout_factor):
            return self._timeout_factor()

        return self._timeout_factor

    def __eq__(self, other):
        return isinstance(other, NodeSetting) and \
                self.identifier == other.identifier

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.identifier)

    def __str__(self):
        return self.identifier

    def hash(self):
        """
        Return the sha1 hexdigest.

        Used for identifying :class:`SystemComposition` across server and
        client.

        :returns: sha1 hexdigest of instance
        :rtype: string
        """
        hasher = sha1()
        update_hasher(hasher, self.identifier)
        return hasher.hexdigest()


class SystemComposition(object):
    """
    This class represents a combination of a :class:`~penchy.jobs.jvms.JVM`
    and a :class:`NodeSetting`.

    A :class:`SystemComposition` is a unique identifier that groups the
    results of its execution for server consumption.

    The ``flow`` of the :class:`SystemComposition` has to be set before
    executing the job::

        composition = SystemComposition(jvm, node)
        w = Dacapo('fop')
        jvm.workload = w
        composition.flow = [w >> Print()]

    """

    def __init__(self, jvm, node_setting, name=None):
        """
        :param jvm: the associated jvm
        :type jvm: :class:`~penchy.jobs.jvms.JVM`
        :param node_setting: the node setting
        :type node_setting: :class:`NodeSetting`
        """
        self.name = default(name, "{0} @ {1}".format(jvm, node_setting))
        self.jvm = jvm
        self.node_setting = node_setting
        self._flow = []

    def __eq__(self, other):
        try:
            return self.hash() == other.hash()
        except Exception:
            return False

    def __ne__(self, other):
        return self.jvm != other.jvm or self.node_setting != other.node_setting

    def __hash__(self):
        return hash(hash(self.jvm) + hash(self.node_setting))

    def __str__(self):  # pragma: no cover
        return self.name

    def hash(self):
        """
        Return the sha1 hexdigest.

        Used for identifying :class:`SystemComposition` across server and
        client.

        :returns: sha1 hexdigest of instance
        :rtype: str
        """
        hasher = sha1()
        update_hasher(hasher, self.jvm.hash())
        update_hasher(hasher, self.node_setting.hash())
        return hasher.hexdigest()

    def set_timeout_function(self, fun):
        """
        Set the timeout function of this composition.

        :param fun: timeout function
        :type fun: callable
        """
        if not self.timeout:
            return

        timeout_hook = Hook(setup=lambda: fun(self.hash(), self.timeout),
                            teardown=lambda: fun(self.hash(), 0))
        self.jvm.hooks.append(timeout_hook)

    @property
    def flow(self):
        """
        The flow of the pipeline.
        """
        return self._flow

    @flow.setter
    def flow(self, flow):
        """
        The flow of the pipeline.

        :param flow: flow of execution after JVM
        :type flow: List of :class:`Edge` or :class:`Pipeline`
        """
        self._flow = list(chain.from_iterable(e.edges for e in flow))

    @property
    def starts(self):
        """
        The starts of the pipeline.

        All :class:`~penchy.jobs.elements.PipelineElement` that
        are executed by the jvm.
        """
        return [e for e in (self.jvm.workload, self.jvm.tool, self.jvm)
                if isinstance(e, PipelineElement)]

    @property
    def elements(self):
        """
        All :class:`~penchy.jobs.elements.PipelineElement` of this composition.
        """
        if not self._flow:
            log.warn('No flow set')

        elements = set(e.source for e in self._flow)
        elements.update(e.sink for e in self._flow)
        if self.jvm.workload:
            elements.add(self.jvm.workload)
        if self.jvm.tool:
            elements.add(self.jvm.tool)
        if isinstance(self.jvm, PipelineElement):
            elements.add(self.jvm)

        return elements

    @property
    def timeout(self):
        """
        Timeout of this Composition.
        """
        return self.jvm.timeout * self.node_setting.timeout_factor

    def _reset(self):
        """
        Reset the elements..
        """
        for e in self.elements:
            e.reset()


class Job(object):
    """
    Represents a job.

    Those attributes have to be set from the outside before a :class:`Job`
    instance is ``run``:

    - ``job.send`` to be set on client to a function with a signature
      ``(hash, data)`` where ``hash`` identifies the :class:`SystemComposition`
      and ``data`` the data to send

    - ``job.receive`` to be set on server to a function that takes no arguments
      and returns the results of all :class:`SystemComposition` with the
      :class:`SystemComposition` as key and the results as value.

    - ``job.filename`` has to be set to the filename of the job
    """

    def __init__(self, compositions, server_flow, invocations=1):
        """
        :param compositions: :class:`SystemComposition` to execute jobs on
        :type compositions: List of :class:`SystemComposition`
                              or :class:`SystemComposition`
        :param server_flow: describes the execution of the job on the server
        :type server_flow: List of :class:`~penchy.jobs.dependency.Edge` or
                           :class:`~penchy.jobs.dependency.Pipeline`
        :param invocations: number of times to run job on each configuration
        :type invocations: int
        """
        self.compositions = compositions if isinstance(compositions, list) \
                            else [compositions]
        self.server_flow = list(chain.from_iterable(dep.edges for dep in server_flow))
        self.invocations = invocations
        self.send = None
        self.timeout = None
        self.receive = None
        self._composition = None
        self.filename = None

    def run(self, composition):
        """
        Run clientside Job.

        :param composition: composition to run.
        :type composition: :class:`SystemComposition`
        """
        # setup
        pomfile = os.path.join(composition.node_setting.path, 'pom.xml')
        setup_dependencies(pomfile, self._get_client_dependencies(composition))
        composition.jvm.add_to_cp(get_classpath(pomfile))
        self._composition = composition

        # save send for restoring
        send = self.send
        # replace with one that knows how to identify the composition if it is set
        if self.send is not None:
            self.send = partial(self.send, composition.hash())

        composition.jvm.basepath = composition.node_setting.basepath

        _, edge_order = edgesort(composition.starts, composition.flow)

        for i in range(1, self.invocations + 1):
            log.info('Run invocation {0}'.format(i))
            with tempdir(prefix='penchy-invocation{0}-'.format(i)):
                composition.jvm.run()

        log.info('Run pipeline')
        for sink, group in groupby(edge_order, attrgetter('sink')):
            kwargs = build_keys(group)
            if isinstance(sink, SystemFilter):
                kwargs[':environment:'] = self._build_environment()
            log.debug('Passing this input to {0}:\n{1}'
                      .format(sink.__class__.__name__,
                              kwargs))
            try:
                sink.run(**kwargs)
            except TypeCheckError:
                log.error('Type check failed on component {0} and arguments {1}'
                          .format(sink.__class__.__name__, kwargs))
                raise
            except WrongInputError:
                log.error('Run failed on component {0} and arguments {1}'
                          .format(sink.__class__.__name__, kwargs))
                raise
            log.debug('{0} transformed input to:\n{1}'
                      .format(sink.__class__.__name__, sink.out))

        # reset state of filters for running multiple configurations
        composition._reset()
        # restore send
        self.send = send
        self._composition = None

    def _get_client_dependencies(self, composition):
        """
        Return all clientside :class:`MavenDependency` of this job for a given
        :class:`SystemComposition`.

        :raises: :exc:`ValueError` if ``composition`` is not part of this job

        :param composition: composition to analyze.
        :type composition::class:`SystemComposition`
        :returns: Set of :class:`MavenDependency`.
        :rtype: set
        """
        if composition not in self.compositions:
            raise ValueError('composition not part of this job')

        return set(chain.from_iterable(e.DEPENDENCIES for e in composition.elements))

    def run_server_pipeline(self):
        """
        Run the serverside pipeline.

        :raise: :exc:`ValueError` if there is no
                :class:`~penchy.jobs.filters.Receive` in the serverside pipeline
        """
        # Do nothing if server_flow is empty
        if not self.server_flow:
            return

        starts = [edge.source for edge in self.server_flow
                  if isinstance(edge.source, Receive)]

        if not starts:
            log.error('There is no Receiver in the serverside flow. Aborting.')
            raise ValueError('There is no Receiver in the serverside flow')

        _, edge_order = edgesort(starts, self.server_flow)

        # all starts are receivers, run them with the environment
        for start in starts:
            start.run(**{':environment:': self._build_environment()})

        # run other filters
        for sink, group in groupby(edge_order, attrgetter('sink')):
            kwargs = build_keys(group)
            if isinstance(sink, SystemFilter):
                kwargs[':environment:'] = self._build_environment()
            log.debug('Passing this input to {0}:\n{1}'
                      .format(sink.__class__.__name__,
                              kwargs))
            try:
                sink.run(**kwargs)
            except TypeCheckError:
                log.error('Type check failed on component {0} and arguments {1}'
                          .format(sink.__class__.__name__, kwargs))
                raise
            except WrongInputError:
                log.error('Run failed on component {0} and arguments {1}'
                          .format(sink.__class__.__name__, kwargs))
                raise
            log.debug('{0} transformed input to:\n{1}'
                      .format(sink.__class__.__name__, sink.out))

    def _get_server_dependencies(self):
        """
        Return the serverside dependencies of the job.

        :returns: Set of :class:`MavenDependency`.
        :rtype: set
        """
        return set(chain.from_iterable(element.DEPENDENCIES for element
                                       in self.server_flow))

    def _build_environment(self):
        """
        Return the environment for a :class:`SystemFilter`.

        Contains:
        - ``receive``: to get all data that has been received, takes no arguments
                       returns a dict with :class:`SystemComposition` as keys
        - ``send``: to send data to the server, takes one datum as argument
        - ``job``: the filename this job
        - ``current_composition``: the current :class:`SystemComposition` or ``None``

        :returns: environment for a SystemFilter
        :rtype: dict
        """
        # replace receive and send with dummy functions if not set to avoid
        # corner cases in pipeline
        receive = default(self.receive, lambda: {})
        send = default(self.send, lambda data: None)

        return dict(receive=receive,
                    send=send,
                    job=self.filename,
                    current_composition=self._composition)

    def compositions_for_node(self, identifier):
        """
        Return the compositions of this job that are to be run on the node
        that corresponds to ``identifier``.

        :param identifier: identifier for node.
        :type host: str
        :returns: :class:`SystemComposition` of job that run on host
        :rtype: list
        """
        return [c for c in self.compositions if c.node_setting.identifier == identifier]

    def check(self):
        """
        Check job for plausibility.

        :returns: if job is plausible, i.e. no failure is expected.
        :rtype: bool
        """
        valid = True
        for composition in self.compositions:
            # check if workload is set
            if composition.jvm.workload is None:
                log.error('Check: composition "{0}" has no workload'
                          .format(composition))
                valid = False

            # check if there are no starts in client pipelines
            if not composition.starts:
                log.error('Check: composition {0} has no starts'
                          .format(composition.name))
                valid = False
            # check if there are cycles in client pipelines
            try:
                edgesort(composition.starts, composition.flow)
            except ValueError:
                log.exception('Check: cycle on composition "{0}"'
                              .format(composition))
                valid = False

            if not any(isinstance(e, Send) for e in composition.elements):
                log.error('Check: there is no Send in composition "{0}"'
                          .format(composition))
                valid = False

            if any(isinstance(e, Plot) for e in composition.elements):
                log.error('Check: there is a Plot in composition "{0}"'
                          .format(composition))
                valid = False

        # check if there are cycles in server pipeline
        starts = [edge.source for edge in self.server_flow
                  if isinstance(edge.source, Receive)]
        if not starts:
            # if there are no receivers the server pipeline is not valid
            log.error('Check: There is no Receiver in server pipeline')
            valid = False
        else:
            try:
                edgesort(starts, self.server_flow)
            except ValueError:
                log.exception('Check: cycle in server pipeline')
                valid = False

        for flow in chain(chain(c.flow for c in self.compositions),
                         [self.server_flow]):
            valid = valid and self._check_flow(flow)

        return valid

    def _check_flow(self, flow):
        """
        Check the flow for validity.

        That is:
        - all Edges are valid (inputs/outputs exist)
        - all Sinks are saturated

        :param flow: flow to check
        :type flow: sequence of :class:`~penchy.jobs.dependency.Edge`
        :returns: if flow is valid
        :rtype: bool
        """
        valid = True
        sources_of_sinks = defaultdict(list)
        for edge in flow:
            if not edge.check():
                log.error('Error at connection from "{0}" to "{1}"'
                          .format(edge.source.__class__.__name__,
                                  edge.sink.__class__.__name__))
                valid = False
            source_name_mapping = (edge.source.__class__.__name__,
                                   default(edge.map_,
                                           [(name, name) for name
                                            in edge.source.outputs.names]))
            sources_of_sinks[edge.sink].append(source_name_mapping)
        for sink, source_mappings in sources_of_sinks.items():
            if not sink.inputs.check_sink(source_mappings):
                log.error('Error at sink "{0}"'.format(sink.__class__.__name__))
                valid = False

        return valid

    def visualize(self, format='png', dot='dot'):
        """
        Visualize job via graphviz.

        .. note::

            The ``dot`` executable has to be in the path or passed as ``dot``
            parameter.

        :param format: output format (has to be supported by dot)
        :type format: str
        :param dot: path to dot executable
        :type dot: str

        :returns: the path to the generated file
        :rtype: str
        """
        def edges_of_flow(flow, flow_id=0):
            """
            :param flow: flow to visualize
            :type flow: list of :class:`~penchy.jobs.dependency.Edge`
            :param flow_id: id to differentiate between multiple flows with same elements
            :type flow_id: int
            :returns: edges in graphviz format
            :rtype: list of str
            """

            return [""" node{source_id}{id} [label = "{source}"];
                        node{sink_id}{id} [label = "{sink}"];
                        node{source_id}{id} -> node{sink_id}{id} [label = "{decoration}"];
                    """
                    .format(source=e.source,
                            source_id=id(e.source),
                            sink=e.sink,
                            sink_id=id(e.sink),
                            id=flow_id,
                            decoration=', '.join('{0} -> {1}'
                                                 .format(m[0], m[1])
                                                 if m[0] != m[1]
                                                 else m[0]
                                                 for m in e.map_
                                             )
                                    if e.map_ else '')
                    for e in flow]

        clients = ["""
                   subgraph cluster_client%d {
                       label = "%s";
                       %s
                   }
                   """ % (i, c.name, '\n'.join(edges_of_flow(c.flow, i)))
                   for i, c in enumerate(self.compositions)]

        server_edges = edges_of_flow(self.server_flow)
        s = """
        digraph G {
            rankdir = LR
            subgraph cluster_server {
                color = blue;
                %s
                label = "Server";
            }
            subgraph cluster_client {
                color = black;
                label = "Clients";
                %s
            }
        }
        """ % ('\n'.join(server_edges), '\n'.join(clients))
        with NamedTemporaryFile(delete=False) as f:
            fname = f.name
            write(f, s)
        subprocess.call([dot, '-T', format, '-O', fname])
        os.remove(fname)
        return '{0}.{1}'.format(fname, format)
