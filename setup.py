from distutils.core import setup
from penchy import __version__

setup(name='penchy',
        version=__version__,
        description='JVM Benchmarking Tool',
        url='http://www.penchy.0x0b.de/',
        packages=['penchy'],
        scripts=[
            'bin/penchy',
            'bin/penchy_test_job',
            'bin/penchy_bootstrap'],
        install_requires=[
            'numpy',
            'argparse',
            'paramiko',
            'pycrypto']
        )
