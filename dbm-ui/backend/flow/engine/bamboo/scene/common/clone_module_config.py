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

from typing import List, Union

from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.clone_config import (
    CloneClusterConfigComponent,
    CloneModuleConfigComponent,
)
from backend.flow.utils.mysql.common.mysql_cluster_info import get_spider_module_version, get_version_and_charset


def add_clone_module_config_act(
    sub_pipeline: SubBuilder,
    cluster: Cluster,
    source_module_id: int,
    target_module_id: int,
    source_conf_file: str,
    target_conf_file: str,
) -> None:
    """
    添加克隆模块配置活动

    用于在数据库模块升级场景中，将源模块的配置克隆到目标模块。
    主要用于节点升级时，模块ID发生变化，需要将旧模块的配置项复制到新模块，确保配置的一致性。

    Args:
        sub_pipeline: 子流程
        cluster: 集群对象
        source_module_id: 源模块ID（旧模块）
        target_module_id: 目标模块ID（新模块）
        source_conf_file: 源配置文件名称（如 "MySQL-5.7"）
        target_conf_file: 目标配置文件名称（如 "MySQL-5.8"）
    """
    sub_pipeline.add_act(
        act_name=_("克隆模块配置"),
        act_component_code=CloneModuleConfigComponent.code,
        kwargs={
            "source_module_id": source_module_id,
            "target_module_id": target_module_id,
            "source_bk_biz_id": cluster.bk_biz_id,
            "target_bk_biz_id": cluster.bk_biz_id,
            "source_conf_file": source_conf_file,
            "target_conf_file": target_conf_file,
            "conf_type": "dbconf",
            "namespace": cluster.cluster_type,
        },
    )


def add_clone_cluster_config_act(
    sub_pipeline: Union[Builder, SubBuilder],
    cluster: Cluster,
    source_module_id: int,
    target_module_id: int,
    source_conf_file: str,
    target_conf_file: str,
    cluster_domains: List[str],
    source_bk_biz_id: int = None,
    target_bk_biz_id: int = None,
) -> None:
    """
    添加克隆集群配置活动

    用于在数据库模块升级场景中，将源模块的集群配置克隆到目标模块。
    与克隆模块配置的区别在于，此服务还会克隆集群级别的配置项。

    Args:
        sub_pipeline: 流程构建器（Builder 或 SubBuilder）
        cluster: 集群对象（用于获取业务ID和集群类型，如果 source_bk_biz_id 和 target_bk_biz_id 未指定则使用 cluster.bk_biz_id）
        source_module_id: 源模块ID（旧模块）
        target_module_id: 目标模块ID（新模块）
        source_conf_file: 源配置文件名称（如 "MySQL-5.7"）
        target_conf_file: 目标配置文件名称（如 "MySQL-5.8"）
        cluster_domains: 集群域名列表，用于指定需要克隆配置的集群
        source_bk_biz_id: 源业务ID（可选，默认使用 cluster.bk_biz_id）
        target_bk_biz_id: 目标业务ID（可选，默认使用 cluster.bk_biz_id）
    """
    # 如果未指定业务ID，使用集群的业务ID（同业务内克隆）
    if source_bk_biz_id is None:
        source_bk_biz_id = cluster.bk_biz_id
    if target_bk_biz_id is None:
        target_bk_biz_id = cluster.bk_biz_id

    sub_pipeline.add_act(
        act_name=_("克隆集群配置"),
        act_component_code=CloneClusterConfigComponent.code,
        kwargs={
            "source_module_id": source_module_id,
            "target_module_id": target_module_id,
            "source_bk_biz_id": source_bk_biz_id,
            "target_bk_biz_id": target_bk_biz_id,
            "source_conf_file": source_conf_file,
            "target_conf_file": target_conf_file,
            "conf_type": "dbconf",
            "namespace": cluster.cluster_type,
            "cluster_domains": cluster_domains,
        },
    )


def add_clone_storage_module_config_act(
    sub_pipeline: SubBuilder,
    cluster: Cluster,
    source_module_id: int,
    target_module_id: int,
) -> None:
    """
    添加克隆存储模块配置活动

    用于在存储模块（MySQL存储节点）升级场景中，将源模块的配置克隆到目标模块。
    此函数会自动从模块ID获取配置文件名称（db_version），无需手动传入。

    Args:
        sub_pipeline: 子流程
        cluster: 集群对象
        source_module_id: 源模块ID（旧模块）
        target_module_id: 目标模块ID（新模块）
    """
    # 自动获取源模块和目标模块的 conf_file（db_version）
    charset, source_conf_file = get_version_and_charset(cluster.bk_biz_id, source_module_id, cluster.cluster_type)
    charset, target_conf_file = get_version_and_charset(cluster.bk_biz_id, target_module_id, cluster.cluster_type)

    # 调用完整的克隆模块配置函数
    add_clone_module_config_act(
        sub_pipeline=sub_pipeline,
        cluster=cluster,
        source_module_id=source_module_id,
        target_module_id=target_module_id,
        source_conf_file=source_conf_file,
        target_conf_file=target_conf_file,
    )


def add_clone_spider_module_config_act(
    sub_pipeline: SubBuilder,
    cluster: Cluster,
    source_module_id: int,
    target_module_id: int,
) -> None:
    """
    添加克隆spider模块配置活动

    用于在spider模块升级场景中，将源模块的配置克隆到目标模块。
    此函数会自动从模块ID获取配置文件名称（spider_version），无需手动传入。
    注意：spider模块使用spider_version作为配置文件名称，与存储模块的db_version不同。

    Args:
        sub_pipeline: 子流程
        cluster: 集群对象
        source_module_id: 源模块ID（旧模块）
        target_module_id: 目标模块ID（新模块）
    """
    # 自动获取源模块和目标模块的 conf_file（spider_version）
    source_conf_file = get_spider_module_version(cluster.bk_biz_id, source_module_id)
    target_conf_file = get_spider_module_version(cluster.bk_biz_id, target_module_id)
    add_clone_module_config_act(
        sub_pipeline=sub_pipeline,
        cluster=cluster,
        source_module_id=source_module_id,
        target_module_id=target_module_id,
        source_conf_file=source_conf_file,
        target_conf_file=target_conf_file,
    )


def add_clone_cluster_storage_config_act(
    sub_pipeline: Union[Builder, SubBuilder],
    source_module_id: int,
    target_module_id: int,
    cluster_domains: List[str],
    source_bk_biz_id: int = None,
    target_bk_biz_id: int = None,
    cluster_type: str = None,
) -> None:
    """
    添加克隆集群存储配置活动

    用于在存储模块升级场景中，将源模块的集群级别配置克隆到目标模块。
    此函数会自动从模块ID获取配置文件名称（db_version），无需手动传入。
    与克隆模块配置的区别在于，此函数还会克隆集群级别的配置项。

    Args:
        sub_pipeline: 流程构建器（Builder 或 SubBuilder）
        cluster: 集群对象（用于获取业务ID和集群类型）
        source_module_id: 源模块ID（旧模块）
        target_module_id: 目标模块ID（新模块）
        cluster_domains: 集群域名列表，用于指定需要克隆配置的集群
        source_bk_biz_id: 源业务ID（可选，用于跨业务场景，默认使用 cluster.bk_biz_id）
        target_bk_biz_id: 目标业务ID（可选，用于跨业务场景，默认使用 cluster.bk_biz_id）
    """
    # 自动获取源模块和目标模块的 conf_file（db_version）
    charset, source_conf_file = get_version_and_charset(source_bk_biz_id, source_module_id, cluster_type)
    charset, target_conf_file = get_version_and_charset(target_bk_biz_id, target_module_id, cluster_type)

    sub_pipeline.add_act(
        act_name=_("克隆集群配置"),
        act_component_code=CloneClusterConfigComponent.code,
        kwargs={
            "source_module_id": source_module_id,
            "target_module_id": target_module_id,
            "source_bk_biz_id": source_bk_biz_id,
            "target_bk_biz_id": target_bk_biz_id,
            "source_conf_file": source_conf_file,
            "target_conf_file": target_conf_file,
            "conf_type": "dbconf",
            "namespace": cluster_type,
            "cluster_domains": cluster_domains,
        },
    )
