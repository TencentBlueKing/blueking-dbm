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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.spider_switch_nodes import TenDBClusterSwitchNodesFlow
from backend.flow.plugins.components.collections.common.add_unlock_ticket_type_config import (
    AddUnlockTicketTypeConfigComponent,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.common.pause_with_ticket_lock_check import (
    PauseWithTicketLockCheckComponent,
)
from backend.flow.utils.base.base_dataclass import AddUnLockTicketTypeKwargs, ReleaseUnLockTicketTypeKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext, TendbClusterSpiderUpgradeContext
from backend.flow.utils.mysql.mysql_version_parse import get_spider_sub_version_by_pkg_name

from .upgrade_components import (
    add_cluster_module_update_act,
    add_spider_alarm_shield_act,
    add_spider_disable_alarm_shield_act,
    add_spider_keyword_check_act,
    add_spider_media_download_act,
    add_spider_upgrade_check_act,
    build_spider_upgrade_subflow,
)
from .upgrade_utils import (
    check_cross_major_version_upgrade,
    check_spider_node_count_compatibility,
    check_spider_upgrade_version_compatibility,
    get_spider_master_instances,
    get_spider_upgrade_instances,
)

logger = logging.getLogger("flow")


class UpgradeSpiderFlow(TenDBClusterSwitchNodesFlow):
    """
    TendbCluster spider节点升级流程

    功能说明：
    1. 支持本地升级：在现有机器上直接升级spider版本
    2. 支持迁移升级：通过新增机器替换旧机器的方式进行升级
    3. 继承自TenDBClusterSwitchNodesFlow类，复用扩容和缩容功能，以及继承TenDBClusterSwitchNodesFlow类的解锁单据列表

    升级模式：
    - 本地升级(upgrade_local=True)：在现有spider节点上直接升级版本
    - 迁移升级(upgrade_local=False)：新增spider节点替换旧节点进行升级

    数据格式示例：
        {
            "upgrade_local": True,  # 是否本地升级
            "force": False,         # 是否强制升级
            "infos": [
                {
                    "cluster_id": 1,                    # 集群ID
                    "pkg_id": 123,                      # 目标版本包ID
                    "new_db_module_id": 3334,           # 新的数据库模块ID
                    "spider_master_ip_list": [],        # 新增的spider master IP列表(迁移升级时使用)
                    "spider_slave_ip_list": []          # 新增的spider slave IP列表(迁移升级时使用)
                }
            ]
        }

    升级流程：
    1. 本地升级：下发安装包 -> 升级spider slave -> 升级spider master -> 更新元数据
    2. 迁移升级：新增节点 -> 人工确认 -> 下架旧节点 -> 更新元数据
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        初始化UpgradeSpiderFlow

        参数说明：
        @param root_id: 任务流程定义的root_id，用于标识整个升级流程
        @param data: 单据传递参数，包含升级配置信息

        初始化流程：
        1. 调用父类初始化方法，设置基础流程参数
        2. 提取升级相关的配置参数
        3. 设置实例变量，供后续方法使用
        """
        # 初始化父类的init方法，设置基础流程参数
        super().__init__(root_id=root_id, data=data)

        # 设置流程基础参数
        self.root_id = root_id  # 流程根ID
        self.uid = data["uid"]  # 用户ID
        self.bk_biz_id = data["bk_biz_id"]  # 业务ID
        self.force_upgrade = data.get("force", False)  # 是否强制升级
        self.is_check_process = data.get("is_check_process", True)
        self.is_safe = data.get("is_check_process", True)
        self.data = data  # 原始数据
        self.upgrade_local = data.get("upgrade_local", False)  # 是否本地升级
        self.pause_when_upgrade_half = data.get("pause_when_upgrade_half", False)
        # 提取所有涉及的集群ID，去重后保存
        self.cluster_ids = list(set([i["cluster_id"] for i in self.data["infos"]]))

    def run(self):
        """
        执行spider升级流程的主入口方法

        执行流程：
        1. 执行前置检查(__pre_check)：验证升级版本和节点数量
        2. 根据upgrade_local参数选择升级模式：
           - True: 执行本地升级(local_upgrade)
           - False: 执行迁移升级(migrate_upgrade)

        升级模式说明：
        - 本地升级：在现有机器上直接升级spider版本，适用于版本兼容性好的场景
        - 迁移升级：通过新增机器替换旧机器的方式进行升级，适用于需要保证服务连续性的场景
        """
        # 执行前置检查：验证升级版本和节点数量
        self.__pre_check()

        # 根据升级模式选择执行路径
        if self.upgrade_local:
            # 本地升级：在现有机器上直接升级版本
            self.local_upgrade()
        else:
            # 迁移升级：通过新增机器替换旧机器进行升级
            self.migrate_upgrade()

    # spider_ins.tendbclusterspiderext.spider_role
    def __pre_check(self):
        """
        检查升级版本和源版本
        """
        # 检查版本兼容性
        check_spider_upgrade_version_compatibility(self.data)

        # 检查节点数量兼容性
        check_spider_node_count_compatibility(self.data)

    def local_upgrade(self):
        """
        spider 本地升级场景
        {
            bk_biz_id: 0,
            bk_cloud_id: 0,
            infos:[
                {
                    cluster_id:,
                    pkg_id:  12,
                    "new_db_module_id": 112,
                }
            ]
        }
        """
        spider_upgrade_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=self.cluster_ids
        )
        sub_pipelines = []
        for upgrade_info in self.data["infos"]:
            cluster_id = upgrade_info["cluster_id"]
            pkg_id = int(upgrade_info["pkg_id"])
            new_db_module_id = upgrade_info["new_db_module_id"]
            spider_pkg = Package.objects.get(id=pkg_id)
            logger.info("param pkg_id:{},get the pkg name: {}".format(pkg_id, spider_pkg.name))
            cluster = Cluster.objects.get(id=cluster_id)
            bk_cloud_id = cluster.bk_cloud_id
            sub_flow_context = copy.deepcopy(self.data)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 使用新的过滤方法，只升级需要升级的spider实例
            spiders_to_upgrade, spiders_already_target_version, spider_ips = get_spider_upgrade_instances(
                cluster_id=cluster_id, target_version=spider_pkg.name
            )

            # 如果没有需要升级的实例，跳过当前集群
            if len(spiders_to_upgrade) == 0:
                logger.info(_("集群 {} 所有spider实例版本已经是目标版本，跳过升级").format(cluster.immute_domain))
                continue

            spider_master_ins = get_spider_master_instances(spiders_to_upgrade)

            # 切换前做预检测
            add_spider_upgrade_check_act(sub_pipeline, spider_master_ins, bk_cloud_id, self.is_check_process)

            # 提前下发文件
            add_spider_media_download_act(sub_pipeline, spider_ips, pkg_id, bk_cloud_id)

            # 添加告警屏蔽
            add_spider_alarm_shield_act(sub_pipeline, cluster)

            spider_slave_upgrade_pipelines = []
            spider_master_upgrade_pipelines = []
            new_spider_version = get_spider_sub_version_by_pkg_name(spider_pkg.name)
            for spider_ins in spiders_to_upgrade:
                spider_role = spider_ins.tendbclusterspiderext.spider_role
                spider_ip = spider_ins.machine.ip
                spider_port = spider_ins.port
                if spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE:
                    spider_slave_upgrade_pipelines.append(
                        build_spider_upgrade_subflow(
                            ip=spider_ip,
                            bk_cloud_id=bk_cloud_id,
                            pkg_id=pkg_id,
                            domain=cluster.immute_domain,
                            spider_version=new_spider_version,
                            spider_port=spider_port,
                            force_upgrade=True,
                            sub_flow_context=sub_flow_context,
                            root_id=self.root_id,
                        )
                    )
                if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                    spider_master_upgrade_pipelines.append(
                        build_spider_upgrade_subflow(
                            ip=spider_ip,
                            bk_cloud_id=bk_cloud_id,
                            pkg_id=pkg_id,
                            domain=cluster.immute_domain,
                            spider_version=new_spider_version,
                            spider_port=spider_port,
                            force_upgrade=True,
                            sub_flow_context=sub_flow_context,
                            root_id=self.root_id,
                        )
                    )
            # spider slave 一起升级
            if len(spider_slave_upgrade_pipelines) > 0:
                sub_pipeline.add_parallel_sub_pipeline(spider_slave_upgrade_pipelines)
            # spider master 分两批次升级
            mid = len(spider_master_upgrade_pipelines) // 2  # 整数除法，自动向下取整
            part1 = spider_master_upgrade_pipelines[:mid]
            part2 = spider_master_upgrade_pipelines[mid:]
            sub_pipeline.add_parallel_sub_pipeline(part1)
            if self.pause_when_upgrade_half:
                sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            sub_pipeline.add_parallel_sub_pipeline(part2)
            # 更新集群模块信息
            if new_db_module_id != cluster.db_module_id:
                add_cluster_module_update_act(sub_pipeline, cluster_id, new_db_module_id)

            # 解除告警屏蔽
            add_spider_disable_alarm_shield_act(sub_pipeline)

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("[{}]本地升级spider版本".format(cluster.immute_domain)))
            )
        spider_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        spider_upgrade_pipeline.run_pipeline(init_trans_data_class=TendbClusterSpiderUpgradeContext())
        return

    def migrate_upgrade(self):
        """
        新版本替换升级spider节点
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines = []
        for info in self.data["infos"]:
            sub_pipelines.append(
                self.migrate_upgrade_for_cluster(
                    cluster_id=info["cluster_id"],
                    spider_master_ip_list=info["spider_master_ip_list"],
                    spider_slave_ip_list=info["spider_slave_ip_list"],
                    new_db_module_id=info["new_db_module_id"],
                    new_pkg_id=info["pkg_id"],
                )
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline(init_trans_data_class=SystemInfoContext())

    def migrate_upgrade_for_cluster(
        self,
        cluster_id: int,
        spider_master_ip_list: list,
        spider_slave_ip_list: list,
        new_db_module_id: int,
        new_pkg_id: int,
    ):
        """
        根据集群维度，并发处理每个集群的替换节点信息
        流程步骤：
        1：修改cluster元数据，更改新的db_module_id版本
        1：给集群新版本的spider实例(包括spider_master和spider_slave的角色)
        2：人工确认
        3：给集群所有旧版本spider实例下架(包括spider_master和spider_slave的角色)
        """
        # 获取对应集群相关对象
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
            old_spider_master = list(
                cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                )
            )
            old_spider_slave = list(
                cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
                )
            )
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
            )

        spiders = ProxyInstance.objects.filter(cluster=cluster)
        spider_pkg = Package.objects.get(id=new_pkg_id, pkg_type=MediumEnum.Spider)

        # 检查是否跨版本升级
        is_cross_major_version, from_version_map = check_cross_major_version_upgrade(spiders, spider_pkg.name)

        sub_pipeline = SubBuilder(
            root_id=self.root_id, data={"uid": self.data["uid"], "bk_biz_id": int(self.data["bk_biz_id"])}
        )
        # 只有在跨版本升级时才进行关键字检查
        if is_cross_major_version:
            add_spider_keyword_check_act(
                sub_pipeline, cluster_id, from_version_map, spider_pkg.name, self.force_upgrade
            )

        # 先执行扩容spider master实例
        sub_pipeline.add_sub_pipeline(
            self.add_spider_nodes_with_cluster(
                cluster_id=cluster_id,
                add_spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
                add_spider_hosts=spider_master_ip_list,
                new_db_module_id=new_db_module_id,
                global_pkg_id=new_pkg_id,
            )
        )

        # 再执行扩容spider slave实例, 如果spider slave集群存在
        if spider_slave_ip_list:
            sub_pipeline.add_sub_pipeline(
                self.add_spider_nodes_with_cluster(
                    cluster_id=cluster_id,
                    add_spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value,
                    add_spider_hosts=spider_slave_ip_list,
                    new_db_module_id=new_db_module_id,
                    global_pkg_id=new_pkg_id,
                )
            )

        # 释放对单据的互斥锁
        # 单据类型：TenDBCLuster的SQL变更/强制变更/模拟执行/授权
        sub_pipeline.add_act(
            act_name=_("释放部分单据互斥锁"),
            act_component_code=AddUnlockTicketTypeConfigComponent.code,
            kwargs=asdict(
                AddUnLockTicketTypeKwargs(
                    cluster_ids=[cluster_id], unlock_ticket_type_list=self.temporary_unlock_ticket_type_list
                )
            ),
        )

        # 人工确认前，解除释放互斥锁，重新互斥
        sub_pipeline.add_act(
            act_name=_("人工确认，解除释放，重新判断互斥条件"),
            act_component_code=PauseWithTicketLockCheckComponent.code,
            kwargs=asdict(
                ReleaseUnLockTicketTypeKwargs(
                    cluster_ids=[cluster_id],
                    release_unlock_ticket_type_list=self.temporary_unlock_ticket_type_list,
                )
            ),
        )

        # 缩容spider master 节点
        sub_pipeline.add_sub_pipeline(
            self.reduce_spider_nodes_with_cluster(
                cluster_id=cluster_id,
                spider_reduced_hosts=[{"ip": s.machine.ip} for s in old_spider_master],
                reduce_spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
                spider_reduced_to_count_snapshot=0,
                is_check_min_count=False,
            )
        )

        # 缩容spider slave 节点
        if old_spider_slave:
            sub_pipeline.add_sub_pipeline(
                self.reduce_spider_nodes_with_cluster(
                    cluster_id=cluster_id,
                    spider_reduced_hosts=[{"ip": s.machine.ip} for s in old_spider_slave],
                    reduce_spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value,
                    spider_reduced_to_count_snapshot=0,
                    is_check_min_count=False,
                    is_check_process=self.is_check_process,
                )
            )

        # 更新集群模块信息
        add_cluster_module_update_act(sub_pipeline, cluster_id, new_db_module_id)

        return sub_pipeline.build_sub_process(sub_name=_("[{}]spider节点迁移升级流程".format(cluster.immute_domain)))
