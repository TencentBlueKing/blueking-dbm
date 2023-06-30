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
from django.utils.translation import ugettext_lazy as _

SWAGGER_TAG = _("资源池")

RESOURCE_IMPORT_TASK_FIELD = "{user}_resource_import_task_field"
RESOURCE_IMPORT_EXPIRE_TIME = 7 * 24 * 60 * 60

# gse正常的状态码为2
GSE_AGENT_RUNNING_CODE = 2


class ResourceOperation(str, StructuredEnum):
    import_hosts = EnumField("imported", _("导入主机"))
    consume_hosts = EnumField("consumed", _("消费主机"))
