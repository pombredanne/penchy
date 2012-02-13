"""
This modules contains the code for defining and checking types of inputs and
outputs in the pipeline.

 .. moduleauthor:: Michael Markert <markert.michael@googlemail.com>

 :copyright: PenchY Developers 2011-2012, see AUTHORS
 :license: MIT License, see LICENSE
"""
import logging
from itertools import chain


log = logging.getLogger(__name__)


class TypeCheckError(Exception):
    """
    Signals that an Argument is missing or has the wrong type.
    """
    pass


class Types(object):
    """
    This class models the typing of input and outputs of
    :class:`~penchy.jobs.elements.PipelineElement`.
    """

    def __init__(self, *type_descriptions):
        """
        The format of a type description is this::

            (name, type, *types)

        - ``name`` is the name of the argument
        - ``type`` is the type of the argument
        - ``types`` are zero or more subtypes
           (preceding types must be ``list``, ``tuple`` or ``dict``)

        Alternatively you can pass no args to disable type checking.

        :raises: :class:`AssertError` if ``type_descriptions has a wrong format.
        :param type_descriptions: description of above format
        :type type_descriptions: tuple
        """
        # Dict of types for GernericFilter
        self.type_descriptions = dict((td[0], td[1:]) for td in type_descriptions)

        if not type_descriptions:
            self.descriptions = None
        else:
            self.descriptions = {}
            for t in type_descriptions:
                msg = '{0} is a malformed type description({{0}}), ' \
                      'expected (str, type, *subtype)'.format(t)

                assert isinstance(t, tuple), msg.format('no tuple')
                assert len(t) > 1, msg.format('wrong length')
                name = t[0]
                types = t[1:]
                assert isinstance(name, str), msg.format('name is not a `str`')
                assert all(isinstance(type_, type) for type_ in types), \
                    msg.format('types expected')

                if name in type_descriptions:
                    log.warn('Overring types of name {0} from {1} to {2}'
                             .format(name, self.descriptions[name], types))
                self.descriptions[name] = types

    def __eq__(self, other):
        return self.descriptions == other.descriptions

    @property
    def names(self):
        return set(self.descriptions)

    @property
    def types(self):
        return self.type_descriptions

    def check_input(self, kwargs):
        """
        Check if ``kwargs`` satisfies the descriptions .
        That is:
            - All required names are found and
            - have the right type (and subtypes)

        Logs warnings if there are more arguments than the required.

        :raises: :class:`TypeCheckError` if a name is missing or has the wrong type.

        :param kwargs: arguments for run of a :class:`PipelineElement`
        :type kwargs: dict
        :returns: count of unused inputs
        :rtype: int
        """

        if self.descriptions is None:
            return 0

        for name, types in self.descriptions.items():
            count = len(types)
            if name not in kwargs:
                raise TypeCheckError('Argument {0} is missing'.format(name))

            value = [kwargs[name]]  # pack start value in list to reuse loop
            for i, type_ in enumerate(types):
                if any(not isinstance(v, type_) for v in value):
                    raise TypeCheckError('Argument {0} is not of type {1}'
                                         .format(name, types))
                # don't reinitialize for last type
                if i == count - 1:
                    break

                if issubclass(type_, dict):
                    value = list(chain.from_iterable(subvalue.values() for subvalue in value))
                elif len(value) > 1:
                    value = list(chain.from_iterable(value))
                else:
                    value = value[0]

        unused_inputs = 0
        for name in set(kwargs) - set(self.descriptions):
            unused_inputs += 1
            log.warn("Unknown input {0}".format(name))

        return unused_inputs

    def check_pipe(self, other, mapping):
        """
        Check the validity of the pipe of ``self`` to ``other`` with given
        ``mapping``.

        ``self`` is the source :class:`~penchy.jobs.elements.PipelineElement`
        and other is the sink.

        :param other: the types to which the pipe is checked
        :type other: :class:`Types`
        :param mapping: mappings from ``self`` to ``other``
        :type mapping: list of tuples
        :returns: if pipe to other is valid
        :rtype: bool
        """
        valid = True

        if self.descriptions is None or other.descriptions is None:
            return True

        missing_inputs = set(other.descriptions)
        if mapping == None:
            mapping = [(name, name) for name in self.descriptions]

        for source, sink in mapping:
            if source not in self.descriptions:
                log.error('Source has no output {0}'.format(source))
                valid = False
            if sink not in other.descriptions:
                log.warning('Sink has no input {0}'.format(sink))
            missing_inputs.discard(sink)

        for input in missing_inputs:
            if input == 'environment':
                continue
            log.error('Sink input {0} not saturated'.format(input))
            valid = False

        return valid
