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

from datetime import datetime

from django.utils import timezone

from backend.components import DRSApi
from backend.db_meta.exceptions import ClusterNotExistException, InstanceNotExistException
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler as BaseClusterServiceHandler
from backend.exceptions import ApiResultError
from backend.flow.utils.mongodb.mongodb_util import MongoUtil


class ClusterServiceHandler(BaseClusterServiceHandler):
    @staticmethod
    def webconsole_rpc(cluster_id: int, cmd: str, **kwargs):
        """
        执行webconsole命令，只支持select语句
        @param cluster_id: 集群ID
        @param cmd: 执行命令
        """
        # 获取rpc结果
        try:
            session_time = kwargs.get("session_time", datetime.now(timezone.utc).replace(microsecond=0))
            session = f"{kwargs['user_id']}:{session_time}"
            rpc_results = DRSApi.mongodb_rpc(
                MongoUtil.get_mongodb_webconsole_args(cluster_id=cluster_id, session=session, command=cmd)
            )
        except (ApiResultError, InstanceNotExistException, ClusterNotExistException) as err:
            return {"query": "", "error_msg": err.message}

        return {"query": rpc_results, "error_msg": ""}
