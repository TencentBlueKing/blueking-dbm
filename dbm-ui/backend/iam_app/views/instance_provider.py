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

import logging
from typing import List

from django.db import models

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import StorageInstance
from backend.iam_app.dataclass.resources import ResourceMeta
from backend.iam_app.views.iam_provider import BaseModelResourceProvider

logger = logging.getLogger("root")


class InstanceResourceProvider(BaseModelResourceProvider):
    """
    集群资源的反向拉取基类
    """

    model: models.Model = StorageInstance
    resource_meta: ResourceMeta = None
    instance_roles: List[InstanceRole] = []

    def list_instance(self, filter, page, **options):
        filter.data_source = self.model
        filter.value_list = [self.resource_meta.lookup_field, *self.resource_meta.display_fields]
        filter.keyword_field = "machine__ip__icontains"
        filter.conditions = {"instance_role__in": self.instance_roles}
        return super().list_instance(filter, page, **options)

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def fetch_instance_info(self, filter, **options):
        filter.data_source = self.model
        return super().fetch_instance_info(filter, **options)

    def list_instance_by_policy(self, filter, page, **options):
        key_mapping = {
            f"{self.resource_meta.id}.id": "id",
            f"{self.resource_meta.id}.creator": "creator",
            f"{self.resource_meta.id}._bk_iam_path_": "bk_biz_id",
        }
        values_hook = {"bk_biz_id": lambda value: value[1:-1].split(",")[1]}
        return self._list_instance_by_policy(
            data_source=self.model,
            value_list=["id", "ip", "port"],
            key_mapping=key_mapping,
            value_hooks=values_hook,
            filter=filter,
            page=page,
        )


# TODO: 暂时屏蔽对influxdb的鉴权
# class InfluxDBInstanceResourceProvider(InstanceResourceProvider):
#     resource_meta: ResourceMeta = ResourceEnum.INFLUXDB
#     instance_roles: List[InstanceRole] = [InstanceRole.INFLUXDB]
