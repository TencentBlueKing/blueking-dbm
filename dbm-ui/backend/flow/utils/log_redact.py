# -*- coding: utf-8 -*-
"""Strip secrets before they are written to flow logs."""

import re

# mongodb://user:secret@host
_MONGO_URI = re.compile(r"(mongodb(?:\+srv)?://[^:\s'\"@]+:)([^@\s'\"]+)(@)")
_CLI_VALUE = r"('[^']*'|\"[^\"]*\"|\S+)"
# --password=secret / --password secret
_CLI_LONG_PASSWORD = re.compile(r"(?i)(--password(?:=|\s+))" + _CLI_VALUE)
# mongosh -u user -p secret / mysql -uuser -psecret。只认跟在 -u 后面的 -p，避免误伤 mkdir -p、-P 端口。
_CLI_USER_PASSWORD = re.compile(r"((?<!\S)-u\s*\S+\s+-p\s*)" + _CLI_VALUE)
# -p'secret' / -p"secret"：紧跟引号的 -p 只会是密码
_CLI_QUOTED_PASSWORD = re.compile(r"((?<!\S)-p)('[^']*'|\"[^\"]*\")")
# JS createUser pwd:'secret' and Python/JSON adminPassword
_NAMED_PASSWORD = re.compile(
    r"(?i)((?:['\"]?(?:admin_?password|password|passwd|pwd)['\"]?)\s*[:=]\s*)('[^']*'|\"[^\"]*\")"
)


def redact_log_secrets(msg):
    """Replace credential values. Non-strings are returned unchanged."""
    if not isinstance(msg, str) or not msg:
        return msg
    msg = _MONGO_URI.sub(r"\1***\3", msg)
    msg = _CLI_LONG_PASSWORD.sub(r"\1***", msg)
    msg = _CLI_USER_PASSWORD.sub(r"\1***", msg)
    msg = _CLI_QUOTED_PASSWORD.sub(r"\1***", msg)
    msg = _NAMED_PASSWORD.sub(r"\1'***'", msg)
    return msg


class RedactingLogMixin:
    """Redact secrets in this component's logs. Does not change BaseService."""

    def log_info(self, msg):
        super().log_info(redact_log_secrets(msg))

    def log_error(self, msg):
        super().log_error(redact_log_secrets(msg))

    def log_warning(self, msg):
        super().log_warning(redact_log_secrets(msg))

    def log_debug(self, msg):
        super().log_debug(redact_log_secrets(msg))

    def log_exception(self, msg):
        super().log_exception(redact_log_secrets(msg))
