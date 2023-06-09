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
# Generated by Django 3.2.4 on 2023-03-07 13:01

from django.db import migrations, models

from backend.core.encrypt.constants import RSAConfigType


class Migration(migrations.Migration):

    dependencies = [
        ("encrypt", "0003_alter_rsakey_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rsakey",
            name="name",
            field=models.CharField(
                choices=RSAConfigType.get_choices(),
                max_length=128,
                verbose_name="密钥名称",
            ),
        ),
    ]
