from aioscpy.inject import CSlot, DependencyInjection


class object_ref(type):
    def __init__(msc, *args, **kwargs):
        msc.ref = CSlot()
        if msc.ref.empty():
            DependencyInjection().inject()
        msc.logger = msc.ref.get("log").logger
        super().__init__(*args, **kwargs)


__version__ = "0.0.1"
