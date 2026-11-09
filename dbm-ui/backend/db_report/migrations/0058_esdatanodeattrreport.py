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

from backend.db_meta.enums import ClusterType


class Migration(migrations.Migration):

    dependencies = [
        ("db_report", "0057_failoverdrillreport_version"),
    ]

    operations = [
        migrations.CreateModel(
            name="EsDatanodeAttrReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("creator", models.CharField(max_length=64, verbose_name="创建人")),
                ("create_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updater", models.CharField(max_length=64, verbose_name="修改人")),
                ("update_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("bk_biz_id", models.IntegerField(default=0, help_text="业务的 cmdb id")),
                ("bk_cloud_id", models.IntegerField(default=0, help_text="云区域 id")),
                ("status", models.BooleanField(default=True, help_text="巡检结果状态, 默认正常")),
                ("state", models.CharField(default="", help_text="巡检结果状态", max_length=64)),
                ("failed_days", models.IntegerField(default=0, help_text="失败持续天数")),
                ("msg", models.TextField(default="", help_text="备注信息")),
                ("domain", models.CharField(default="", max_length=255)),
                ("app", models.CharField(max_length=100, verbose_name="业务名")),
                ("dba", models.JSONField(verbose_name="业务所属dba")),
                (
                    "cluster_type",
                    models.CharField(choices=ClusterType.get_choices(), default="", help_text="集群类型", max_length=64),
                ),
                ("ip", models.CharField(default="", max_length=64, verbose_name="节点IP")),
                ("node_name", models.CharField(default="", max_length=255, verbose_name="节点名称")),
                ("node_role", models.CharField(default="", max_length=32, verbose_name="节点角色")),
                ("es_idc_id", models.CharField(default="", max_length=64, verbose_name="ES配置机房ID")),
                ("meta_idc_id", models.IntegerField(default=0, verbose_name="元数据机房ID")),
                ("es_rack_id", models.CharField(default="", max_length=64, verbose_name="ES配置机架ID")),
                ("meta_rack_id", models.IntegerField(default=0, verbose_name="元数据机架ID")),
                ("es_sub_zone_id", models.CharField(default="", max_length=64, verbose_name="ES配置园区ID")),
                ("meta_sub_zone_id", models.IntegerField(default=0, verbose_name="元数据园区ID")),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
