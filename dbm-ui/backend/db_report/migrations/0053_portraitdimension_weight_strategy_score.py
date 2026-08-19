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

from backend.db_report.enums import SummaryFetchStrategy


class Migration(migrations.Migration):

    dependencies = [
        ("db_report", "0052_clusterportraitreport"),
    ]

    operations = [
        migrations.AddField(
            model_name="portraitdimensionregistry",
            name="weight",
            field=models.FloatField(
                blank=True,
                default=None,
                help_text="该维度在画像综合评分中的计算权重，为空表示未配置",
                null=True,
                verbose_name="权重",
            ),
        ),
        migrations.AddField(
            model_name="portraitdimensionregistry",
            name="summary_fetch_strategy",
            field=models.CharField(
                choices=SummaryFetchStrategy.get_choices(),
                default="all",
                help_text="获取该维度摘要结果的策略：all 返回全部 / last 返回最新一条 / first 返回最老一条",
                max_length=16,
                verbose_name="摘要获取策略",
            ),
        ),
        migrations.AddField(
            model_name="portraitdimensionsummary",
            name="score",
            field=models.FloatField(
                blank=True,
                default=None,
                help_text="本次巡检摘要结果的分数，为空表示未上报",
                null=True,
                verbose_name="分数",
            ),
        ),
    ]
