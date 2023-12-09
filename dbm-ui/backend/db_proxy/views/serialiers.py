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

from django.utils.translation import ugettext as _
from rest_framework import serializers

logger = logging.getLogger("root")


class BaseProxyPassSerializer(serializers.Serializer):
    """
    所有透传接口的基类，每个透传接口必须包含加密的token，用于校验身份和获取参数信息
    """

    db_cloud_token = serializers.CharField(help_text=_("调用的校验token"), required=False)
    bk_cloud_id = serializers.IntegerField(help_text=_("请求服务所属的云区域ID"), required=False)
