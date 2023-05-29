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
import logging

from bkoauth.jwt_client import JWTClient
from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.core.encrypt.constants import RSAConfigType
from backend.core.encrypt.exceptions import RSADecryptException
from backend.core.encrypt.handlers import RSAHandler

logger = logging.getLogger("root")


class BaseProxyPassSerialier(serializers.Serializer):
    """
    所有透传接口的基类，每个透传接口必须包含加密的token，用于校验身份和获取参数信息
    """

    db_cloud_token = serializers.CharField(help_text=_("调用的校验token"), required=False)
    bk_cloud_id = serializers.IntegerField(help_text=_("请求服务所属的云区域ID"), required=False)

    def validate(self, attrs):
        request = self.context["request"]

        # 如果带有jwt认证，则认为是apigw调用的，不进行token检验
        if JWTClient(request).is_valid:
            return attrs

        # 如果是直连区域的内部调用，不进行token校验
        if getattr(request, "internal_call", None):
            return attrs

        rsa = RSAHandler.get_or_generate_rsa_in_db(name=RSAConfigType.PROXYPASS.value)
        try:
            token = RSAHandler.decrypt_password(rsa.rsa_private_key.content, attrs["db_cloud_token"])
        except RSADecryptException:
            # TODO 联调的时候暂时去掉校验逻辑
            # raise serializers.ValidationError(_("token:{}解密失败，请检查token是否合法").format(attrs["db_cloud_token"]))
            attrs.pop("db_cloud_token")
            return attrs
        except KeyError:
            # raise serializers.ValidationError(_("token:{}不存在，请传入校验token").format(attrs["db_cloud_token"]))
            pass

        token_cloud_id = int(token.split("_")[0])
        if token_cloud_id != int(attrs["bk_cloud_id"]):
            logger.info(_("解析的云区域ID{}与请求参数的云区域ID{}不相同，请检查token是否合法").format(token_cloud_id, attrs["bk_cloud_id"]))
            # raise serializers.ValidationError(
            #     _("解析的云区域ID{}与请求参数的云区域ID{}不相同，请检查token是否合法").format(
            #         token_cloud_id, attrs["bk_cloud_id"]
            #     )
            # )

        attrs.pop("db_cloud_token")
        return attrs


class JobCallBackSerializer(serializers.Serializer):
    job_instance_id = serializers.IntegerField(help_text=_("作业实例ID"))
    status = serializers.IntegerField(help_text=_("作业状态码"))
    step_instance_list = serializers.ListField(help_text=_("步骤块中包含的各个步骤执行状态"), child=serializers.DictField())
