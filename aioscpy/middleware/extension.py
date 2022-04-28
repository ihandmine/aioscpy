from aioscpy.middleware.manager import MiddlewareManager
from aioscpy.utils.common import build_component_list


class ExtensionManager(MiddlewareManager):

    component_name = 'extension'

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        return build_component_list(settings.getwithbase('EXTENSIONS'))
