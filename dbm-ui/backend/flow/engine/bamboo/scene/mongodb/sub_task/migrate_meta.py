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

from copy import deepcopy
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.add_relationship_to_meta import (
    ExecAddRelationshipOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.migrate_meta import MongoDBMigrateMetaComponent
from backend.flow.utils.mongodb.mongodb_migrate_dataclass import MigrateActKwargs


def cluster_migrate(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: MigrateActKwargs, cluster: bool
) -> SubBuilder:
    """
    单个replicaset迁移元数
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)
    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取副本集机器是否复用
    sub_get_kwargs.skip_machine()

    # 检查 是否已经迁移 从目标环境检查迁移ip是否复用
    kwargs = sub_get_kwargs.get_check_dest_cluster_info(
        cluster_name=sub_get_kwargs.source_cluster_info.get("replsetname")
    )
    sub_pipeline.add_act(
        act_name=_("检查cluster目标端是否存在"), act_component_code=MongoDBMigrateMetaComponent.code, kwargs=kwargs
    )

    # 检查机器规格是否在目标端存在
    kwargs = sub_get_kwargs.get_check_spec_info()
    sub_pipeline.add_act(act_name=_("检查目标端机器规格"), act_component_code=MongoDBMigrateMetaComponent.code, kwargs=kwargs)

    # dbconfig保存oplogsize cachesize
    if cluster:
        namespace = ClusterType.MongoShardedCluster.value
    else:
        namespace = ClusterType.MongoReplicaSet.value
    kwargs = sub_get_kwargs.get_save_conf_info(namespace=namespace)
    sub_pipeline.add_act(act_name=_("保存配置"), act_component_code=MongoDBMigrateMetaComponent.code, kwargs=kwargs)

    # 目标业务更新dba 检查目标业务的dba，不一致则更新
    kwargs = sub_get_kwargs.get_dba_info()
    sub_pipeline.add_act(act_name=_("更新dba"), act_component_code=MongoDBMigrateMetaComponent.code, kwargs=kwargs)

    # 迁移数据
    kwargs = sub_get_kwargs.get_migrate_info()
    sub_pipeline.add_act(
        act_name=_("迁移meta"),
        act_component_code=ExecAddRelationshipOperationComponent.code,
        kwargs=kwargs,
    )

    # node保存密码到密码服务
    kwargs = sub_get_kwargs.get_save_password_info()
    sub_pipeline.add_act(act_name=_("保存密码"), act_component_code=MongoDBMigrateMetaComponent.code, kwargs=kwargs)

    # 修改dns的app字段
    kwargs = sub_get_kwargs.get_change_dns_app_info()
    sub_pipeline.add_act(act_name=_("更新dns的app"), act_component_code=MongoDBMigrateMetaComponent.code, kwargs=kwargs)

    if cluster:
        name = "cluster"
        # cluster删除shard的域名 迁移完，运行无误后再删
        # kwargs = sub_get_kwargs.get_shard_delete_doamin_info()
        # sub_pipeline.add_act(
        #     act_name=_("删除shard的domain"),
        #     act_component_code=MongoDBMigrateMetaComponent.code,
        #     kwargs=kwargs
        # )
        cluster_name = sub_get_kwargs.source_cluster_info["cluster_id"]
        # 添加clb
        if sub_get_kwargs.source_cluster_info["clb"]:
            kwargs = sub_get_kwargs.get_clb_info()
            sub_pipeline.add_act(
                act_name=_("添加clb到meta"), act_component_code=MongoDBMigrateMetaComponent.code, kwargs=kwargs
            )
    else:
        name = "replicaset"
        cluster_name = sub_get_kwargs.source_cluster_info["replsetname"]

    return sub_pipeline.build_sub_process(
        sub_name=_("MongoDB--{}-meta迁移-{}-{}".format(name, sub_get_kwargs.payload["app"], cluster_name))
    )
