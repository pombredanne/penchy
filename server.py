#!/usr/bin/env python

import os
import sys
import paramiko
import logging

from config import *

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("server")

class Node(object):
    """
    This class represents a node (=a machine on which the benchmark
    will be run on).
    """
    def __init__(self, node):
        """Initialize the node

        :param node: tuple of (hostname, port, username, remote path)
        :type pkey: paramiko.RSAKey
        """

        self.host, self.port, self.username, self.path = node
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.sftp = None

    def connect(self):
        """Connect to the node"""

        log.info("Connecting to node %s" % self.host)
        self.ssh.connect(self.host, username=self.username,
                key_filename=ID_RSA, port=SSH_PORT)

        self.sftp = self.ssh.open_sftp()

        # Create the directory we will be uploading to
        try:
            self.sftp.mkdir(self.path)
        except IOError:
            pass

    def disconnect(self):
        """Disconnect from the node"""

        self.sftp.close()
        self.ssh.close()

    def put(self, filename):
        """Upload a file to the node

        :param filename: string
        """

        location = self.path + os.path.sep + os.path.basename(filename)
        log.info("Copying file %s to %s" % (filename, location))
        self.sftp.put(sys.path[0] + os.path.sep + filename, location)


if __name__ == "__main__":
    nodes = []
    for node in NODES:
        nodes.append(Node(node))

    for node in nodes:
        node.connect()
        for f in FILES:
            node.put(f)
        node.disconnect()