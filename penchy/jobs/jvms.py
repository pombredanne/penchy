"""
This module provides JVMs to run programs.

 .. moduleauthor:: Michael Markert <markert.michael@googlemail.com>

 :copyright: PenchY Developers 2011-2012, see AUTHORS
 :license: MIT License, see LICENSE
"""
import itertools
import logging
import os
import shlex
import subprocess
from hashlib import sha1
from tempfile import NamedTemporaryFile

from penchy.compat import update_hasher, nested
from penchy.jobs.elements import PipelineElement
from penchy.jobs.typecheck import Types


log = logging.getLogger(__name__)


class JVMNotConfiguredError(Exception):
    """
    Signals that a JVM is not sufficiently configured, i.e. a workload is
    missing or no classpath is set.
    """
    pass


class JVMExecutionError(Exception):
    """
    Signals that a execution of JVM failed, that is return non zero exit code.
    """
    pass


class JVM(object):
    """
    This class represents a JVM.

    :attr:`jvm.prehooks` callables (e.g. functions or methods) that are executed
                         before execution
    :attr:`jvm.posthooks` callables (e.g. functions or methods) that are executed
                         after execution
    """

    def __init__(self, path, options=""):
        """
        :param path: path to jvm executable relative to node's basepath
                     (can also be absolute)
        :param options: string of options that will be passed to JVM needs to be
                        properly escaped for a shell
        :type options: str
        """
        self.basepath = '/'
        self._path = path
        # keep user_options for log messages and comparisons around
        self._user_options = options

        self._options = shlex.split(options)
        self._classpath = _extract_classpath(self._options)

        self.prehooks = []
        self.posthooks = []

        # for tools and workloads
        self._tool = None
        self._workload = None

    @property
    def workload(self):
        return self._workload

    @workload.setter
    def workload(self, workload):
        if self._workload is not None:  # pragma: no cover
            log.warn("Overwriting workload!")

        self._workload = workload

    @property
    def tool(self):
        return self._tool

    @tool.setter
    def tool(self, tool):
        if self._tool is not None:  # pragma: no cover
            log.warn("Overwriting Tool!")

        self._tool = tool

    def add_to_cp(self, path):
        """
        Adds a path to the classpath.

        :param path: classpath to add
        :type path: string
        """
        self._classpath.extend(path.split(os.pathsep))

    def run(self):
        """
        Run the JVM in the current configuration.

        :raises: :exc:`JVMNotConfiguredError` if no workload or classpath is set
        """
        prehooks, posthooks = self._get_hooks()

        if not self._classpath:
            log.error('No classpath configured')
            raise JVMNotConfiguredError('no classpath configured')

        if not self.workload:
            log.error('No workload configured')
            raise JVMNotConfiguredError('no workload configured')

        log.debug("executing prehooks")
        for hook in prehooks:
            hook()

        log.debug("executing {0}".format(self.cmdline))
        with nested(NamedTemporaryFile(delete=False, dir='.'),
                    NamedTemporaryFile(delete=False, dir='.')) \
            as (stderr, stdout):
            exit_code = subprocess.call(self.cmdline,
                                        stderr=stderr,
                                        stdout=stdout)

            self.workload.out['exit_code'].append(exit_code)
            self.workload.out['stdout'].append(stdout.name)
            self.workload.out['stderr'].append(stderr.name)
            if exit_code != 0:
                log.error('jvm execution failed, stderr:')
                stderr.seek(0)
                log.error(stderr.read())
                raise JVMExecutionError('non zero exit code: {0}'
                                        .format(exit_code))

        log.debug("executing posthooks")
        for hook in posthooks:
            hook()

    @property
    def cmdline(self):
        """
        The command line suitable for `subprocess.Popen` based on the current
        configuration.
        """
        executable = os.path.join(self.basepath, self._path)
        cp = ['-classpath', os.pathsep.join(self._classpath)] if self._classpath \
             else []
        if self.tool:
            options = self._options + self.tool.arguments
        else:
            options = self._options
        args = self.workload.arguments if self.workload else []
        return [executable] + options + cp + args

    def _get_hooks(self):
        """
        Return hooks of jvm together with possible workload and tool hooks.

        :returns: hooks of configuration grouped as pre- and posthooks
        :rtype: tuple of :func:`itertools.chain`
        """
        if self.workload is None:
            workload_prehooks = []
            workload_posthooks = []
        else:
            workload_prehooks = self.workload.prehooks
            workload_posthooks = self.workload.posthooks

        if self.tool is None:
            tool_prehooks = []
            tool_posthooks = []
        else:
            tool_prehooks = self.tool.prehooks
            tool_posthooks = self.tool.posthooks

        prehooks = itertools.chain(self.prehooks, tool_prehooks,
                                   workload_prehooks)
        posthooks = itertools.chain(self.posthooks, tool_posthooks,
                                    workload_posthooks)
        return prehooks, posthooks

    def __eq__(self, other):
        try:
            return all((
                # executing the equal jvm
                self._path == other._path,
                # with equal options
                self._user_options == other._user_options,
                # check if both workloads or none is set
                (self.workload is None and other.workload is None
                 or self.workload and other.workload),
                # check if both tools or none is set
                (self.tool is None and other.tool is None
                 or self.tool and other.tool)))
        except AttributeError:
            log.exception('Comparing JVM to non-JVM: ')
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(hash(self._path) + hash(self._user_options))

    def __repr__(self):
        return '{2}({0}, {1})'.format(self._path, self._user_options,
                                      self.__class__.__name__)

    def hash(self):
        """
        Return the sha1 hexdigest.

        Used for identifying :class:`SystemComposition` across server and
        client.

        :returns: sha1 hexdigest of instance
        :rtype: str
        """
        hasher = sha1()
        update_hasher(hasher, self._path)
        update_hasher(hasher, self._user_options)
        return hasher.hexdigest()


class WrappedJVM(JVM, PipelineElement):  # pragma: no cover
    """
    This class is an abstract base class for a JVM that is wrapped by another
    Program.

    Inheriting classes must expose this attributes:

    - ``out`` a dictionary that maps logical names for output to actual.
    - ``outputs`` a :class:`~penchy.jobs.typecheck.Types` that describes the
                  output with a logical name and its types
    - ``cmdline`` that returns the cmdline suitable for :class:`subprocess.Popen`
    """

    def _run(self):
        raise ValueError('This is not your normal element, but a JVM')


class ValgrindJVM(WrappedJVM):
    """
    This class represents a JVM which is called by valgrind.
    """
    outputs = Types(('valgrind_log', list, str))

    def __init__(self, path, options='',
                 valgrind_path='valgrind', valgrind_options=''):
        """
        :param path: path to jvm executable relative to node's basepath
                     (can also be absolute)
        :type path: str
        :param options: options for JVM (needs to be escaped for a shell)
        :type options: str
        :param valgrind_path: path to valgrind executable
        :type valgrind_path: str
        :param valgrind_options: options for valgrind (needs to be escaped for
                                 shell)
        :type valgrind_options: str
        """
        super(ValgrindJVM, self).__init__(path, options)
        PipelineElement.__init__(self)

        self.valgrind_path = valgrind_path
        self.valgrind_options = valgrind_options
        self.log_name = 'penchy-valgrind.log'

        self.posthooks.append(lambda: self.out['valgrind_log']
                              .append(os.path.abspath(self.log_name)))

    @property
    def cmdline(self):
        """
        The command line suitable for `subprocess.Popen` based on the current
        configuration.
        """
        cmd = [self.valgrind_path,
               '--log-file={0}'.format(self.log_name),
               '--trace-children=yes']
        cmd.extend(shlex.split(self.valgrind_options))
        return cmd + super(ValgrindJVM, self).cmdline


def _extract_classpath(options):
    """
    Return the jvm classpath from a sequence of option strings.

    :param options: sequence of jvm options to search
    :type options: list
    :returns: classpath as list of parts
    :rtype: list
    """
    classpath = ''
    prev = ''
    # a later classpath overwrites previous definitions so we have to search
    # from the end
    for x in reversed(options):
        if x in ('-cp', '-classpath'):
            classpath = prev
            break
        prev = x

    return classpath.split(os.pathsep) if classpath else []
