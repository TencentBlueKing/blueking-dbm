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
from typing import Dict

from django.db import models

from backend.db_monitor.models import MonitorPolicy
from backend.iam_app.dataclass.resources import MonitorPolicyResourceMeta, ResourceEnum
from backend.iam_app.handlers.converter import MonitorDjangoQuerySetConverter
from backend.iam_app.views.iam_provider import BaseModelResourceProvider

logger = logging.getLogger("root")


class MonitorPolicyResourceProvider(BaseModelResourceProvider):
    """
    监控策略资源的反向拉取基类
    """

    model: models.Model = MonitorPolicy
    resource_meta: MonitorPolicyResourceMeta = ResourceEnum.MONITOR_POLICY

    @staticmethod
    def parse_iam_path(iam_path):
        if iam_path.count("/") == 2:
            # 只有一层拓扑层级，说明只有dbtype
            return {
                "bk_biz_id": "0",
                "db_type": iam_path.split("/")[1].split(",")[-1],
            }
        else:
            return {
                "bk_biz_id": iam_path.split("/")[1].split(",")[-1],
                "db_type": iam_path.split("/")[2].split(",")[-1],
            }

    def get_bk_iam_path(self, instance_ids, *args, **kwargs) -> Dict:
        """获取带有模型实例的bk_iam_path"""
        instances = self.model.objects.filter(pk__in=instance_ids)
        id__bk_iam_path = {instance.id: self.resource_meta.get_bk_iam_path(instance) for instance in instances}
        return id__bk_iam_path

    def list_instance(self, filter, page, **options):
        logger.info("list_instance params: %s, %s, %s", filter, page, options)
        filter.data_source = self.model
        filter.value_list = [self.resource_meta.lookup_field, *self.resource_meta.display_fields]
        filter.keyword_field = "name__icontains"
        # 默认给上bk_biz_id=0的过滤，如果监控有业务层级，则被覆盖不影响
        filter.conditions = {"bk_biz_id": 0}
        return super().list_instance(filter, page, **options)

    def search_instance(self, filter, page, **options):
        logger.info("search_instance params: %s, %s, %s", filter, page, options)
        return self.list_instance(filter, page, **options)

    def list_instance_by_policy(self, filter, page, **options):
        logger.info("list_instance_by_policy params: %s, %s, %s", filter, page, options)
        key_mapping = {
            f"{self.resource_meta.id}.id": "id",
            f"{self.resource_meta.id}.creator": "creator",
            f"{self.resource_meta.id}._bk_iam_path_": "bk_biz_id,db_type",
        }
        value_hooks = {"bk_biz_id,db_type": self.parse_iam_path}
        converter_class = options.get("converter_class", MonitorDjangoQuerySetConverter)
        return self._list_instance_by_policy(
            data_source=self.model,
            value_list=["id", "name"],
            key_mapping=key_mapping,
            value_hooks=value_hooks,
            filter=filter,
            page=page,
            converter_class=converter_class,
        )
