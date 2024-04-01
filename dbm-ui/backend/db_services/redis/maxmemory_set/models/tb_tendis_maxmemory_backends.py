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

"""
CREATE TABLE `tb_tendis_maxmemory_backends` (
  `cluster_domain` varchar(255) NOT NULL DEFAULT '',
  `backends` longtext NOT NULL,
  `update_time` datetime(6) NOT NULL,
  PRIMARY KEY (`cluster_domain`),
  KEY `idx_update_time` (`update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


class TbTendisMaxmemoryBackends(models.Model):
    cluster_domain = models.CharField(primary_key=True, max_length=255, default="", verbose_name=_("集群域名"))
    backends = models.TextField(default="", verbose_name=_("backends"))
    update_time = models.DateTimeField(verbose_name=_("更新时间"))

    class Meta:
        db_table = "tb_tendis_maxmemory_backends"
        indexes = [
            models.Index(fields=["update_time"], name="idx_maxmemory_update_time"),
        ]
