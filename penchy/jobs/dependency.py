"""
This module provides the parts to define and resolve dependencies in the
pipeline.

 .. moduleauthor:: Michael Markert <markert.michael@googlemail.com>

 :copyright: PenchY Developers 2011-2012, see AUTHORS
 :license: MIT License, see LICENSE
"""

from penchy.compat import str, unicode


class Edge(object):
    """
    This class represents edges in the dependency graph.
    """

    def __init__(self, source, sink, map_=None):
        """
        :param source: source of data
        :param sink: sink of data
        :param map_: sequence of name pairs that map source exits to sink
                     entrances
        """
        self.source = source
        self.sink = sink
        self.map_ = map_

    def __repr__(self):  # pragma: no cover
        return "Edge({0}, {1}, {2})".format(self.source, self.sink, self.map_)

    def __eq__(self, other):
        return (self.source == other.source and
                self.sink == other.sink and
                self.map_ == other.map_)

    def __rshift__(self, other):
        """
        Connect this :class:`Edge` to other pipeline elements.

        :param other: element to connect with
        """
        p = Pipeline(self.source)
        if self.map_:
            p >> self.map_
        p >> self.sink
        return p >> other

    @property
    def edges(self):
        """
        Return the edges.

        Provides uniform access to edges of
        :class:`~penchy.jobs.dependency.Edge` and
        :class:`~penchy.jobs.dependency.Pipeline`.
        """
        return [self]

    def check(self):
        """
        Check if ``source`` fits on ``sink`` with the given mapping.
        """
        return self.source.outputs.check_pipe(self.sink.inputs, self.map_)


class Pipeline(object):
    """
    This class represents a whole pipeline in the flow and is used to provide
    the ``Element >> Element >> [('a', 'b')] >> Element`` syntax.

    It is not meant to be used directly but via ``PipelineElement.__rshift__``
    """

    def __init__(self, element):
        """
        :param element: Start element of pipeline
        :type element: :class:`~penchy.jobs.elements.PipelineElement`
        """
        self._edges = []
        self.current_source = element
        self.pending = None

    def __rshift__(self, other):
        """
        Connect pipeline with ``other`` element.

        If ``other`` is a

        - String: copy a single output to a single input with this name
        - List of String: copy all outputs with those names to outputs with
          those names
        - List of Tuple of String (``output``, ``input``): copy ``output`` to
          ``input``
        - :class:`~penchy.jobs.elements.PipelineElement`: append element to
          pipeline (how data is transferred depends on the previous
          shifted elements)

        :param other: element to connect with
        :type other: str, list of str, list of tuple,
                     :class:`~penchy.jobs.element.PipelineElement`
        """
        if isinstance(other, (str, unicode)):
            self.pending = [(other, other)]
        elif isinstance(other, tuple):
            if len(other) == 2 and \
               all(isinstance(x, (str, unicode)) for x in other):
                self.pending = [other]
            else:
                raise ValueError('{0} is not a tuple of 2 strings'.format(other))
        elif isinstance(other, list):
            mapping = [(map_, map_) if isinstance(map_, (str, unicode))
                       else map_ for map_ in other]
            self.pending = mapping
        else:
            edge = Edge(self.current_source, other, self.pending)
            self._edges.append(edge)
            self.current_source = other
            self.pending = None

        return self

    @property
    def edges(self):
        """
        Return the edges.

        Provides uniform access to edges of :class:`Edge` and :class:`Pipeline`.
        """
        return self._edges


def edgesort(starts, edges):
    """
    Return the topological sorted elements of ``edges``.

    ``starts`` won't be included.

    :raises: :exc:`ValueError` if no topological sort is possible
    :param starts: Sequence of :class:`~penchy.jobs.elements.PipelineElement`
                   that have no dependencies
    :param edges: Sequence of :class:`~penchy.jobs.job.Edge`
    :returns: pair of topological sorted
              :class:`~penchy.jobs.elements.PipelineElement` and sorted list of
              corresponding :class:`~penchy.jobs.job.Edge`
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

    :param edges: iterable of :class:`~penchy.jobs.job.Edge`
    :param generic: is this sink a :class:`~penchy.jobs.elements.GenericFilter`
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
