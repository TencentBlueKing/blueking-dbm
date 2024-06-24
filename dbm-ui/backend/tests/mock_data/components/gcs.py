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
from backend.db_meta.models import AppCache

GCS_CLUSTER_INSTANCE = "gcs.testdb.dba.db"


class GcsApiMock(object):
    """Gcs的mock类"""

    @classmethod
    def cloud_privileges_asyn_bydbname(cls, params, headers):
        cluster = params["target_ip"]
        assert cluster == GCS_CLUSTER_INSTANCE, f"{cluster} not belong to gcs"
        return {"task_id": "gcs_task", "platform": "gcs", "job_id": "gcs_task"}


class ScrApiMock(object):
    """Scr的mock类"""

    @classmethod
    def common_query(cls, params):
        try:
            bk_biz_id = AppCache.objects.get(db_app_abbr=params["app"]).bk_biz_id
        except AppCache.DoesNotExist:
            bk_biz_id = 0
        return {"detail": [{"appid": params["app"], "ccId": bk_biz_id}], "rowsNum": 1}
