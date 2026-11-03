"""JOB 回调凭证，成功处理后删除，超时由 Redis 自动清理。"""

import hashlib
import re
import secrets
from urllib.parse import urlencode

from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied

from backend import env
from backend.db_proxy.constants import JOB_CALLBACK_TOKEN_EXPIRE_TIME
from backend.utils.redis import RedisConn


def _token_key(action, token):
    digest = hashlib.sha256(token.encode()).hexdigest()
    return f"dbm:job_callback:{action}:{digest}"


def build_job_callback_url(action):
    """为每个作业签发独立的限时凭证，并绑定具体回调接口。"""
    token = secrets.token_urlsafe(32)
    RedisConn.set(_token_key(action, token), "valid", ex=JOB_CALLBACK_TOKEN_EXPIRE_TIME)
    return f"{env.BK_SAAS_CALLBACK_URL}/apis/proxypass/{action}/?{urlencode({'token': token})}"


def verify_job_callback_token(action, token):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise PermissionDenied(_("无效或已过期的 JOB 回调凭证"))
    # Redis 异常时向上抛出，禁止绕过认证。
    key = _token_key(action, token)
    if not RedisConn.exists(key):
        raise PermissionDenied(_("无效或已过期的 JOB 回调凭证"))
    return key
