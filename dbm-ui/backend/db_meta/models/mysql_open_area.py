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
    bk_biz_id = models.IntegerField(default=0)
    bk_cloud_id = models.IntegerField(default=DEFAULT_BK_CLOUD_ID, help_text=_("云区域 ID"))
    config_name = models.CharField(max_length=256, default="")
    domain_name = models.CharField(max_length=256, default="")
    source_cluster_id = models.BigIntegerField(default=0)
    cluster_type = models.CharField(max_length=64, default="")

    class Meta:
        unique_together = ("bk_biz_id", "domain_name", "source_cluster_id", "cluster_type")


class TendbOpenAreaSubConfig(AuditedModel):
    config = models.ManyToManyField(TendbOpenAreaConfig, blank=True)
    db_schema_source_db = models.CharField(max_length=256, help_text=_("获取库表结构的源db"), unique=True)
    # json字段，直接存储待克隆表结构列表，克隆所有表时为空列表
    db_schema_source_tblist = models.JSONField(help_text=_("获取表结构的源tb列表"), default=list)
    # json字段，直接存储待克隆表数据列表，隆所有表时为空列表
    db_data_source_tblist = models.JSONField(help_text=_("获取数据的源tb列表"), default=list)
    db_schema_source_db_model = models.CharField(max_length=256, help_text=_("目标db范式"))
    # json字段，存储权限模板列表
    priv_init_id = models.JSONField(help_text=_("权限关联模板id"), default=list)
    creator = models.CharField(max_length=100)
    create_time = models.DateTimeField(auto_now_add=True, help_text=_("配置创建时间"))
    updater = models.CharField(max_length=100)
    update_time = models.DateTimeField(auto_now=True, help_text=_("配置创建时间"))

    class Meta:
        unique_together = (
            "db_schema_source_db",
            "db_schema_source_db_model",
            "db_schema_source_tblist",
            "db_data_source_tblist",
        )


class TendbOpenAreaConfigLog(AuditedModel):
    config = models.ManyToManyField(TendbOpenAreaConfig, blank=True)
    operator = models.CharField(max_length=100)
    operate_time = models.DateTimeField(auto_now=True, help_text=_("配置修改时间"))
    config_change_log = models.JSONField(help_text=_("开区配置修改记录"))
