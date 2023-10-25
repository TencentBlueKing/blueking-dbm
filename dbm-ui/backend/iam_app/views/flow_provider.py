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

from backend.flow.models import FlowTree
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.views.iam_provider import BaseResourceProvider, CommonProviderMixin

logger = logging.getLogger("root")


class FlowResourceProvider(BaseResourceProvider, CommonProviderMixin):
    """
    flow资源的反向拉取类
    """

    model: models.Model = FlowTree
    resource_meta: ResourceMeta = ResourceEnum.TASKFLOW

    def get_bk_iam_path(self, instance_ids, *args, **kwargs) -> Dict:
        return super().get_model_bk_iam_path(self.model, instance_ids, *args, **kwargs)

    def list_attr(self, **options):
        return self._list_attr(id=self.resource_meta.attribute, display_name=self.resource_meta.attribute_display)

    def list_attr_value(self, filter, page, **options):
        user_resource = self.list_user_resource()
        return self._list_attr_value(self.resource_meta.attribute, user_resource, filter, page, **options)

    def list_instance(self, filter, page, **options):
        filter.model = self.model
        filter.value_list = [self.resource_meta.lookup_field, *self.resource_meta.display_fields]
        filter.keyword_field = "root_id"
        return super().list_instance(filter, page, **options)

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def list_instance_by_policy(self, filter, page, **options):
        key_mapping = {
            f"{self.resource_meta.id}.id": "root_id",
            f"{self.resource_meta.id}.created_by": "created_by",
            f"{self.resource_meta.id}._bk_iam_path_": "bk_biz_id",
        }
        values_hook = {"bk_biz_id": lambda value: value[1:-1].split(",")[1]}
        return self._list_instance_by_policy(
            obj_model=self.model,
            # root_id 同时作为id和display name
            value_list=["root_id", "root_id"],
            key_mapping=key_mapping,
            value_hooks=values_hook,
            filter=filter,
            page=page,
        )
