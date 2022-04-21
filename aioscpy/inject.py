import asyncio

from importlib import import_module
from pkgutil import iter_modules

from aioscpy.settings import Settings


class Slot:

    def __init__(self, settings, crawler):
        self._objects_slot = {
            'settings': settings,
            'crawler': crawler
        }
        self._modules_slot = []
        self._close = None
        self.live_beat = None

    @property
    def is_live(self):
        return bool(self._close)

    def get(self, sets: str, default=None) -> object:
        return self._objects_slot.get(sets, default)

    def set(self, sets: str, obj: object):
        self._objects_slot.__setitem__(sets, obj)

    def remove(self, sets: str):
        self._objects_slot.pop(sets)

    def clear(self):
        del self._objects_slot
        self._modules_slot = []
        self._close = True

    def close(self):
        if self.live_beat:
            self.live_beat.cancel()


class DependencyInjection(object):
    def __init__(self, settings: Settings, crawler):
        if not settings:
            settings = Settings()
        self.settings = settings
        self.crawler = crawler
        self.slot = Slot(settings, crawler)

    @classmethod
    def from_settings(cls, settings, crawler):
        return cls(settings, crawler)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings, crawler)

    def load(self, key):
        return self.slot.get(key)

    def load_object_slot(self, key: str, path: str):
        try:
            dot = path.rindex('.')
        except ValueError:
            raise ValueError("Error loading object '%s': not a full path" % path)

        module, name = path[:dot], path[dot + 1:]
        mod = import_module(module)

        try:
            obj = getattr(mod, name)
        except AttributeError:
            raise NameError("Module '%s' doesn't define any object named '%s'" % (module, name))

        self.slot.set(key, self.create_instance(obj, self.settings, self.crawler))

    def walk_modules(self, path: str):
        mods = self.slot._modules_slot
        mod = import_module(path)
        mods.append(mod)
        if hasattr(mod, '__path__'):
            for _, subpath, ispkg in iter_modules(mod.__path__):
                fullpath = path + '.' + subpath
                if ispkg:
                    mods += self.walk_modules(fullpath)
                else:
                    submod = import_module(fullpath)
                    mods.append(submod)
        return mods

    def create_instance(self, objcls, settings, crawler, *args, **kwargs):
        if settings is None:
            if crawler is None:
                raise ValueError("Specify at least one of settings and crawler.")
            settings = crawler.settings
        if crawler and hasattr(objcls, 'from_crawler'):
            return objcls.from_crawler(crawler, *args, **kwargs)
        elif hasattr(objcls, 'from_settings'):
            return objcls.from_settings(settings, *args, **kwargs)
        else:
            return objcls(*args, **kwargs)

    async def runner(self):
        if not self.settings.get('DI_CONFIG'):
            raise KeyError('Settings DI config must not be None')
        for key, value in self.settings['DI_CONFIG'].items():
            self.load_object_slot(key, value)
        self.slot.live_beat = asyncio.create_task(self.live_beat())

    async def live_beat(self):
        while 1:
            if not self.slot.is_live:
                await asyncio.sleep(20)
                break
            asyncio.create_task(self.runner())
