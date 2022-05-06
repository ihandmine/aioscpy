import pkgutil

from aioscpy.inject import call_grace_instance

__version__ = (pkgutil.get_data(__package__, "VERSION") or b"").decode("ascii").strip()

__all__ = [
    '__version__',
    'call_grace_instance'
]
