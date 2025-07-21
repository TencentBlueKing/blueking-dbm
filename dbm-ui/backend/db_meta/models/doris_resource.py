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
from backend.flow.utils.doris.consts import DorisResourceGrant, DorisResourceTag

logger = logging.getLogger("root")


class DorisResource(AuditedModel):
    """
    定义doris集群申请远程存储资源记录表，存储doris管理资源记录信息
    doris专用
    """

    # 冗余业务Id, 兼容非DBA业务申请的资源录入
    bk_biz_id = models.IntegerField(default=0, help_text=_("关联的业务id，对应cmdb"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("云区域 ID"))
    # 资源名称，保持唯一，可被直接检索get
    name = models.CharField(max_length=255, unique=True, help_text=_("资源名称，唯一"))
    bucket_name = models.CharField(max_length=255, help_text=_("存储桶名称"))
    region = models.CharField(max_length=64, help_text=_("地域"))
    endpoint = models.CharField(max_length=255, help_text=_("API地址"))
    root_path = models.CharField(max_length=255, default="/data", help_text=_("存储桶目录名"))
    # 绑定已存在的资源时标记是否能被绑定，不启用时资源亦存在
    enable = models.BooleanField(help_text=_("是否启用"), default=True)
    # 资源标记: 区分独立集群或公共存储资源，公共集群用于Doris集群导出功能使用
    tag = models.CharField(max_length=64, choices=DorisResourceTag.get_choices(), help_text=_("资源标记: public|private"))
    # 是否由DBM完全管控
    control = models.CharField(max_length=64, choices=DorisResourceGrant.get_choices(), help_text=_("dbm|others"))
    # 云账号ID, 用于从密码服务获取访问存储资源密钥
    account_id = models.CharField(max_length=255, help_text=_("访问账号ID"))

    class Meta:
        verbose_name = verbose_name_plural = _("doris资源记录表")
