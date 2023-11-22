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
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import ConfigTypeEnum, HdfsRoleEnum, UserName
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.hdfs.hdfs_sub_flow import HdfsOperationFlow
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.hdfs.hdfs_act_playload import gen_host_name_by_role, get_cluster_config
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, HdfsApplyContext

logger = logging.getLogger("flow")


class HdfsShrinkFlow(HdfsOperationFlow):
    """
    构建hdfs缩容流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
         @param data : 单据传递参数
        """
        super().__init__(root_id, data)
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

        del_dn_sub_pipeline = self.build_del_dn_sub_flow(act_kwargs, self.data_with_role)
        hdfs_pipeline.add_sub_pipeline(del_dn_sub_pipeline.build_sub_process(sub_name=_("集群DN替换-缩容DN")))

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
        # 用户名密码改由密码服务拉取
        password = PayloadHandler.get_bigdata_password_by_cluster(
            cluster, data_with_role["rpc_port"], UserName.HDFS_DEFAULT
        )
        # 若密码获取不到，从dbconfig获取
        if not password:
            logger.error("cannot get auth info from password service")
            data_with_role["username"] = cluster_config["username"]
            data_with_role["haproxy_passwd"] = cluster_config["password"]
        else:
            logger.debug("get auth info from password")
            data_with_role["username"] = UserName.HDFS_DEFAULT
            data_with_role["haproxy_passwd"] = password

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
