"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy
import logging
from typing import Dict

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.mysql_upgrade_subflow import (
    get_is_same_tmysql_version,
    mysql_cluster_upgrade_check_subflow,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.utils.mysql.mysql_context_dataclass import TendbClusterStorageUpgradeContext

from ..remote_master_slave_swtich import RemoteMasterSlaveSwitchFlow
from .upgrade_components import add_standardize_act, build_mysql_upgrade_pipelines
from .upgrade_utils import (
    add_alarm_shield_act,
    add_disable_alarm_shield_act,
    add_mysql_media_download_for_all_hosts,
    check_master_slave_pair,
    check_version_compatibility,
    convert_pairs_to_upgrade_instances,
    group_master_slave_pairs,
)


class TenDBClusterStorageLocalUpgradeFlow(object):
    """
    TenDBCluster存储层本地升级流程
    1. 先本地升级slave节点
    2. 人工确认主从切换
    3. 主从切换
    4. 再升级新的slave节点(原master)
    5. 执行标准化
    """

    def __init__(self, root_id: str, data: Dict):
        """
        @param root_id: 任务流程定义的root_id
        @param data: 单据传递参数
        """
        self.root_id = root_id
        self.ticket_data = data

    def local_upgrade(self):
        """
        TenDBCluster存储层本地升级流程:
        1. 先本地升级slave节点
        2. 人工确认主从切换
        3. 主从切换
        4. 再升级新的slave节点(原master)
        5. 执行标准化

        数据格式：
        {
            "upgrade_local": True,
            "is_check_process": bool,      # 是否检查客户端连接情况
            "is_verify_checksum": bool,    # 是否验证checksum结果
            "infos": [
                {
                    "cluster_id": 1,
                    "pkg_id": 123,
                }
            ]
        }
        """
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        tendbcluster_upgrade_pipeline = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )

        sub_pipelines = []
        idx = 1
        for info in self.ticket_data["infos"]:
            cluster_id = info["cluster_id"]
            pkg_id = info["pkg_id"]
            sub_pipeline = self.build_upgrade_pipeline(cluster_id, pkg_id, idx)
            sub_pipelines.append(sub_pipeline)
            idx += 1

        tendbcluster_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        tendbcluster_upgrade_pipeline.run_pipeline(
            init_trans_data_class=TendbClusterStorageUpgradeContext(), is_drop_random_user=True
        )

    def build_upgrade_pipeline(self, cluster_id, pkg_id, idx):
        """构建升级流水线"""
        # 执行升级前置检查
        new_mysql_pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
        cluster = Cluster.objects.get(id=cluster_id)
        bk_cloud_id = cluster.bk_cloud_id
        is_check_process = self.ticket_data.get("is_check_process", True)

        self.pre_check(cluster_id, new_mysql_pkg)
        sub_pipeline = SubBuilder(
            root_id=self.root_id, data=copy.deepcopy(self.ticket_data), need_random_pass_cluster_ids=[cluster_id]
        )

        # 按主从分组，同时获取所有实例
        master_slave_pairs, remote_storage_instances = group_master_slave_pairs(cluster_id)

        # 转换为升级检查所需的格式
        upgrade_instances = convert_pairs_to_upgrade_instances(master_slave_pairs)
        logger = logging.getLogger("flow")
        logger.info(
            _("集群 {} 共有 {} 个主从对需要升级，涉及 {} 个主机").format(cluster_id, len(master_slave_pairs), len(upgrade_instances))
        )

        # 阶段1: 按主机维度统一下发MySQL升级介质
        add_mysql_media_download_for_all_hosts(sub_pipeline, remote_storage_instances, pkg_id, bk_cloud_id)

        # 阶段2: 对所有实例执行MySQL升级前置检查
        sub_pipeline.add_sub_pipeline(
            sub_flow=mysql_cluster_upgrade_check_subflow(
                uid=self.ticket_data.get("uid"),
                root_id=self.root_id,
                parent_global_data=copy.deepcopy(self.ticket_data),
                bk_cloud_id=bk_cloud_id,
                upgrade_instances=upgrade_instances,
                pkg_id=pkg_id,
                sub_flow_name=_("集群存储节点升级检查"),
            )
        )

        # 阶段3: 添加告警屏蔽
        add_alarm_shield_act(sub_pipeline, cluster)

        is_same_tmysql_version = get_is_same_tmysql_version(cluster_id, new_mysql_pkg.name)
        # 阶段4: 升级所有slave节点
        slave_upgrade_pipelines = build_mysql_upgrade_pipelines(
            master_slave_pairs,
            "slave",
            _("升级slave节点"),
            is_same_tmysql_version,
            self.root_id,
            self.ticket_data,
            pkg_id,
            cluster,
            is_check_process,
        )
        if slave_upgrade_pipelines:
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=slave_upgrade_pipelines)

        # 阶段5: 人工确认主从切换
        sub_pipeline.add_act(act_name=_("人工确认主从切换"), act_component_code=PauseComponent.code, kwargs={})

        # 阶段6: 主从切换
        switch_flow = RemoteMasterSlaveSwitchFlow(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))
        switch_pipeline = switch_flow.build_cluster_switch_all_pipeline(
            parent_global_data=copy.deepcopy(self.ticket_data), cluster_id=cluster_id, batch_idx=idx
        )
        # 阶段7: 主从切换
        sub_pipeline.add_sub_pipeline(sub_flow=switch_pipeline)

        # 阶段8: 解除告警屏蔽
        add_disable_alarm_shield_act(sub_pipeline)

        # 阶段9: 执行标准化
        add_standardize_act(sub_pipeline, remote_storage_instances, self.root_id, self.ticket_data, cluster)

        # 阶段10: 人工确认主从切换
        sub_pipeline.add_act(act_name=_("人工确认升级原Master节点"), act_component_code=PauseComponent.code, kwargs={})

        # 阶段11: 添加告警屏蔽
        add_alarm_shield_act(sub_pipeline, cluster)

        # 阶段12: 升级原master节点（现在是slave）
        original_master_upgrade_pipelines = build_mysql_upgrade_pipelines(
            master_slave_pairs,
            "master",
            _("升级原master节点"),
            is_same_tmysql_version,
            self.root_id,
            self.ticket_data,
            pkg_id,
            cluster,
            is_check_process,
        )
        if original_master_upgrade_pipelines:
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=original_master_upgrade_pipelines)
        # 阶段13: 解除告警屏蔽
        add_disable_alarm_shield_act(sub_pipeline)

        return sub_pipeline.build_sub_process(sub_name=_("{}:本地升级").format(cluster.immute_domain))

    def pre_check(self, cluster_id, new_mysql_pkg):
        """
        升级前置检查
        1. 检查集群元数据完整性
        2. 检查master和slave实例是否都存在且健康
        3. 检查主从关系是否正确
        4. 检查版本兼容性
        """
        logger = logging.getLogger("flow")
        logger.info(_("开始执行集群 {} 的升级前置检查").format(cluster_id))

        # 检查集群基本信息
        if not Cluster.objects.filter(id=cluster_id).exists():
            raise DBMetaException(message=_("集群 {} 不存在").format(cluster_id))

        # 按主从分组，同时获取所有实例
        master_slave_pairs, remote_storage_instances = group_master_slave_pairs(cluster_id)

        logger.info(_("集群 {} 共发现 {} 个主从对").format(cluster_id, len(master_slave_pairs)))

        # 检查每个主从对
        for i, pair in enumerate(master_slave_pairs):
            check_master_slave_pair(pair, i + 1, cluster_id)

        # 检查版本兼容性
        check_version_compatibility(cluster_id, new_mysql_pkg, self.ticket_data)

        logger.info(_("集群 {} 升级前置检查通过").format(cluster_id))
