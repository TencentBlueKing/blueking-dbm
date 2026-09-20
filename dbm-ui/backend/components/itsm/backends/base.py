# -*- coding: utf-8 -*-


class BaseItsmBackend:
    """按版本注册 ITSM 后端的基类。"""

    version = ""
    backends = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.version:
            cls.backends[cls.version] = cls
