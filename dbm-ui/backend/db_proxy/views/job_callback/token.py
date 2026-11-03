"""JOB 回调的限次凭证，不限制有效时间。"""

import hashlib
import re
import secrets
from urllib.parse import urlencode

from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied

from backend import env
from backend.db_proxy.constants import JOB_CALLBACK_TOKEN_MAX_USES
from backend.utils.redis import RedisConn

# 原子校验并扣减剩余次数，防止并发回调重复使用同一凭证。
_CONSUME_TOKEN_SCRIPT = """
local remaining = tonumber(redis.call('GET', KEYS[1]))
if not remaining or remaining <= 0 then
    return 0
end
if remaining == 1 then
    redis.call('DEL', KEYS[1])
else
    redis.call('DECR', KEYS[1])
end
return 1
"""


def _token_key(action, token):
    digest = hashlib.sha256(token.encode()).hexdigest()
    return f"dbm:job_callback:{action}:{digest}"


def build_job_callback_url(action):
    """为每个作业签发独立的限次凭证，并绑定具体回调接口。"""
    token = secrets.token_urlsafe(32)
    RedisConn.set(_token_key(action, token), JOB_CALLBACK_TOKEN_MAX_USES)
    return f"{env.BK_SAAS_CALLBACK_URL}/apis/proxypass/{action}/?{urlencode({'token': token})}"


def verify_job_callback_token(action, token):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise PermissionDenied(_("无效或使用次数已耗尽的 JOB 回调凭证"))
    # Redis 异常时向上抛出，禁止绕过认证。
    if not RedisConn.eval(_CONSUME_TOKEN_SCRIPT, 1, _token_key(action, token)):
        raise PermissionDenied(_("无效或使用次数已耗尽的 JOB 回调凭证"))
