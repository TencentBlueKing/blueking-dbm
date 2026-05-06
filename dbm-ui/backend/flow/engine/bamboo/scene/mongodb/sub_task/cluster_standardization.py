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

from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import add_install_dbmon
from backend.flow.plugins.components.collections.mongodb.migrate_meta import MongoDBMigrateMetaComponent
from backend.flow.utils.mongodb.migrate_meta import MongoDBMigrateMeta
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository


def cluster_standardization(
    root_id: str, ticket_data: Optional[Dict], cluster_type: str, cluster_id: int, cluster_id_set: list[int]
) -> SubBuilder:
    """
    集群标准化流程
    """

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    exec_ips = []
    bk_cloud_id = ticket_data.get("bk_cloud_id")
    restart_exporter = ticket_data.get("restart_exporter", False)
    str_cluster_id = ""
    if cluster_id:
        cluster_info = MongoRepository().fetch_one_cluster(id=cluster_id)
        # mongos
        for node in cluster_info.get_mongos():
            exec_ips.append(node.ip)
        # configsvr
        for node in cluster_info.get_config().members:
            exec_ips.append(node.ip)
        # shardsvr
        host_set = set()
        for shard in cluster_info.get_shards():
            for node in shard.members:
                if node.ip not in host_set:
                    host_set.add(node.ip)
                    exec_ips.append(node.ip)
        str_cluster_id = str(cluster_id)
    if cluster_id_set:
        cluster_info = MongoRepository().fetch_one_cluster(id=cluster_id_set[0])
        for node in cluster_info.get_shards()[0].members:
            exec_ips.append(node.ip)
        str_cluster_id = ",".join([str(id) for id in cluster_id_set])

    # 安装 dbmon
    add_install_dbmon(
        root_id=root_id,
        flow_data=ticket_data,
        pipeline=sub_pipeline,
        iplist=exec_ips,
        bk_cloud_id=bk_cloud_id,
        allow_empty_instance=True,
    )

    # 挪模块 副本集多实例部署，串行挪cc
    if restart_exporter:
        kwargs = {
            "cluster_type": cluster_type,
            "cluster_id": cluster_id,
            "cluster_id_set": cluster_id_set,
            "meta_func_name": MongoDBMigrateMeta.gse_reload.__name__,
        }
        sub_pipeline.add_act(act_name=_("gse下发配置"), act_component_code=MongoDBMigrateMetaComponent.code, kwargs=kwargs)

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--集群标准化-{}".format(str_cluster_id)))
