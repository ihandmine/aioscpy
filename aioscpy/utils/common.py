import numbers

from operator import itemgetter

from aioscpy.settings import BaseSettings


def without_none_values(iterable):
    """Return a copy of ``iterable`` with all ``None`` entries removed.

    If ``iterable`` is a mapping, return a dictionary where all pairs that have
    value ``None`` have been removed.
    """
    try:
        return {k: v for k, v in iterable.items() if v is not None}
    except AttributeError:
        return type(iterable)((v for v in iterable if v is not None))


def build_component_list(compdict, custom=None):
    """Compose a component list from a { class: order } dictionary."""

    def _check_components(complist):
        if len({c for c in complist}) != len(complist):
            raise ValueError(f'Some paths in {complist!r} convert to the same object, '
                             'please update your settings')

    def _map_keys(compdict):
        if isinstance(compdict, BaseSettings):
            compbs = BaseSettings()
            for k, v in compdict.items():
                prio = compdict.getpriority(k)
                if compbs.getpriority(k) == prio:
                    raise ValueError(f'Some paths in {list(compdict.keys())!r} '
                                     'convert to the same '
                                     'object, please update your settings'
                                     )
                else:
                    compbs.set(k, v, priority=prio)
            return compbs
        else:
            _check_components(compdict)
            return {k: v for k, v in compdict.items()}

    def _validate_values(compdict):
        """Fail if a value in the components dict is not a real number or None."""
        for name, value in compdict.items():
            if value is not None and not isinstance(value, numbers.Real):
                raise ValueError(f'Invalid value {value} for component {name}, '
                                 'please provide a real number or None instead')

    # BEGIN Backward compatibility for old (base, custom) call signature
    if isinstance(custom, (list, tuple)):
        _check_components(custom)
        return type(custom)(c for c in custom)

    if custom is not None:
        compdict.update(custom)
    # END Backward compatibility

    _validate_values(compdict)
    compdict = without_none_values(_map_keys(compdict))
    return [k for k, v in sorted(compdict.items(), key=itemgetter(1))]
