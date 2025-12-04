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

import copy
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceInnerRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import (
    mysql_restore_master_slave_sub_flow,
)
from backend.flow.engine.exceptions import CloneClusterException
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.mysql_rds_execute import MySQLExecuteRdsComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import ExecuteRdsKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.ticket.builders.common.constants import MySQLBackupSource

logger = logging.getLogger("flow")

# 系统库列表，用于检查目标集群是否为空
SYSTEM_DBS = frozenset(
    ["mysql", "information_schema", "performance_schema", "sys", "test", "db_infobase", "infodba_schema"]
)


class MySQLCloneClusterFlow(object):
    """
    构建 MySQL 集群克隆流程

    该流程用于将源集群的数据克隆到已存在的目标集群，主要步骤包括：
    1. 前置校验：版本和字符集一致性校验、目标集群空集群校验
    2. 屏蔽告警：屏蔽目标集群 master 和 slave 的机器告警
    3. 断开同步：目标集群 slave 执行 reset slave all 断开与原有 master 的同步关系
    4. 数据恢复：从源集群备份恢复数据到目标集群的 master 和 slave
    5. 断开同步：目标集群 master 执行 reset slave all 断开与源集群的同步关系
    6. 解除告警屏蔽：解除目标集群的告警屏蔽

    入参格式 (ticket_data):
    {
        "uid": "单据ID",
        "created_by": "创建人",
        "bk_biz_id": "业务ID",
        "backup_source": "REMOTE/LOCAL",  # 备份源类型，默认 REMOTE
        "infos": [
            {
                "cluster_id": 源集群ID,  # 源集群
                "dest_cluster_id": 目标集群ID,  # 目标集群
            }
        ]
    }

    注意事项：
    - 源集群和目标集群的版本和字符集必须一致
    - 目标集群必须为空集群（不含用户数据库）
    - 不需要安装 MySQL（目标集群已存在）
    - 不需要切换域名和元数据更新
    - 不需要卸载旧实例
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id: 任务流程定义的 root_id
        @param ticket_data: 单据传递参数
        """
        self.root_id = root_id
        self.ticket_data = ticket_data
        self.data = {}

        # 定义备份文件存放到目标机器目录位置
        self.backup_target_path = f"/data/dbbak/{self.root_id}"
        self.local_backup = False
        if self.ticket_data.get("backup_source") == MySQLBackupSource.LOCAL:
            self.local_backup = True

    def _validate_cluster_compatibility(self, source_cluster: Cluster, dest_cluster: Cluster) -> None:
        """
        校验源集群和目标集群的版本和字符集一致性

        @param source_cluster: 源集群对象
        @param dest_cluster: 目标集群对象
        @raises CloneClusterException: 版本或字符集不一致时抛出异常
        """
        # 获取源集群的版本和字符集
        source_charset, source_version = get_version_and_charset(
            bk_biz_id=source_cluster.bk_biz_id,
            db_module_id=source_cluster.db_module_id,
            cluster_type=source_cluster.cluster_type,
        )

        # 获取目标集群的版本和字符集
        dest_charset, dest_version = get_version_and_charset(
            bk_biz_id=dest_cluster.bk_biz_id,
            db_module_id=dest_cluster.db_module_id,
            cluster_type=dest_cluster.cluster_type,
        )

        # 校验版本一致性
        if source_version != dest_version:
            raise CloneClusterException(
                message=_("源集群 {} 版本 {} 与目标集群 {} 版本 {} 不一致").format(
                    source_cluster.name, source_version, dest_cluster.name, dest_version
                )
            )

        # 校验字符集一致性
        if source_charset != dest_charset:
            raise CloneClusterException(
                message=_("源集群 {} 字符集 {} 与目标集群 {} 字符集 {} 不一致").format(
                    source_cluster.name, source_charset, dest_cluster.name, dest_charset
                )
            )

        logger.info(
            _("集群兼容性校验通过: 源集群={}, 目标集群={}, 版本={}, 字符集={}").format(
                source_cluster.name, dest_cluster.name, source_version, source_charset
            )
        )

    def _validate_dest_cluster_empty(self, dest_cluster: Cluster) -> None:
        """
        校验目标集群是否为空集群

        通过在目标集群 master 上执行 show databases，排除系统库后检查是否存在用户库

        @param dest_cluster: 目标集群对象
        @raises CloneClusterException: 目标集群非空时抛出异常
        """
        # 获取目标集群的 master 实例
        dest_master = dest_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)

        # 执行 show databases 查询
        address = "{}{}{}".format(dest_master.machine.ip, IP_PORT_DIVIDER, dest_master.port)
        res = DRSApi.rpc(
            {
                "addresses": [address],
                "cmds": ["show databases"],
                "force": False,
                "bk_cloud_id": dest_cluster.bk_cloud_id,
            }
        )

        # 检查查询结果
        if res[0]["error_msg"]:
            raise CloneClusterException(
                message=_("查询目标集群 {} 数据库列表失败: {}").format(dest_cluster.name, res[0]["error_msg"])
            )

        # 获取所有数据库列表
        databases = []
        for row in res[0]["cmd_results"][0]["table_data"]:
            db_name = row.get("Database", "")
            if db_name:
                databases.append(db_name)

        # 过滤掉系统库，检查是否存在用户库
        user_databases = [db for db in databases if db not in SYSTEM_DBS]

        if user_databases:
            raise CloneClusterException(
                message=_("目标集群 {} 非空，存在用户数据库: {}").format(dest_cluster.name, ", ".join(user_databases))
            )

        logger.info(_("目标集群 {} 空集群校验通过").format(dest_cluster.name))

    def _get_cluster_info(self, source_cluster: Cluster, dest_cluster: Cluster) -> Dict:
        """
        构建集群克隆所需的集群信息

        @param source_cluster: 源集群对象
        @param dest_cluster: 目标集群对象
        @return: 集群信息字典
        """
        # 获取源集群的 master
        source_master = source_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)

        # 获取目标集群的 master 和 slave
        dest_master = dest_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        dest_slave = dest_cluster.storageinstance_set.filter(
            instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
        ).first()

        if not dest_slave:
            # 如果没有 stand_by 的 slave，取第一个运行中的 slave
            dest_slave = dest_cluster.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.SLAVE.value,
                status=InstanceStatus.RUNNING.value,
            ).first()

        if not dest_slave:
            raise CloneClusterException(message=_("目标集群 {} 没有可用的从节点").format(dest_cluster.name))

        # 获取字符集
        charset, unused_version = get_version_and_charset(
            bk_biz_id=source_cluster.bk_biz_id,
            db_module_id=source_cluster.db_module_id,
            cluster_type=source_cluster.cluster_type,
        )

        return {
            # 源集群信息
            "cluster_id": source_cluster.id,
            "master_ip": source_master.machine.ip,
            "master_port": source_master.port,
            # 目标集群信息（作为新主从）
            "new_master_ip": dest_master.machine.ip,
            "new_master_port": dest_master.port,
            "new_slave_ip": dest_slave.machine.ip,
            "new_slave_port": dest_slave.port,
            # 其他配置
            "bk_cloud_id": source_cluster.bk_cloud_id,
            "file_target_path": f"{self.backup_target_path}/{source_master.port}",
            "charset": charset,
            "backup_source": self.ticket_data.get("backup_source", MySQLBackupSource.REMOTE.value),
            "change_master_force": False,
            "change_master": False,
        }

    def clone_cluster_flow(self):
        """
        执行集群克隆流程

        主要步骤：
        1. 前置校验（版本字符集、空集群）
        2. 屏蔽告警（屏蔽目标集群 master 和 slave 的机器告警）
        3. 断开同步（目标集群 slave 执行 reset slave all）
        4. 数据恢复（使用 mysql_restore_master_slave_sub_flow）
        5. 断开同步（目标集群 master 执行 reset slave all）
        6. 解除告警屏蔽
        """
        # 构建主流程
        cluster_ids = []
        for info in self.ticket_data["infos"]:
            cluster_ids.append(info["dest_cluster_id"])
            cluster_ids.append(info["cluster_id"])
        clone_pipeline_all = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )

        clone_pipeline_list = []

        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            source_cluster_id = info["cluster_id"]
            dest_cluster_id = info["dest_cluster_id"]

            # 获取源集群和目标集群对象
            source_cluster = Cluster.objects.get(id=source_cluster_id)
            dest_cluster = Cluster.objects.get(id=dest_cluster_id)

            # === 前置校验 ===
            # 1. 版本和字符集一致性校验
            self._validate_cluster_compatibility(source_cluster, dest_cluster)

            # 2. 目标集群空集群校验
            self._validate_dest_cluster_empty(dest_cluster)

            # 设置基础数据
            self.data["bk_biz_id"] = source_cluster.bk_biz_id
            self.data["bk_cloud_id"] = source_cluster.bk_cloud_id
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["uid"] = self.ticket_data["uid"]

            # 构建子流程
            clone_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))

            # === 数据恢复阶段 ===
            # 构建集群信息
            cluster_info = self._get_cluster_info(source_cluster, dest_cluster)

            # 获取目标集群的所有存储实例 IP（用于屏蔽告警）
            dest_storage_ips = list(dest_cluster.storageinstance_set.values_list("machine__ip", flat=True).distinct())

            # 屏蔽目标集群告警
            clone_pipeline.add_act(
                act_name=_("屏蔽目标集群 {} 告警24小时").format(dest_cluster.name),
                act_component_code=AddAlarmShieldComponent.code,
                kwargs={
                    "duration_seconds": 24 * 3600,
                    "description": _("集群 {} 克隆操作").format(dest_cluster.name),
                    "dimensions": [
                        {
                            "name": "instance_host",
                            "values": dest_storage_ips,
                        }
                    ],
                },
            )

            # 在目标集群 slave 上执行 reset slave all，断开与原有 master 的同步关系
            dest_slave = dest_cluster.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
            ).first()

            if not dest_slave:
                # 如果没有 stand_by 的 slave，取第一个运行中的 slave
                dest_slave = dest_cluster.storageinstance_set.filter(
                    instance_inner_role=InstanceInnerRole.SLAVE.value,
                    status=InstanceStatus.RUNNING.value,
                ).first()

            if dest_slave:
                clone_pipeline.add_act(
                    act_name=_("目标集群 {} Slave 执行 reset slave all").format(dest_cluster.name),
                    act_component_code=MySQLExecuteRdsComponent.code,
                    kwargs=asdict(
                        ExecuteRdsKwargs(
                            bk_cloud_id=dest_cluster.bk_cloud_id,
                            instance_ip=dest_slave.machine.ip,
                            instance_port=dest_slave.port,
                            sqls=["stop slave", "reset slave all"],
                        )
                    ),
                )

            # 获取备份过滤 IP 列表（本地备份场景）
            filter_ips = None
            if self.local_backup:
                source_master = source_cluster.storageinstance_set.get(
                    instance_inner_role=InstanceInnerRole.MASTER.value
                )
                stand_by_slaves = source_cluster.storageinstance_set.filter(
                    instance_inner_role=InstanceInnerRole.SLAVE.value,
                    is_stand_by=True,
                    status=InstanceStatus.RUNNING.value,
                )
                filter_ips = [source_master.machine.ip]
                filter_ips.extend([slave.machine.ip for slave in stand_by_slaves])

            # 添加数据恢复子流程
            clone_pipeline.add_sub_pipeline(
                sub_flow=mysql_restore_master_slave_sub_flow(
                    root_id=self.root_id,
                    ticket_data=copy.deepcopy(self.data),
                    cluster=cluster_info,
                    cluster_model=source_cluster,
                    filter_ips=filter_ips,
                )
            )

            # === 断开同步阶段 ===
            # 人工确认后再断开与源集群的同步关系
            clone_pipeline.add_act(
                act_name=_("人工确认断开同步"),
                act_component_code=PauseComponent.code,
                kwargs={},
            )

            # 在目标集群 master 上执行 reset slave all，断开与源集群的同步关系
            dest_master = dest_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
            clone_pipeline.add_act(
                act_name=_("目标集群 {} Master 执行 reset slave all").format(dest_cluster.name),
                act_component_code=MySQLExecuteRdsComponent.code,
                kwargs=asdict(
                    ExecuteRdsKwargs(
                        bk_cloud_id=dest_cluster.bk_cloud_id,
                        instance_ip=dest_master.machine.ip,
                        instance_port=dest_master.port,
                        sqls=["stop slave", "reset slave all"],
                    )
                ),
            )

            # 解除告警屏蔽
            clone_pipeline.add_act(
                act_name=DisableAlarmShieldComponent.node_name,
                act_component_code=DisableAlarmShieldComponent.code,
                kwargs={},
            )

            clone_pipeline_list.append(
                clone_pipeline.build_sub_process(sub_name=_("克隆集群到 {}").format(dest_cluster.name))
            )

        # 运行流程
        clone_pipeline_all.add_parallel_sub_pipeline(clone_pipeline_list)
        clone_pipeline_all.run_pipeline(
            init_trans_data_class=ClusterInfoContext(),
            is_drop_random_user=True,
        )
