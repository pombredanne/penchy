"""
This module provides the parts to model and resolve dependencies in the flow of
execution.
"""


class Edge(object):
    """
    This class represents edges in the dependency graph.
    """

    def __init__(self, source, sink, map_=None):
        """
        :param source: source of data
        :param sink: sink of data
        :param map: sequence of name pairs that map source exits to sink
                    entrances
        """
        self.source = source
        self.sink = sink
        self.map_ = map_

    def __repr__(self):  # pragma: no cover
        return "Edge({0}, {1}, {2})".format(self.source, self.sink, self.map_)


def edgesort(starts, edges):
    """
    Return the topological sorted elements of ``edges``.

    ``starts`` won't be included.

    :param starts: Sequence of :class:`PipelineElement` that have no deps
    :param edges: Sequence of :class:`Edge`
    :returns: pair of topological sorted :class:`PipelineElement` and
              sorted list of corresponding :class:`Edge`
    """
    resolved = set(starts)
    order = []
    edge_order = []
    edges = list(edges)
    old_edges = []
    while True:
        if not edges:
            return order, edge_order

        if edges == old_edges:
            raise ValueError("no topological sort possible")

        for target in set(edge.sink for edge in edges):
            current = [edge for edge in edges if edge.sink is target]
            if all(edge.source in resolved for edge in current):
                resolved.add(target)
                order.append(target)
                edge_order.extend(current)

        old_edges = list(edges)
        edges = [edge for edge in edges if edge.sink not in resolved]


def build_keys(edges):
    """
    Return dictionary that maps the the sink's inputs to the outputs of all its
    sources.

    All ``edges`` must have the identical sink.

    :param edges: iterable of :class:`Edge`
    :returns: dictionary that contains the mapping of sink arguments to all
              wired sources' output
    :rtype: dict of strings to values
    """
    sink = None
    keys = dict()

    for edge in edges:
        # check for identical sinks
        if sink is not None:
            assert sink == edge.sink, "different sinks!"
        sink = edge.sink

        if edge.map_ is None:
            for key in edge.source._output_names:
                keys[key] = edge.source.out[key]
        else:
            for output, input_ in edge.map_:
                keys[input_] = edge.source.out[output]
    return keys
