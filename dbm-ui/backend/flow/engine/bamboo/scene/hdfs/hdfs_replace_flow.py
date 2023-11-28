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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import ConfigTypeEnum, HdfsRoleEnum, UserName
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.hdfs.exceptions import ReplaceMachineCountException, ReplaceMachineNullException
from backend.flow.engine.bamboo.scene.hdfs.hdfs_sub_flow import HdfsOperationFlow
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.hdfs.hdfs_act_playload import gen_host_name_by_role, get_cluster_config
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, HdfsReplaceContext
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class HdfsReplaceFlow(HdfsOperationFlow):
    """
    构建hdfs集群申请流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
         @param data : 单据传递参数
        """
        super().__init__(root_id, data)
        self.__init_data_with_role()

    def replace_hdfs_flow(self):
        """
        替换 hdfs集群 节点
        """
        # Builder 传参 为封装好角色IP的数据结构
        hdfs_pipeline = Builder(root_id=self.root_id, data=self.data_with_role)
        trans_files = GetFileList(db_type=DBType.Hdfs)

        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data_with_role["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = HdfsReplaceContext.__name__
        act_kwargs.file_list = trans_files.hdfs_apply(db_version=self.data_with_role["db_version"])

        # 需要将配置项写入
        act_kwargs.is_update_trans_data = True

        scale_up_data = self.__get_replace_dn_data(TicketType.HDFS_SCALE_UP)
        add_dn_sub_pipeline = self.build_add_dn_sub_flow(act_kwargs, scale_up_data)
        hdfs_pipeline.add_sub_pipeline(add_dn_sub_pipeline.build_sub_process(sub_name=_("集群DN替换-扩容DN")))

        shrink_data = self.__get_replace_dn_data(TicketType.HDFS_SHRINK)
        del_dn_sub_pipeline = self.build_del_dn_sub_flow(act_kwargs, shrink_data)
        hdfs_pipeline.add_sub_pipeline(del_dn_sub_pipeline.build_sub_process(sub_name=_("集群DN替换-缩容DN")))

        hdfs_pipeline.run_pipeline()

    def __init_data_with_role(self):
        data_with_role = copy.deepcopy(self.data)
        data_with_role["ip_source"] = IpSource.MANUAL_INPUT

        # 从cluster_id 获取cluster
        cluster = Cluster.objects.get(id=self.data["cluster_id"])
        data_with_role["domain"] = cluster.immute_domain
        data_with_role["cluster_name"] = cluster.name
        data_with_role["db_version"] = cluster.major_version
        data_with_role["bk_biz_id"] = cluster.bk_biz_id
        data_with_role["bk_cloud_id"] = cluster.bk_cloud_id

        data_with_role["nn_ips"] = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_NAME_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        data_with_role["zk_ips"] = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_ZOOKEEPER).values_list(
                "machine__ip", flat=True
            )
        )
        data_with_role["jn_ips"] = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_JOURNAL_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        data_with_role["dn_ips"] = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_DATA_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        cluster_config = get_cluster_config(
            bk_biz_id=str(cluster.bk_biz_id),
            cluster_domain=cluster.immute_domain,
            db_version=cluster.major_version,
            conf_type=ConfigTypeEnum.DBConf,
        )

        all_ip_hosts = dict()
        all_ip_hosts[cluster_config["nn1_ip"]] = cluster_config["nn1_host"]
        all_ip_hosts[cluster_config["nn2_ip"]] = cluster_config["nn2_host"]

        data_with_role["nn1_ip"] = cluster_config["nn1_ip"]
        data_with_role["nn2_ip"] = cluster_config["nn2_ip"]
        all_ip_set = {data_with_role["nn1_ip"], data_with_role["nn2_ip"]}
        all_ip_set.update(data_with_role["zk_ips"])
        # used by db_meta
        data_with_role["master_ips"] = list(all_ip_set)

        all_ip_set.update(data_with_role["dn_ips"])
        data_with_role["all_ips"] = list(all_ip_set)

        data_with_role["http_port"] = int(cluster_config["http_port"])
        data_with_role["rpc_port"] = int(cluster_config["rpc_port"])
        # 用户名密码改由密码服务拉取
        password = PayloadHandler.get_bigdata_password_by_cluster(
            cluster, data_with_role["rpc_port"], UserName.HDFS_DEFAULT
        )
        # 若密码获取不到，从dbconfig获取
        if not password:
            logger.error("cannot get auth info from password service")
            data_with_role["username"] = cluster_config["username"]
            data_with_role["password"] = cluster_config["password"]
        else:
            logger.debug("get auth info from password")
            data_with_role["username"] = UserName.HDFS_DEFAULT
            data_with_role["password"] = password

        data_with_role["dfs_include_file"] = cluster_config["hdfs-site.dfs.hosts"]
        data_with_role["dfs_exclude_file"] = cluster_config["hdfs-site.dfs.hosts.exclude"]

        dn_ip_hosts = {dn_ip: gen_host_name_by_role(dn_ip, "dn") for dn_ip in data_with_role["dn_ips"]}

        if HdfsRoleEnum.DataNode.value not in self.data["old_nodes"]:
            logger.error(_("没有需要替换的角色IP"))
            raise ReplaceMachineNullException()
        else:
            data_with_role["del_dn_ips"] = [node["ip"] for node in self.data["old_nodes"][HdfsRoleEnum.DataNode]]
            data_with_role["new_dn_ips"] = [node["ip"] for node in self.data["new_nodes"][HdfsRoleEnum.DataNode]]
            if len(data_with_role["del_dn_ips"]) != len(data_with_role["new_dn_ips"]):
                logger.error(_("替换HDFS DataNode角色IP不一致"))
                raise ReplaceMachineCountException(hdfs_role=HdfsRoleEnum.DataNode)

        new_dn_ip_hosts = {dn_ip: gen_host_name_by_role(dn_ip, "dn") for dn_ip in data_with_role["new_dn_ips"]}
        all_ip_hosts = dict(**all_ip_hosts, **dn_ip_hosts, **new_dn_ip_hosts)
        data_with_role["all_ip_hosts"] = all_ip_hosts
        # remain ip for manager
        # 剩余可写入haproxy实例，与缩容处理不同，替换过程存在全部节点替换的情况，后续待优化
        data_with_role["remain_dn_ips"] = data_with_role["new_dn_ips"]

        self.data_with_role = data_with_role

    def __get_replace_dn_data(self, ticket_type: TicketType) -> dict:

        data = copy.deepcopy(self.data_with_role)
        data["ticket_type"] = ticket_type.value
        # 根据不同单据类型生成dn_hosts字段的值，在更新节点配置中需要
        if ticket_type == TicketType.HDFS_SCALE_UP:
            data["dn_hosts"] = [data["all_ip_hosts"][dn_ip] for dn_ip in data["new_dn_ips"]]
        elif ticket_type == TicketType.HDFS_SHRINK:
            data["dn_hosts"] = [data["all_ip_hosts"][dn_ip] for dn_ip in data["del_dn_ips"]]

        return data
