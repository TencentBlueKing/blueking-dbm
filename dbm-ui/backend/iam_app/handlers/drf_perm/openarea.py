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

from typing import List

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.exceptions import ActionNotExistError
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id


class OpenareaConfigPermission(ResourceActionPermission):
    """
    告警组相关动作鉴权
    """

    def __init__(self, view_action, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        self.view_action = view_action
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 从业务或告警组后，决定动作和资源类型
        bk_biz_id = view.kwargs["bk_biz_id"]
        if self.view_action == "create":
            cluster_type = get_request_key_id(request, key="cluster_type")
            db_type = ClusterType.cluster_type_to_db_type(cluster_type)
            self.actions = [getattr(ActionEnum, f"{db_type.upper()}_OPENAREA_CONFIG_CREATE")]
            self.resource_meta = ResourceEnum.BUSINESS
            return [bk_biz_id]
        elif self.view_action in ["update", "destroy"]:
            config = TendbOpenAreaConfig.objects.get(id=view.kwargs["pk"])
            db_type = ClusterType.cluster_type_to_db_type(config.cluster_type)
            self.actions = [getattr(ActionEnum, f"{db_type.upper()}_OPENAREA_CONFIG_{self.view_action.upper()}")]
            self.resource_meta = ResourceEnum.OPENAREA_CONFIG
            return [config.id]
        else:
            raise ActionNotExistError(_("{}没有找到相关动作鉴权").format(self.view_action))
