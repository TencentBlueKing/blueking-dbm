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
import logging.config
from collections import defaultdict
from dataclasses import asdict
from datetime import timedelta
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import check_sub_flow
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import (
    standardize_mysql_cluster_by_ip_subflow,
)
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SpiderSwitchContext
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class RemoteMasterSlaveSwitchFlow(object):
    """
    构建TenDB Cluster集群remote存储对的互切流程，产品形态是整机切换，保证同一台机器的所有实例要不master角色，要不slave角色
    目前集群维度的互切流程如下：
    1：下发db-actuator介质到中控primary机器
    2：下发中控执行互切逻辑命令，命令包括有：
    2.1：做前置检查
    2.2：中控执行切换主分片
    2.3：断开newMaster同步
    2.4：授权repl账号给oldMaster
    2.3：建立新的复制关系
    2.3：断开newMaster同步
    3: 修改元数据
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    # 公有方法 - 子类可以调用
    def remote_switch(self):
        """
        构建remote互切的流程
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = self._extract_cluster_ids()
        switch_pipeline = self._create_main_pipeline(cluster_ids)
        cluster_switch_map = self.build_cluster_switch_mapping()
        sub_pipelines = self.build_cluster_sub_pipelines(cluster_switch_map)

        switch_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        switch_pipeline.run_pipeline(is_drop_random_user=True, init_trans_data_class=SpiderSwitchContext())

    # 受保护的方法 - 子类可以调用和重写
    def _extract_cluster_ids(self):
        """提取集群ID列表"""
        return [info["cluster_id"] for info in self.data["infos"]]

    # 受保护的方法 - 子类可以重写以自定义行为
    def _create_main_pipeline(self, cluster_ids):
        """创建主流水线"""
        return Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids)))

    def build_cluster_switch_mapping(self):
        """构建集群切换映射关系"""
        cluster_switch_map = defaultdict(list)
        for info in self.data["infos"]:
            cluster_switch_map[info["cluster_id"]].extend(info["switch_tuples"])
        return cluster_switch_map

    def get_cluster_and_validate(self, cluster_id):
        """获取并验证集群对象"""
        try:
            return Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
            )

    def get_cluster_components(self, cluster):
        """获取集群相关组件"""
        spiders = cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING)
        ctl_primary = cluster.tendbcluster_ctl_primary_address()
        return spiders, ctl_primary

    def calculate_check_parameters(self, sub_flow_context, cluster, switch_tuples, spiders):
        """计算预检测需要的参数"""
        check_client_conn_inst = []
        verify_checksum_tuples = []
        slave_addr_tuples = []

        if sub_flow_context["is_check_process"]:
            check_client_conn_inst = [s.ip_port for s in spiders]

        if sub_flow_context["is_verify_checksum"]:
            verify_checksum_tuples, slave_addr_tuples = self.build_checksum_tuples(cluster, switch_tuples)

        return check_client_conn_inst, verify_checksum_tuples, slave_addr_tuples

    def build_checksum_tuples(self, cluster, switch_tuples):
        """构建checksum检测元组"""
        verify_checksum_tuples = []
        slave_addr_tuples = []

        for t in switch_tuples:
            objs = cluster.storageinstance_set.filter(machine__ip=t["master"]["ip"])
            for master in objs:
                slave = StorageInstanceTuple.objects.get(ejector=master).receiver
                verify_checksum_tuples.append({"master": master.ip_port, "slave": slave.ip_port})
                slave_addr_tuples.append(slave.ip_port)

        return verify_checksum_tuples, slave_addr_tuples

    def add_pre_check_sub_flow(
        self,
        sub_pipeline,
        sub_flow_context,
        cluster,
        check_client_conn_inst,
        verify_checksum_tuples,
        slave_addr_tuples,
    ):
        """添加预检测子流程"""
        sub_flow = check_sub_flow(
            uid=self.data["uid"],
            root_id=self.root_id,
            cluster=cluster,
            is_check_client_conn=sub_flow_context["is_check_process"],
            is_verify_checksum=sub_flow_context["is_verify_checksum"],
            check_client_conn_inst=check_client_conn_inst,
            verify_checksum_tuples=verify_checksum_tuples,
            is_check_delay=sub_flow_context["is_check_delay"],
            slave_addr_tuples=slave_addr_tuples,
        )
        if sub_flow:
            sub_pipeline.add_sub_pipeline(sub_flow=sub_flow)

    def add_download_media_act(self, sub_pipeline, cluster, ctl_primary):
        """添加下发介质活动"""
        sub_pipeline.add_act(
            act_name=_("下发db-actuator介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    exec_ip=ctl_primary.split(":")[0],
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

    def add_master_switch_act(self, sub_pipeline, cluster, ctl_primary, cluster_id, switch_tuples, batch_idx):
        """添加主节点切换活动"""
        sub_pipeline.add_act(
            act_name=_("执行切换主节点路由"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    get_mysql_payload_func=MysqlActPayload.tendb_cluster_remote_switch.__name__,
                    exec_ip=ctl_primary.split(":")[0],
                    cluster={"cluster_id": cluster_id, "switch_tuples": switch_tuples, "batch_id": batch_idx},
                )
            ),
            write_payload_var=SpiderSwitchContext.get_new_masters_bin_pos_var_name(),
        )

    def add_slave_switch_act(self, sub_pipeline, cluster, ctl_primary, cluster_id, switch_tuples, batch_idx):
        """添加从节点切换活动"""
        sub_pipeline.add_act(
            act_name=_("转换复制关系,并切换从分片的路由"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    get_mysql_payload_func=MysqlActPayload.tendb_cluster_slave_spt_switch.__name__,
                    exec_ip=ctl_primary.split(":")[0],
                    cluster={"cluster_id": cluster_id, "switch_tuples": switch_tuples, "batch_id": batch_idx},
                )
            ),
        )

    def add_meta_update_act(self, sub_pipeline, cluster_id, switch_tuples, force):
        """添加元数据更新活动"""
        sub_pipeline.add_act(
            act_name=_("变更db_meta元信息"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SpiderDBMeta.remote_switch.__name__,
                    cluster={
                        "cluster_id": cluster_id,
                        "switch_tuples": switch_tuples,
                        "force": force,
                    },
                )
            ),
        )

    def add_standardization_flows(self, sub_pipeline, sub_flow_context, cluster, switch_tuples):
        """添加标准化流程"""
        master_ips = [info["master"]["ip"] for info in switch_tuples]
        slave_ips = [info["slave"]["ip"] for info in switch_tuples]

        standardization_flows = [
            self.create_standardization_flow(sub_flow_context, cluster, master_ips),
            self.create_standardization_flow(sub_flow_context, cluster, slave_ips),
        ]

        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=standardization_flows)

    def create_standardization_flow(self, sub_flow_context, cluster, ips):
        """创建标准化流程"""
        return standardize_mysql_cluster_by_ip_subflow(
            root_id=self.root_id,
            data=copy.deepcopy(sub_flow_context),
            bk_cloud_id=cluster.bk_cloud_id,
            bk_biz_id=cluster.bk_biz_id,
            ips=ips,
            with_actuator=True,
            with_cc_standardize=False,
            with_instance_standardize=False,
            with_bk_plugin=False,
            with_collect_sysinfo=False,
        )

    def add_alarm_shield_act(self, sub_pipeline, cluster):
        """添加告警屏蔽活动"""
        # 获取集群的所有存储实例IP
        storage_ips = list(cluster.storageinstance_set.values_list("machine__ip", flat=True).distinct())

        sub_pipeline.add_act(
            act_name=_("屏蔽集群 {} 告警2小时").format(cluster.name),
            act_component_code=AddAlarmShieldComponent.code,
            kwargs={
                "begin_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": (datetime.datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "description": _("集群 {} 主从切换操作").format(cluster.immute_domain),
                "dimensions": [
                    {
                        "name": "instance_host",
                        "values": storage_ips,
                    }
                ],
            },
        )

    def add_disable_alarm_shield_act(self, sub_pipeline):
        """添加解除告警屏蔽活动"""
        sub_pipeline.add_act(act_name=_("解除告警屏蔽"), act_component_code=DisableAlarmShieldComponent.code, kwargs={})

    def build_cluster_sub_pipelines(self, cluster_switch_map):
        """构建集群子流水线"""
        sub_pipelines = []
        batch_idx = 1000

        for cluster_id, switch_tuples in cluster_switch_map.items():
            sub_pipeline = self._build_single_cluster_pipeline(cluster_id, switch_tuples, batch_idx)
            sub_pipelines.append(sub_pipeline)
            batch_idx += 1

        return sub_pipelines

    def _build_single_cluster_pipeline(self, cluster_id, switch_tuples, batch_idx):
        """构建单个集群的子流水线"""
        # 准备子流程上下文
        sub_flow_context = copy.deepcopy(self.data)
        sub_flow_context.pop("infos")

        # 获取集群相关信息
        cluster = self.get_cluster_and_validate(cluster_id)
        spiders, ctl_primary = self.get_cluster_components(cluster)

        # 计算检测参数
        check_client_conn_inst, verify_checksum_tuples, slave_addr_tuples = self.calculate_check_parameters(
            sub_flow_context, cluster, switch_tuples, spiders
        )

        # 创建子流水线
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

        # 添加各个步骤
        self.add_pre_check_sub_flow(
            sub_pipeline, sub_flow_context, cluster, check_client_conn_inst, verify_checksum_tuples, slave_addr_tuples
        )
        self.add_download_media_act(sub_pipeline, cluster, ctl_primary)

        # 新增告警屏蔽步骤
        self.add_alarm_shield_act(sub_pipeline, cluster)

        self.add_master_switch_act(sub_pipeline, cluster, ctl_primary, cluster_id, switch_tuples, batch_idx)
        self.add_slave_switch_act(sub_pipeline, cluster, ctl_primary, cluster_id, switch_tuples, batch_idx)
        force = self.data.get("force", False)  # 主从切换默认不强制
        self.add_meta_update_act(sub_pipeline, cluster_id, switch_tuples, force)
        self.add_standardization_flows(sub_pipeline, sub_flow_context, cluster, switch_tuples)

        # 新增解除告警屏蔽步骤
        self.add_disable_alarm_shield_act(sub_pipeline)

        return sub_pipeline.build_sub_process(sub_name=_("[{}]集群后端切换".format(cluster.name)))
