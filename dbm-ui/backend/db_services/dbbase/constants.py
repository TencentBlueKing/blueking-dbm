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
from django.utils.translation import ugettext_lazy as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

ES_DEFAULT_PORT = 9200

# 用户指定访问HDFS的WEB端口，默认50070，禁用2181，8480，8485
HDFS_DEFAULT_HTTP_PORT = 50070

# 用户指定访问HDFS的RPC端口，默认9000，禁用2181，8480，8485，不能与http_port相同
HDFS_DEFAULT_RPC_PORT = 9000

KAFKA_DEFAULT_PORT = 9200

IP_PORT_DIVIDER = ":"
SPACE_DIVIDER = " "


class IpSource(str, StructuredEnum):
    """主机来源枚举"""

    MANUAL_INPUT = EnumField("manual_input", _("手动录入"))
    RESOURCE_POOL = EnumField("resource_pool", _("资源池"))
