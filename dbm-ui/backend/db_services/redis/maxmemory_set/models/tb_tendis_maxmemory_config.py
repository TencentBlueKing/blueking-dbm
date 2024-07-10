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
from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.flow.consts import RedisMaxmemoryConfigType

"""
CREATE TABLE `tb_tendis_maxmemory_config` (
  `config_type` varchar(255) NOT NULL DEFAULT '',
  `config_data` text NOT NULL,
  PRIMARY KEY (`config_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


class TbTendisMaxmemoryConfig(models.Model):
    config_type = models.CharField(
        primary_key=True,
        max_length=255,
        choices=RedisMaxmemoryConfigType.get_choices(),
        default="",
        verbose_name=_("配置类型"),
    )
    config_data = models.TextField(default="", verbose_name=_("配置数据"))

    class Meta:
        db_table = "tb_tendis_maxmemory_config"
        verbose_name = _("redis maxmemory配置")
