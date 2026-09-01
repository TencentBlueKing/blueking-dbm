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
from typing import List, Optional

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.dts.deploy.cc_standardize import MysqlDtsCcStandardizeComponent


def mysql_dts_cc_standardize_subflow(
    *,
    root_id: str,
    bk_biz_id: int,
    bk_cloud_id: int,
    cluster_name: str = "",
    master_nodes: Optional[List[dict]] = None,
    worker_nodes: Optional[List[dict]] = None,
    dts_cluster_id: Optional[int] = None,
    creator: str = "",
) -> SubBuilder:
    """DTS 标准化子流程（本期仅 CC 挪机，预留后续监控扩展）。"""
    sub = SubBuilder(
        root_id=root_id,
        data={
            "bk_biz_id": bk_biz_id,
            "bk_cloud_id": bk_cloud_id,
            "cluster_name": cluster_name,
            "uid": root_id,
            "creator": creator,
        },
    )
    kwargs = {
        "bk_biz_id": bk_biz_id,
        "bk_cloud_id": bk_cloud_id,
        "cluster_name": cluster_name,
        "master_nodes": master_nodes or [],
        "worker_nodes": worker_nodes or [],
    }
    if dts_cluster_id is not None:
        kwargs["dts_cluster_id"] = dts_cluster_id
    sub.add_act(
        act_name=_("DTS CC 模块标准化"),
        act_component_code=MysqlDtsCcStandardizeComponent.code,
        kwargs=kwargs,
    )
    return sub
