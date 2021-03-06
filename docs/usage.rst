=====
Usage
=====
This document explains the basic usage of PenchY.

There is only a single entry point to PenchY, the ``penchy`` command,
which takes quite a few command line parameters:

 * ``-h`` or ``--help``
   shows a help message and exit
 * ``-c CONFIG`` or ``--config config`` specifies a configuration file. Please
   consult the :doc:`configuration` file section in order to learn how to
   write such a file. This argument defaults to ``~/.penchyrc``.
 * ``--logfile``
   specifies the file to which PenchY will log. Please note that PenchY will
   automatically rotate logfiles, so if you pass ``--logfile foo.log``,
   ``foo.log.1`` might be created by PenchY.
 * ``-d`` or ``--debug``
   sets the log level to ``DEBUG``.
 * ``-q`` or ``--quiet``
   sets the log level to ``WARNING``.
 * ``--check``
   checks a job for validity only.
 * ``--visualize``
   visualize the dependencies of the job's pipelines as Graph (needs Graphviz).
 * ``--run-locally``
   runs a job locally without the involvement of client/server
   communication. This requires the ``hostname`` passed to
   :class:`~penchy.jobs.job.NodeSetting` to be ``localhost``.
 * ``-f`` or ``--load-from`` will load PenchY from the path supplied
   instead of acquiring it using maven. This is a pretty nifty feature
   if you are working on the client code and don't want to deploy
   the changes using maven as you write it. A simple scenario might
   be copying your PenchY version to the nodes using rsync and then
   using that version. Let's say you are using rsync to copy your
   version of PenchY to ``/tmp/penchy2``, then you'd need to pass
   ``-f /tmp/penchy2`` to the ``penchy`` command on the server, which
   will result in all nodes loading PenchY from this path. The following
   snippet might be useful to you::

        #!/bin/bash -e

        for node in 192.168.56.10 192.168.56.11; do
            rsync -az --exclude '*.log' --exclude '*.pyc' . bench@${node}:~/penchy
        done

        bin/penchy --load-from /home/bench/penchy $*
