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

from django.utils.translation import gettext as _
from iam.resource.provider import ListResult

from backend.configuration.constants import DBType
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.views.dbtype_provider import DBTypeResourceProvider


class TicketGroupResourceProvider(DBTypeResourceProvider):
    """
    TicketGroup资源是固定的，视图简化处理: 没有属性，全量返回资源
    """

    resource_meta: ResourceMeta = ResourceEnum.TICKET_GROUP

    def list_instance(self, filter, page, **options):
        db_types = [{"id": db.value, "display_name": db.name} for db in DBType]
        db_types.append({"id": "other", "display_name": _("其他")})
        return ListResult(results=db_types, count=len(db_types))

    def fetch_instance_info(self, filter, **options):
        items = [
            {"id": id, "display_name": DBType.get_choice_label(id) if id != "other" else _("其他")} for id in filter.ids
        ]
        return ListResult(results=items, count=len(items))
