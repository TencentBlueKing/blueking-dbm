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


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DnsDomain",
            fields=[
                ("creator", models.CharField(max_length=64, verbose_name="创建人")),
                ("create_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updater", models.CharField(max_length=64, verbose_name="修改人")),
                ("update_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("domain", models.CharField(max_length=253, primary_key=True, serialize=False, verbose_name="完整域名")),
                (
                    "maintain_type",
                    models.CharField(
                        choices=[("self", "自主维护"), ("cluster", "集群托管")],
                        default="self",
                        max_length=32,
                        verbose_name="维护方式",
                    ),
                ),
                ("remark", models.CharField(blank=True, default="", max_length=500, verbose_name="备注")),
                ("owners", models.JSONField(default=list, verbose_name="负责人")),
                ("bk_biz_id", models.IntegerField(default=0, verbose_name="业务ID")),
                ("bk_cloud_id", models.IntegerField(default=0, verbose_name="云区域ID")),
            ],
            options={
                "verbose_name": "域名(DnsDomain)",
                "verbose_name_plural": "域名(DnsDomain)",
                "db_table": "dns_domain",
            },
        ),
        migrations.CreateModel(
            name="DnsDomainAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain", models.CharField(db_index=True, max_length=253, verbose_name="完整域名")),
                ("operator", models.CharField(max_length=64, verbose_name="操作人")),
                ("client_ip", models.CharField(blank=True, default="", max_length=64, verbose_name="客户端IP")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "创建域名"),
                            ("update_ip", "修改 IP"),
                            ("update_remark", "修改备注"),
                            ("update_owner", "修改负责人"),
                            ("delete", "删除域名"),
                        ],
                        max_length=32,
                        verbose_name="操作类型",
                    ),
                ),
                ("change_lines", models.JSONField(default=list, verbose_name="变更内容")),
                ("create_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="时间")),
            ],
            options={
                "verbose_name": "域名操作日志(DnsDomainAuditLog)",
                "verbose_name_plural": "域名操作日志(DnsDomainAuditLog)",
                "db_table": "dns_domain_audit_log",
            },
        ),
        migrations.AddIndex(
            model_name="dnsdomainauditlog",
            index=models.Index(fields=["domain", "create_at"], name="dns_audit_domain_time_idx"),
        ),
    ]
