"""
This module contains classes which deal with nodes
(that is, connecting via ssh, uploading the job, starting it...).

 .. moduleauthor:: Fabian Hirschmann <fabian@hirschm.net>

 :copyright: PenchY Developers 2011-2012, see AUTHORS
 :license: MIT License, see LICENSE
"""

import os
import logging
import atexit
from contextlib import contextmanager

import paramiko


log = logging.getLogger(__name__)


class NodeError(Exception):
    """
    Raised when errors occur while dealing
    with :class:`Node`.
    """


class Node(object):  # pragma: no cover
    """
    This class represents a node (a system on which the benchmark
    will be run on) and provides basic ssh/sftp functionality.
    """

    _LOGFILES = set(('penchy_bootstrap.log', 'penchy.log'))

    def __init__(self, setting, compositions):
        """
        Initialize the node.

        :param setting: the node setting
        :type setting: :class:`~penchy.jobs.job.NodeSetting`
        :param compositions: the job module to execute
        :type compositions: module
        """
        self.setting = setting
        self.log = logging.getLogger('.'.join([__name__,
            self.setting.identifier]))

        self.compositions = compositions
        self.expected = list(compositions.job.compositions_for_node(
            self.setting.identifier))

        self.ssh = self._setup_ssh()

        self.client_is_running = False
        self.was_closed = False
        self.sftp = None

    def __eq__(self, other):
        return isinstance(other, Node) and \
                self.setting.identifier == other.setting.identifier

    def __hash__(self):
        return hash(self.setting.identifier)

    def __str__(self):
        return self.setting.identifier

    def _setup_ssh(self):
        """
        Initializes the SSH Connection.
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if not self.setting.keyfile:
            ssh.load_system_host_keys()
        return ssh

    @property
    def received_all_results(self):
        """
        Indicates wheter we are received all results. In other words,
        this is False if we are still waiting for a job which is
        running on a :class:`~penchy.jobs.job.SystemComposition`.
        """
        return len(self.expected) == 0

    def received(self, composition):
        """
        Should be called when a :class:`~penchy.jobs.job.SystemComposition`
        was received for this node.

        :param composition: composition which was received
        :type composition: :class:`~penchy.jobs.job.SystemComposition`
        """
        if composition in self.expected:
            self.expected.remove(composition)

    def connect(self):
        """
        Connect to node.
        """
        self.log.debug('Connecting')
        self.ssh.connect(self.setting.host, username=self.setting.username,
                port=self.setting.ssh_port, password=self.setting.password,
                key_filename=self.setting.keyfile)

        self.sftp = self.ssh.open_sftp()

    def disconnect(self):
        """
        Disconnect from node.
        """
        self.log.debug('Disconnecting')
        self.sftp.close()
        self.ssh.close()

    @property
    def connected(self):
        """
        Indicates whether we are connected to this node.
        """
        transport = self.ssh.get_transport()
        if transport and transport.is_active():
            return True
        return False

    @contextmanager
    def connection_required(self):
        """
        Contextmanager to make sure we are connected before
        working on this node.
        """
        if not self.connected:
            try:
                self.connect()
            except paramiko.AuthenticationException as e:
                self.log.error('Authentication Error: %s' % e)
                self.expected = []
                self.was_closed = True
                raise

        yield

        if self.connected:
            self.disconnect()

    def close(self):
        """
        Close node (disconnect, receive the logs and kill the
        client if neccessary).

        If we have not received all results from this node, the PenchY
        client will be killed on this node.
        """
        if self.was_closed:
            return

        with self.connection_required():
            if not self.received_all_results:
                self.kill()
                self.expected = []

            self.get_logs()
        self.was_closed = True

    def put(self, local, remote=None):
        """
        Upload a file to the node

        :param local: path to the local file
        :type local: string
        :param remote: path to the remote file
        :type remote: string
        """

        local = os.path.abspath(local)

        if not remote:
            remote = os.path.basename(local)

        if not os.path.isabs(remote):
            remote = os.path.join(self.setting.path, remote)

        try:
            self.sftp.mkdir(os.path.dirname(remote))
        except IOError:
            pass

        self.log.debug('Copying file %s to %s' % (local, remote))
        self.sftp.put(local, remote)

    def get_logs(self):
        """
        Read the client's log file and log it using the server's
        logging capabilities.
        """
        client_log = []

        for filename in self.__class__._LOGFILES:
            try:
                filename = os.path.join(self.setting.path, filename)
                logfile = self.sftp.open(filename)
                client_log.append(logfile.read())
                logfile.close()
            except IOError:
                log.error('Logfile %s could not be received from %s' % \
                        (filename, self))

        log.info("""
%(separator)s Start log for %(identifier)s %(separator)s
%(client_log)s
%(separator)s End log for %(identifier)s %(separator)s
        """ % {
            'separator': '-' * 10,
            'identifier': self.setting.identifier,
            'client_log': ''.join(client_log)})

    def execute(self, cmd):
        """
        Executes command on node.

        :param cmd: command to execute
        :type cmd: string
        """
        self.log.debug('Executing `%s`' % cmd)
        return self.ssh.exec_command(cmd)

    def execute_penchy(self, args):
        """
        Executes penchy on node.

        :param args: arguments to pass to penchy_bootstrap
        :type args: string
        """
        if self.client_is_running:
            raise NodeError('You may not start penchy twice!')

        self.log.info('Staring PenchY client')

        self.execute('cd %s && python penchy_bootstrap %s' % (
            self.setting.path, args))
        self.client_is_running = True

        atexit.register(self.close)

    def kill_composition(self):
        """
        Kill the current :class:`~penchy.jobs.job.SystemComposition`
        on this node.

        A pidfile named `penchy.pid` must exist on the node.
        """
        pidfile_name = os.path.join(self.setting.path, 'penchy.pid')
        pidfile = self.sftp.open(pidfile_name)
        pid = pidfile.read()
        pidfile.close()
        self.execute('kill -SIGHUP ' + pid)
        self.log.warn('Current composition was terminated')

    def kill(self):
        """
        Kill PenchY on node. This will kill all processes whose
        parent id match penchy's id.

        A pidfile named `penchy.pid` must exist on the node.
        """
        pidfile_name = os.path.join(self.setting.path, 'penchy.pid')
        pidfile = self.sftp.open(pidfile_name)
        pid = pidfile.read()
        pidfile.close()
        self.execute('pkill -TERM -P ' + pid)
        self.log.warn('PenchY was terminated')
