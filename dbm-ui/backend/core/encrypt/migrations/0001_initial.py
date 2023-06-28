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
# Generated by Django 3.2.4 on 2022-08-22 13:18

from django.db import migrations, models

from backend.core.encrypt.constants import RSAKeyType


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RSAKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128, verbose_name="密钥名称")),
                (
                    "type",
                    models.CharField(choices=RSAKeyType.get_choices(), max_length=64, verbose_name="密钥类型"),
                ),
                ("description", models.TextField(default="", null=True, verbose_name="密钥描述")),
                ("content", models.TextField(verbose_name="密钥内容")),
                ("update_time", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
            ],
            options={
                "verbose_name": "RSA密钥",
                "verbose_name_plural": "RSA密钥",
                "unique_together": {("name", "type")},
            },
        ),
    ]
