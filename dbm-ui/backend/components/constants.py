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

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _

SSL_KEY = "DBM_SSL"
CLIENT_CRT_PATH = "backend/components/conf/ssl"


class SSLEnum(str, StructuredEnum):
    SERVER_CRT = EnumField("server.crt", _("服务器证书文件"))
    SERVER_KEY = EnumField("server.key", _("服务器私钥"))
    CLIENT_CRT = EnumField("client.crt", _("客户端证书文件"))
    CLIENT_KEY = EnumField("client.key", _("客户端私钥"))
