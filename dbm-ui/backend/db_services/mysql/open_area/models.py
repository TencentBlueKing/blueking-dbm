"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.constants import DEFAULT_BK_CLOUD_ID


class TendbOpenAreaConfig(AuditedModel):
    """开区模板表"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID"))
    config_name = models.CharField(max_length=256, help_text=_("开区模板名"))
    source_cluster_id = models.BigIntegerField(help_text=_("源集群ID"))
    config_rules = models.JSONField(help_text=_("模板克隆规则列表"))
    related_authorize = models.JSONField(help_text=_("关联的规则列表(目前用于级联规则的修改删除)"))

    class Meta:
        # 不允许同个业务下出现同名模板配置
        unique_together = ("bk_biz_id", "config_name")


class TendbOpenAreaConfigLog(AuditedModel):
    """开区配置表的修改记录表，用于DBA日常回顾"""

    bk_biz_id = models.IntegerField(default=0)
    config_name = models.CharField(max_length=256, default="")
    config_change_log = models.JSONField(help_text=_("开区配置修改记录数据"))
