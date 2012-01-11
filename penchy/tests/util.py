import os
import json

from penchy.jobs.dependency import Edge

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def get_json_data(name):
    """
    Return the content of the json data file with name.

    :param name: name of the json data file without extension
    :returns: content of json file
    """
    with open(os.path.join(TEST_DATA_DIR, name + '.json')) as f:
        ob = json.load(f)
    return ob


def make_edge(sink, map_):
    return Edge(MockPipelineElement(x[0] for x in map_), sink, map_)


class MockPipelineElement(object):
    def __init__(self, names=None):
        names = names if names is not None else ()
        self.exports = tuple(names)
        self.out = dict((name, 42) for name in self.exports)

    def __repr__(self):
        return "MockPipelineElement({0}, {1})".format(self.exports, self.out)

    def _run(self):
        pass

    def check(self):
        pass