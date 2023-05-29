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
import json

from .. import models
from . import BaseHandler


class DBHandler(BaseHandler):
    def handle_user(self, request, username: str):
        pass

    def handle_org(self, request, org_name: str, username: str):
        pass

    def handle_datasources(self, request, org_name: str, org_id: int, ds_list: int):
        created = list(
            models.DataSource.objects.filter(org_id=org_id, name__in=[ds.name for ds in ds_list]).values_list(
                "name", flat=True
            )
        )

        want_create = []
        for ds in ds_list:
            if ds.name in created:
                continue
            _ds = models.DataSource(
                org_id=org_id,
                name=ds.name,
                type=ds.type,
                url=ds.url,
                access=ds.access,
                is_default=ds.isDefault,
                database=ds.database,
                with_credentials=ds.withCredentials,
                version=ds.version,
                json_data=json.dumps(ds.jsonData),
            )
            want_create.append(_ds)

        if len(want_create) > 0:
            models.DataSource.objects.bulk_create(want_create)

    def handle_dashboards(self, request, org_name: str, org_id: int):
        pass
