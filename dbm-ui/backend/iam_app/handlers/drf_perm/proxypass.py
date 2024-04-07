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

from django.utils.translation import gettext as _
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.exceptions import RSADecryptException
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_proxy.constants import DB_CLOUD_TOKEN_EXPIRE_TIME
from backend.utils.redis import RedisConn


class ProxyPassPermission(permissions.BasePermission):
    """
    透传接口权限
    """

    @classmethod
    def verify_token(cls, db_cloud_token, bk_cloud_id):
        try:
            token = AsymmetricHandler.decrypt(name=AsymmetricCipherConfigType.PROXYPASS.value, content=db_cloud_token)
        except (RSADecryptException, binascii.Error, KeyError, IndexError):
            raise PermissionDenied(_("db_cloud_token:{}解密失败，请检查token是否合法").format(db_cloud_token))

        token_cloud_id = int(token.split("_")[0])
        if token_cloud_id != int(bk_cloud_id):
            raise PermissionDenied(
                _("解析的云区域(ID:{})与请求参数的云区域(ID:{})不相同，请检查token是否合法").format(token_cloud_id, bk_cloud_id)
            )

    def has_permission(self, request, view):

        # 如果是直连区域的内部调用，不进行token校验
        if getattr(request, "internal_call", None):
            return True

        db_cloud_token = request.data.get("db_cloud_token", "")
        bk_cloud_id = request.data.get("bk_cloud_id")
        cache_key = f"cache_db_cloud_token_{bk_cloud_id}"
        # 判断是否在缓存集合中，不在cache中则走解密流程并cache。
        # 由于Redis的list不能直接判断元素是否存在，所以选择set存取
        if not RedisConn.sismember(cache_key, db_cloud_token):
            self.verify_token(db_cloud_token, bk_cloud_id)
            # 如果这个cache_key刚创建，则需要设置过期时间
            if not RedisConn.exists(cache_key):
                RedisConn.sadd(cache_key, db_cloud_token)
                RedisConn.expire(cache_key, DB_CLOUD_TOKEN_EXPIRE_TIME)
            else:
                RedisConn.sadd(cache_key, db_cloud_token)
        request.data.pop("db_cloud_token")
        return True
