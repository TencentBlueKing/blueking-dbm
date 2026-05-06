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

from django.utils.translation import gettext as _
from rest_framework.response import Response

from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class MysqlCloneClusterSceneApiView(FlowTestView):
    """
    MySQL 集群克隆 API

    将源集群的数据克隆到已存在的目标集群，主要步骤包括：
    1. 前置校验：版本和字符集一致性校验、目标集群空集群校验
    2. 数据恢复：从源集群备份恢复数据到目标集群的 master 和 slave
    3. 人工确认后断开同步：目标集群 master 执行 reset slave all 断开与源集群的同步关系

    请求参数示例:
    {
        "uid": "2022051612120002",
        "created_by": "admin",
        "bk_biz_id": "152",
        "backup_source": "REMOTE",
        "infos": [
            {
                "cluster_ids": [1, 2, 3],
                "dest_cluster_id": 100
            }
        ]
    }

    参数说明:
    - uid: 单据ID
    - created_by: 创建人
    - bk_biz_id: 业务ID
    - backup_source: 备份源类型，REMOTE（远程备份）或 LOCAL（本地备份），默认 REMOTE
    - infos: 克隆信息列表
        - cluster_ids: 源集群ID列表（支持同一机器多实例场景）
        - dest_cluster_id: 目标集群ID

    注意事项:
    - 源集群和目标集群的版本和字符集必须一致
    - 目标集群必须为空集群（不含用户数据库）
    """

    def post(self, request):
        logger.info(_("开始执行 MySQL 集群克隆"))
        root_id = generate_root_id()
        logger.info("define root_id: {}".format(root_id))
        mysql_controller = MySQLController(root_id=root_id, ticket_data=request.data)
        mysql_controller.mysql_clone_cluster_scene()
        return Response({"root_id": root_id})
