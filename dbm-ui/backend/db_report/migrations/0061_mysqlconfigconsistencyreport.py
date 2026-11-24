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
from django.db import migrations, models
from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.db_report.enums.mysql_config_consistency_sub_type import MysqlConfigConsistencySubType


class Migration(migrations.Migration):

    dependencies = [
        ("db_report", "0060_alter_mysqlclusterskewreport_cluster_type_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MysqlConfigConsistencyReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("creator", models.CharField(max_length=64, verbose_name=_("创建人"))),
                ("create_at", models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))),
                ("updater", models.CharField(max_length=64, verbose_name=_("修改人"))),
                ("update_at", models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))),
                ("bk_biz_id", models.IntegerField(default=0, help_text=_("业务的 cmdb id"))),
                ("bk_cloud_id", models.IntegerField(default=0, help_text=_("云区域 id"))),
                ("status", models.BooleanField(default=True, help_text=_("巡检结果状态, 默认正常"))),
                ("state", models.CharField(default="", help_text=_("巡检结果状态"), max_length=64)),
                ("failed_days", models.IntegerField(default=0, help_text=_("失败持续天数"))),
                ("msg", models.TextField(default="", help_text=_("备注信息"))),
                ("cluster_id", models.IntegerField(default=0, help_text=_("集群ID"))),
                ("cluster", models.CharField(default="", help_text=_("集群域名"), max_length=255)),
                (
                    "cluster_type",
                    models.CharField(
                        choices=ClusterType.get_choices(),
                        default="",
                        help_text=_("集群类型"),
                        max_length=64,
                    ),
                ),
                (
                    "subtype",
                    models.CharField(
                        choices=MysqlConfigConsistencySubType.get_choices(),
                        default="",
                        help_text=_("检查项"),
                        max_length=64,
                    ),
                ),
                ("diff_count", models.IntegerField(default=0, help_text=_("差异配置项数量"))),
                ("high_impact_count", models.IntegerField(default=0, help_text=_("高危差异配置项数量"))),
                ("diff_variables", models.JSONField(default=list, help_text=_("差异配置项列表"))),
                ("diff_detail", models.JSONField(default=dict, help_text=_("差异详情JSON"))),
            ],
            options={
                "verbose_name": _("MySQL配置一致性巡检报告"),
                "verbose_name_plural": _("MySQL配置一致性巡检报告"),
                "db_table": "tb_mysql_config_consistency_report",
                "managed": True,
                "indexes": [
                    models.Index(fields=["cluster_id", "subtype", "create_at"], name="idx_cfg_consist_cid_sub_at"),
                    models.Index(fields=["cluster_type", "subtype", "create_at"], name="idx_cfg_consist_type_sub_at"),
                    models.Index(fields=["state", "create_at"], name="idx_cfg_consist_state_at"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="mysqlconfigconsistencyreport",
            constraint=models.UniqueConstraint(
                fields=("cluster_id", "subtype"),
                name="uniq_cfg_consist_cid_sub",
            ),
        ),
    ]
