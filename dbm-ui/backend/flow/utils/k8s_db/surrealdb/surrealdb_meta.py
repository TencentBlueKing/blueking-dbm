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

from django.db.transaction import atomic
from django.utils.translation import gettext as _

from backend.db_meta import api
from backend.db_meta.enums import ClusterPhase, ClusterStatus

logger = logging.getLogger("flow")


class SurrealDBMeta(object):
    def __init__(self, ticket_data: dict):
        """
        @param ticket_data : 单据信息
        """
        self.ticket_data = ticket_data

    def write(self) -> dict:
        function_name = self.ticket_data["ticket_type"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(_("找不到单据类型需要变更的cmdb函数{}，请联系系统管理员").format(function_name))
        return {}

    def k8s_surrealdb_enable(self) -> dict:
        api.cluster.surrealdb.enable(self.ticket_data["cluster_id"])
        return {"id": self.ticket_data["cluster_id"]}

    def k8s_surrealdb_delete(self) -> dict:
        api.cluster.surrealdb.delete(self.ticket_data["cluster_id"])
        return {"id": self.ticket_data["cluster_id"]}

    def k8s_surrealdb_disable(self) -> dict:
        api.cluster.surrealdb.disable(self.ticket_data["cluster_id"])
        return {"id": self.ticket_data["cluster_id"]}

    def k8s_surrealdb_single_apply(self) -> dict:
        # 部署 surrealdb，更新cmdb
        result = {}
        cluster = {
            "name": self.ticket_data["cluster_name"],
            "alias": self.ticket_data["cluster_alias"],
            "bk_biz_id": self.ticket_data["bk_biz_id"],
            "cluster_type": self.ticket_data["cluster_type"],
            "immute_domain": self.ticket_data["domain"],
            "major_version": self.ticket_data["major_version"],
            "phase": ClusterPhase.ONLINE.value,
            "status": ClusterStatus.NORMAL.value,
            "region": self.ticket_data["region"],
            "creator": self.ticket_data["creator"],
        }

        with atomic():
            resp = api.cluster.surrealdb.create(**cluster)
            result.update(resp)

        return result
