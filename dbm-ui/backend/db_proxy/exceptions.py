# -*- coding: utf-8 -*-

from backend.exceptions import AppBaseException, ErrorCode


class ProxyPassBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.PROXY_PASS_CODE
