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

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums.extra_process_type import ExtraProcessType

logger = logging.getLogger("root")


class ExtraProcessInstance(AuditedModel):
    """
    引入“附属”进程的概念，“附属”进程是指一类在DB机器安装在非DB进程，
    在DBM系统中，TBinlogDumper可以认为是这类的进程。
    1：这张表是以进程的维度进行存储，所以，进程信息作为唯一约束，
    如果DBM系统托管的是非监听端口的进程，listen_port设置默认0或者其他有意义的值即可。
    2：表中信息应该和db_meta其他的核心表做“割裂”，比如设置外键约束等，这样对之前写的代码不影响，但可以跟字段做隐形关联。
    """

    bk_biz_id = models.IntegerField(default=0, help_text=_("关联的业务id，对应cmdb"))
    cluster_id = models.IntegerField(default=0, help_text=_("关联的cluster_id"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("云区域 ID，对应cmdb"))
    ip = models.GenericIPAddressField(default="", help_text=_("IP 地址"))
    proc_type = models.CharField(
        max_length=64, choices=ExtraProcessType.get_choices(), default="", help_text=_("进程类型")
    )
    version = models.CharField(max_length=64, default="", help_text=_("版本号"))
    listen_port = models.PositiveIntegerField(default=0, help_text=_("进程监听端口"))
    extra_config = models.JSONField(default=dict, help_text=_("进程的定制化属性"))

    class Meta:
        unique_together = ("ip", "bk_cloud_id", "listen_port")
