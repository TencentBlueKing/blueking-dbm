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

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import ConfigTypeEnum, DnsOpType, HdfsRoleEnum, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.bigdata_manager_service import (
    BigdataManagerComponent,
    get_manager_ip,
)
from backend.flow.plugins.components.collections.hdfs.exec_actuator_script import ExecuteHdfsActuatorScriptComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_payload import GetHdfsActPayloadComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_db_meta import HdfsDBMetaComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_dns_manage import HdfsDnsManageComponent
from backend.flow.plugins.components.collections.hdfs.trans_flies import TransFileComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.hdfs.hdfs_act_playload import HdfsActPayload, gen_host_name_by_role, get_cluster_config
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, DnsKwargs, HdfsApplyContext

logger = logging.getLogger("flow")


class HdfsShrinkFlow(object):
    """
    构建hdfs缩容流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
         @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.__init_data_with_role()

    def shrink_hdfs_flow(self):

        """
        缩容hdfs集群流程
        """
        # Builder 传参 为封装好角色IP的数据结构
        hdfs_pipeline = Builder(root_id=self.root_id, data=self.data_with_role)
        trans_files = GetFileList(db_type=DBType.Hdfs)

        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data_with_role["bk_cloud_id"])

        # 需要将配置项写入
        act_kwargs.is_update_trans_data = True
        act_kwargs.set_trans_data_dataclass = HdfsApplyContext.__name__
        act_kwargs.file_list = trans_files.hdfs_actuator()

        hdfs_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetHdfsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.exec_ip = self.data_with_role["dn_ips"]
        hdfs_pipeline.add_act(
            act_name=_("下发hdfs介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = self.data_with_role["nn_ips"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_add_exclude_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("添加数据节点到exclude"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        act_kwargs.exec_ip = self.data_with_role["nn1_ip"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_refresh_nodes_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("刷新节点配置"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )
        # 访问某一台DN节点的代理NN WEB服务
        act_kwargs.exec_ip = self.data_with_role["dn_ips"][0]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_check_decommission_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("检查节点退役信息"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 从include剔除数据节点
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_remove_include_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("include剔除数据节点"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 执行 刷新HDFS节点
        act_kwargs.exec_ip = self.data_with_role["nn1_ip"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_refresh_nodes_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("刷新节点配置"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )
        # 从exclude剔除数据节点
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_remove_exclude_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("exclude剔除数据节点"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 执行 刷新HDFS节点
        act_kwargs.exec_ip = self.data_with_role["nn1_ip"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_refresh_nodes_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("刷新节点配置"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 检查下架节点上是否安装haproxy
        manager_ip = get_manager_ip(
            bk_biz_id=self.data_with_role["bk_biz_id"],
            db_type=DBType.Hdfs,
            cluster_name=self.data_with_role["cluster_name"],
            service_type=ManagerServiceType.HA_PROXY,
        )
        if manager_ip in self.data_with_role["del_dn_ips"]:
            # 更新haproxy实例信息
            manager_kwargs = BigdataManagerKwargs(
                manager_op_type=ManagerOpType.UPDATE,
                db_type=DBType.Hdfs,
                service_type=ManagerServiceType.HA_PROXY,
                manager_ip=self.data_with_role["remain_dn_ips"][0],
                manager_port=self.data_with_role["http_port"],
            )
            hdfs_pipeline.add_act(
                act_name=_("更新haproxy实例信息"),
                act_component_code=BigdataManagerComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
            )
        # 缩容后对机器进行清理
        del_dn_ip_acts = []
        for ip in self.data_with_role["del_dn_ips"]:
            # 停止进程 + 数据清理
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_data_clean_payload.__name__
            act_kwargs.exec_ip = ip
            act = {
                "act_name": _("HDFS集群节点清理-{}").format(ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            del_dn_ip_acts.append(act)

        hdfs_pipeline.add_parallel_acts(acts_list=del_dn_ip_acts)

        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.UPDATE,
            domain_name=self.data_with_role["domain"],
            dns_op_exec_port=self.data_with_role["rpc_port"],
            bk_cloud_id=self.data_with_role["bk_cloud_id"],
        )

        hdfs_pipeline.add_act(
            act_name=_("更新域名"),
            act_component_code=HdfsDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 包含将机器CC挪到待回收
        hdfs_pipeline.add_act(
            act_name=_("DBMeta删除下架IP"), act_component_code=HdfsDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        hdfs_pipeline.run_pipeline()

    def __init_data_with_role(self):
        data_with_role = copy.deepcopy(self.data)
        # 从cluster_id 获取cluster
        cluster = Cluster.objects.get(id=self.data["cluster_id"])
        self.cluster = cluster
        data_with_role["domain"] = cluster.immute_domain

        data_with_role["cluster_name"] = cluster.name
        data_with_role["db_version"] = cluster.major_version
        data_with_role["bk_biz_id"] = cluster.bk_biz_id
        data_with_role["bk_cloud_id"] = cluster.bk_cloud_id

        data_with_role["nn_ips"] = list(
            StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.HDFS_NAME_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        data_with_role["zk_ips"] = list(
            StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.HDFS_ZOOKEEPER).values_list(
                "machine__ip", flat=True
            )
        )
        data_with_role["jn_ips"] = list(
            StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.HDFS_JOURNAL_NODE).values_list(
                "machine__ip", flat=True
            )
        )

        data_with_role["dn_ips"] = list(
            StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.HDFS_DATA_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        data_with_role["del_dn_ips"] = [node["ip"] for node in self.data["nodes"][HdfsRoleEnum.DataNode]]

        cluster_config = get_cluster_config(
            bk_biz_id=str(cluster.bk_biz_id),
            cluster_domain=cluster.immute_domain,
            db_version=cluster.major_version,
            conf_type=ConfigTypeEnum.DBConf,
        )

        data_with_role["nn1_ip"] = cluster_config["nn1_ip"]
        data_with_role["nn2_ip"] = cluster_config["nn2_ip"]
        data_with_role["http_port"] = int(cluster_config["http_port"])
        data_with_role["rpc_port"] = int(cluster_config["rpc_port"])
        data_with_role["haproxy_passwd"] = cluster_config["password"]
        data_with_role["dfs_exclude_file"] = cluster_config["hdfs-site.dfs.hosts.exclude"]
        data_with_role["dfs_include_file"] = cluster_config["hdfs-site.dfs.hosts"]
        data_with_role["dn_hosts"] = [gen_host_name_by_role(dn_ip, "dn") for dn_ip in data_with_role["del_dn_ips"]]

        all_ip_hosts = dict()
        all_ip_hosts[cluster_config["nn1_ip"]] = cluster_config["nn1_host"]
        all_ip_hosts[cluster_config["nn2_ip"]] = cluster_config["nn2_host"]
        all_ip_hosts = dict(
            {dn_ip: gen_host_name_by_role(dn_ip, "dn") for dn_ip in data_with_role["dn_ips"]}, **all_ip_hosts
        )

        data_with_role["all_ip_hosts"] = all_ip_hosts

        # remain ip for manager
        data_with_role["remain_dn_ips"] = [
            ip for ip in data_with_role["dn_ips"] if ip not in data_with_role["del_dn_ips"]
        ]
        self.data_with_role = data_with_role
