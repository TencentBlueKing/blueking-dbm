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
import datetime
import logging
from dataclasses import asdict
from datetime import timedelta
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.enums.instance_phase import InstancePhase
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.spider.spider_switch_nodes import TenDBClusterSwitchNodesFlow
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.add_unlock_ticket_type_config import (
    AddUnlockTicketTypeConfigComponent,
)
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.common.pause_with_ticket_lock_check import (
    PauseWithTicketLockCheckComponent,
)
from backend.flow.plugins.components.collections.mysql.check_client_connections import CheckClientConnComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.upgrade_key_word_check import UpgradeKeyWordCheckComponent
from backend.flow.utils.base.base_dataclass import AddUnLockTicketTypeKwargs, ReleaseUnLockTicketTypeKwargs
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckClientConnKwargs,
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    RecycleDnsRecordKwargs,
    UpgradeKeyWordCheckKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.mysql_version_parse import (
    get_spider_sub_version_by_pkg_name,
    spider_cross_major_version,
    tspider_version_parse,
)
from backend.flow.utils.spider.spider_check_constants import BASIC_CHECK_TYPES

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
        self.data = data  # 原始数据
        self.upgrade_local = data.get("upgrade_local", False)  # 是否本地升级
        # 提取所有涉及的集群ID，去重后保存
        self.cluster_ids = list(set([i["cluster_id"] for i in self.data["infos"]]))

    def add_alarm_shield_act(self, sub_pipeline, cluster):
        """添加告警屏蔽活动"""
        # 获取集群的所有spider实例IP
        spider_ips = list(cluster.proxyinstance_set.values_list("machine__ip", flat=True).distinct())

        sub_pipeline.add_act(
            act_name=_("屏蔽集群 {} spider节点告警2小时").format(cluster.name),
            act_component_code=AddAlarmShieldComponent.code,
            kwargs={
                "begin_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": (datetime.datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "description": _("集群 {} spider节点升级操作").format(cluster.immute_domain),
                "dimensions": [
                    {
                        "name": "instance_host",
                        "values": spider_ips,
                    }
                ],
            },
        )

    def add_disable_alarm_shield_act(self, sub_pipeline):
        """添加解除告警屏蔽活动"""
        sub_pipeline.add_act(act_name=_("解除告警屏蔽"), act_component_code=DisableAlarmShieldComponent.code, kwargs={})

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

    def filter_spiders_by_version(self, cluster_id: int, target_version: str):
        """
        过滤掉版本已经等于待升级版本的spider实例

        Args:
            cluster_id: 集群ID
            target_version: 目标升级版本

        Returns:
            tuple: (需要升级的spider实例列表, 已经是目标版本的spider实例列表)
        """
        cluster = Cluster.objects.get(id=cluster_id)
        all_spiders = ProxyInstance.objects.filter(cluster=cluster)

        if len(all_spiders) <= 0:
            raise DBMetaException(message=_("根据cluster ids:{}无法找到对应的proxy实例").format(cluster_id))

        target_version_num = tspider_version_parse(target_version)
        spiders_to_upgrade = []
        spiders_already_target_version = []

        for spider_ins in all_spiders:
            current_version_num = tspider_version_parse(spider_ins.version)
            if current_version_num == target_version_num:
                spiders_already_target_version.append(spider_ins)
                logger.info(
                    _("Spider实例 {}:{} 版本 {} 已经是目标版本，跳过升级").format(
                        spider_ins.machine.ip, spider_ins.port, spider_ins.version
                    )
                )
            else:
                spiders_to_upgrade.append(spider_ins)

        logger.info(
            _("集群 {} 共有 {} 个spider实例，其中 {} 个需要升级，{} 个已经是目标版本").format(
                cluster.immute_domain, len(all_spiders), len(spiders_to_upgrade), len(spiders_already_target_version)
            )
        )

        return spiders_to_upgrade, spiders_already_target_version

    # spider_ins.tendbclusterspiderext.spider_role
    def __pre_check(self):
        """
        检查升级版本和源版本
        """
        for info in self.data["infos"]:
            pkg_id = info["pkg_id"]
            cluster_id = info["cluster_id"]
            spider_pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.Spider)
            new_spider_version_num = tspider_version_parse(spider_pkg.name)
            cluster = Cluster.objects.get(id=cluster_id)
            spiders = ProxyInstance.objects.filter(cluster=cluster)

            # 获取当前版本信息用于关键字检查
            current_versions = set()
            for spider_ins in spiders:
                current_version = tspider_version_parse(spider_ins.version)
                current_versions.add(spider_ins.version)
                if current_version >= new_spider_version_num:
                    logger.error(_("待升级版本 {} 需要大于当前版本 {}").format(new_spider_version_num, current_version))
                    raise DBMetaException(message=_("待升级版本大于等于新版本，请确认升级的版本"))

            if not self.local_upgrade:
                spider_master_ip_list = info["spider_master_ip_list"]
                spider_slave_ip_list = info.get("spider_slave_ip_list", [])
                master_spiders_count = cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                ).count()
                if master_spiders_count != len(spider_master_ip_list):
                    raise DBMetaException(message=_("待升级spiderMaster节点数传入ip节点数不一致,请确认"))
                slave_spiders_count = cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
                ).count()
                if slave_spiders_count > 0 and len(spider_slave_ip_list) != slave_spiders_count:
                    raise DBMetaException(message=_("待升级spiderSlave节点数传入ip节点数不一致,请确认"))

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
            spiders_to_upgrade, spiders_already_target_version = self.filter_spiders_by_version(
                cluster_id=cluster_id, target_version=spider_pkg.name
            )

            # 如果没有需要升级的实例，跳过当前集群
            if len(spiders_to_upgrade) == 0:
                logger.info(_("集群 {} 所有spider实例版本已经是目标版本，跳过升级").format(cluster.immute_domain))
                continue

            spider_ips = []
            spider_master_ins = []
            for spider_ins in spiders_to_upgrade:
                spider_ips.append(spider_ins.machine.ip)
                spider_role = spider_ins.tendbclusterspiderext.spider_role
                if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                    spider_master_ins.append(f"{spider_ins.machine.ip}{IP_PORT_DIVIDER}{spider_ins.port}")

            # 切换前做预检测
            if not self.force_upgrade:
                sub_pipeline.add_act(
                    act_name=_("检查Master Spider端连接情况"),
                    act_component_code=CheckClientConnComponent.code,
                    kwargs=asdict(
                        CheckClientConnKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            check_instances=spider_master_ins,
                        )
                    ),
                )
            # 提前下发文件
            sub_pipeline.add_act(
                act_name=_("下发升级的安装包"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=spider_ips,
                        file_list=GetFileList(db_type=DBType.MySQL).spider_upgrade_package(pkg_id=pkg_id),
                    )
                ),
            )

            # 添加告警屏蔽
            self.add_alarm_shield_act(sub_pipeline, cluster)

            spider_slave_upgrade_pipelines = []
            spider_master_upgrade_pipelines = []
            new_spider_version = get_spider_sub_version_by_pkg_name(spider_pkg.name)
            for spider_ins in spiders_to_upgrade:
                spider_role = spider_ins.tendbclusterspiderext.spider_role
                spider_ip = spider_ins.machine.ip
                spider_port = spider_ins.port
                if spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE:
                    spider_slave_upgrade_pipelines.append(
                        self.upgrade_spider_subflow(
                            ip=spider_ip,
                            bk_cloud_id=bk_cloud_id,
                            pkg_id=pkg_id,
                            domain=cluster.immute_domain,
                            spider_version=new_spider_version,
                            spider_port=spider_port,
                            force_upgrade=True,
                            sub_flow_context=sub_flow_context,
                        )
                    )
                if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                    spider_master_upgrade_pipelines.append(
                        self.upgrade_spider_subflow(
                            ip=spider_ip,
                            bk_cloud_id=bk_cloud_id,
                            pkg_id=pkg_id,
                            domain=cluster.immute_domain,
                            spider_version=new_spider_version,
                            spider_port=spider_port,
                            force_upgrade=True,
                            sub_flow_context=sub_flow_context,
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
            sub_pipeline.add_parallel_sub_pipeline(part2)
            # 更新集群模块信息
            if new_db_module_id != cluster.db_module_id:
                sub_pipeline.add_act(
                    act_name=_("更新集群db模块信息"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.update_cluster_module.__name__,
                            cluster={
                                "cluster_ids": [cluster_id],
                                "new_module_id": new_db_module_id,
                            },
                        )
                    ),
                )

            # 解除告警屏蔽
            self.add_disable_alarm_shield_act(sub_pipeline)

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("[{}]本地升级spider版本".format(cluster.immute_domain)))
            )
        spider_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        spider_upgrade_pipeline.run_pipeline()
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

        # 获取当前版本信息用于关键字检查
        from_version_map = {}

        # 检查是否跨版本升级
        is_cross_major_version = False
        for spider_ins in spiders:
            # 判断是否跨主版本
            if spider_cross_major_version(
                tspider_version_parse(spider_pkg.name), tspider_version_parse(spider_ins.version)
            ):
                is_cross_major_version = True
                # 跨版本时，只需要存一个检查版本的实例
                # spider_ins.version 存的值 1.15
                if not from_version_map:
                    from_version_map[spider_ins.version] = [f"{spider_ins.machine.ip}:{spider_ins.port}"]

        sub_pipeline = SubBuilder(
            root_id=self.root_id, data={"uid": self.data["uid"], "bk_biz_id": int(self.data["bk_biz_id"])}
        )
        # 只有在跨版本升级时才进行关键字检查
        if is_cross_major_version:
            sub_pipeline.add_act(
                act_name=_("升级前关键字检查"),
                act_component_code=UpgradeKeyWordCheckComponent.code,
                kwargs=asdict(
                    UpgradeKeyWordCheckKwargs(
                        cluster_id=cluster_id,
                        from_version_map=from_version_map,
                        to_version=spider_pkg.name,
                        check_types=BASIC_CHECK_TYPES,
                        fail_on_conflict=not self.force_upgrade,
                    )
                ),
            )

        # 先执行扩容spider master实例
        sub_pipeline.add_sub_pipeline(
            self.add_spider_nodes_with_cluster(
                cluster_id=cluster_id,
                add_spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
                add_spider_hosts=spider_master_ip_list,
                new_db_module_id=new_db_module_id,
                new_pkg_id=new_pkg_id,
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
                    new_pkg_id=new_pkg_id,
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
                )
            )

        # 更新集群模块信息
        sub_pipeline.add_act(
            act_name=_("更新集群db模块信息"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_cluster_module.__name__,
                    cluster={
                        "cluster_ids": [cluster_id],
                        "new_module_id": new_db_module_id,
                    },
                )
            ),
        )

        return sub_pipeline.build_sub_process(sub_name=_("[{}]spider节点迁移升级流程".format(cluster.immute_domain)))

    def upgrade_spider_subflow(
        self,
        ip: str,
        bk_cloud_id: int,
        pkg_id: int,
        domain: str,
        spider_version: str,
        spider_port: int,
        force_upgrade: bool,
        sub_flow_context: dict,
    ):
        """
        定义upgrade tendbcluster spider 本地升级 的flow
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
        # 执行本地升级
        # 回收对应的域名关系
        sub_pipeline.add_act(
            act_name=_("回收对应spider域名解析"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs=asdict(
                RecycleDnsRecordKwargs(
                    bk_cloud_id=bk_cloud_id,
                    dns_op_exec_port=spider_port,
                    exec_ip=[ip],
                ),
            ),
        )
        cluster = {"proxy_ports": [spider_port], "pkg_id": pkg_id, "force_upgrade": force_upgrade}
        exec_act_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=bk_cloud_id)
        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_spider_upgrade_payload.__name__
        sub_pipeline.add_act(
            act_name=_("更新spider instance status -> upgrade"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                    cluster={"proxy_ip": ip, "phase": InstancePhase.UPGRADING, "status": InstanceStatus.UPGRADING},
                )
            ),
        )
        sub_pipeline.add_act(
            act_name=_("执行本地升级"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        # 更新proxy instance version 信息
        act_list = []
        act_list.append(
            {
                "act_name": _("更新spider version meta信息"),
                "act_component_code": MySQLDBMetaComponent.code,
                "kwargs": asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_proxy_instance_version.__name__,
                        cluster={"proxy_ip": ip, "version": spider_version},
                    )
                ),
            }
        )
        act_list.append(
            {
                "act_name": _("更新spider instance status -> online"),
                "act_component_code": MySQLDBMetaComponent.code,
                "kwargs": asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                        cluster={"proxy_ip": ip, "phase": InstancePhase.ONLINE, "status": InstanceStatus.RUNNING},
                    )
                ),
            }
        )
        sub_pipeline.add_parallel_acts(act_list)
        sub_pipeline.add_act(
            act_name=_("添加集群域名"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs=asdict(
                CreateDnsKwargs(
                    bk_cloud_id=bk_cloud_id,
                    add_domain_name=domain,
                    dns_op_exec_port=spider_port,
                    exec_ip=[ip],
                )
            ),
        )
        return sub_pipeline.build_sub_process(sub_name=_("{}spider实例升级").format(ip))
