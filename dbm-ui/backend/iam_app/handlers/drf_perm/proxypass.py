# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import binascii
import logging

import redis
from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.exceptions import RSADecryptException
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_proxy.constants import (
    DB_CLOUD_TOKEN_EXPIRE_TIME,
    DB_CLOUD_TOKEN_LOCAL_CACHE_MAXSIZE,
    DB_CLOUD_TOKEN_LOCAL_CACHE_TTL,
)
from backend.utils.cache import LocalTTLCache
from backend.utils.local import local
from backend.utils.redis import RedisConn

logger = logging.getLogger("root")

# 只缓存校验通过的 token；失败不写入，避免把误拦截放大
_token_local_cache = LocalTTLCache(ttl=DB_CLOUD_TOKEN_LOCAL_CACHE_TTL, maxsize=DB_CLOUD_TOKEN_LOCAL_CACHE_MAXSIZE)


class ProxyPassPermission(permissions.BasePermission):
    """
    透传接口权限
    """

    @classmethod
    def verify_token(cls, db_cloud_token, bk_cloud_id):
        # 兼容云区域容器化，app_code:app_secret的鉴权模式
        if db_cloud_token == f"{settings.APP_CODE}:{settings.APP_TOKEN}":
            return

        try:
            token = AsymmetricHandler.decrypt(name=AsymmetricCipherConfigType.PROXYPASS.value, content=db_cloud_token)
        except (RSADecryptException, binascii.Error, KeyError, IndexError):
            raise PermissionDenied(_("db_cloud_token:{}解密失败，请检查token是否合法").format(db_cloud_token))

        token_cloud_id = int(token.split("_")[0])
        if token_cloud_id != int(bk_cloud_id):
            raise PermissionDenied(_("解析云区域(ID:{})与参数云区域(ID:{})不同，请检查token是否合法").format(token_cloud_id, bk_cloud_id))

    @classmethod
    def _ensure_token_verified(cls, db_cloud_token, bk_cloud_id):
        """L1 未命中时：查 Redis，再必要时解密校验并回写。仅成功路径返回 True 以写入本地缓存。"""
        redis_cache_key = f"cache_db_cloud_token_{bk_cloud_id}"

        try:
            token_cached = RedisConn.sismember(redis_cache_key, db_cloud_token)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            logger.error("[ProxyPassPermission]read token cache failed: %s", e)
            token_cached = False

        if not token_cached:
            cls.verify_token(db_cloud_token, bk_cloud_id)
            try:
                # 如果这个cache_key刚创建，则需要设置过期时间
                if not RedisConn.exists(redis_cache_key):
                    RedisConn.sadd(redis_cache_key, db_cloud_token)
                    RedisConn.expire(redis_cache_key, DB_CLOUD_TOKEN_EXPIRE_TIME)
                else:
                    RedisConn.sadd(redis_cache_key, db_cloud_token)
            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
                logger.error("[ProxyPassPermission]write token cache failed: %s", e)

        return True

    def has_permission(self, request, view):

        # 如果是直连区域的内部调用，不进行token校验
        if getattr(request, "internal_call", None):
            return True

        # token鉴权认证 + 缓存(L1 内存，L2 redis缓存，L3 rsa解密)
        db_cloud_token = request.data.get("db_cloud_token", "")
        bk_cloud_id = request.data.get("bk_cloud_id")
        _token_local_cache.get_or_load(
            (bk_cloud_id, db_cloud_token),
            lambda: self._ensure_token_verified(db_cloud_token, bk_cloud_id),
        )

        request.data.pop("db_cloud_token")

        # 通过鉴权后，修改调用方式为内部调用
        try:
            local_request = local.request or request
            local_request.internal_call = True
        except Exception:  # pylint: disable=broad-except
            pass

        return True
