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
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterEntryType, InstanceInnerRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import CreateDnsKwargs, DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLHAEnableFlow(object):
    """
    构建mysql主从版启动流程抽象类，集群启动功能是已将禁用的集群重新让它提供服务，
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_ha_cluster_info(cluster_id: int) -> dict:
        """
        根据cluster_id 获取到集群相关信息
        @param cluster_id: 需要下架的集群id
        """
        cluster = Cluster.objects.get(id=cluster_id)
        proxy_info = ProxyInstance.objects.filter(cluster=cluster).all()
        slave_info = StorageInstance.objects.filter(
            cluster=cluster, instance_inner_role=InstanceInnerRole.SLAVE.value
        ).all()

        # 查询proxy所有域名入口,一套HA集群所有proxy节点都是同样的dns映射，所有拿其中一个proxy的dns映射关系信息即可
        proxy_dns_list = proxy_info[0].bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()

        # 查询slave的所有域名入口，由于每个slave节点的dns映射关系有可能是不一样，所以要一一查询对应起来
        slave_dns_list = []
        for slave in slave_info:
            slave_dns_infos = slave.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
            slave_dns_list.append(
                {
                    "slave_ip": slave.machine.ip,
                    "slave_port": slave.port,
                    "dns_list": [i.entry for i in slave_dns_infos],
                }
            )

        return {
            "id": cluster_id,
            "name": cluster.name,
            "bk_cloud_id": cluster.bk_cloud_id,
            "proxy_port": proxy_info[0].port,
            "proxy_ip_list": [p.machine.ip for p in proxy_info],
            "proxy_dns_list": [i.entry for i in proxy_dns_list],
            "slave_dns_list": slave_dns_list,
        }

    def enable_mysql_ha_flow(self):
        """
        定义mysql主从版禁用流程，支持多套集群同时禁用模式
        """
        mysql_ha_destroy_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群下架时循环加入集群下架子流程
        for cluster_id in self.data["cluster_ids"]:

            # 获取集群的实例信息
            cluster = self.__get_ha_cluster_info(cluster_id=cluster_id)

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            # 阶段1 重新恢复集群注册的域名
            acts_list = []
            for proxy_dns_name in cluster["proxy_dns_list"]:
                acts_list.append(
                    {
                        "act_name": _("添加主集群域名"),
                        "act_component_code": MySQLDnsManageComponent.code,
                        "kwargs": asdict(
                            CreateDnsKwargs(
                                bk_cloud_id=cluster["bk_cloud_id"],
                                add_domain_name=proxy_dns_name,
                                dns_op_exec_port=cluster["proxy_port"],
                                exec_ip=cluster["proxy_ip_list"],
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            acts_list = []
            for slave_dns_info in cluster["slave_dns_list"]:
                for dns_name in slave_dns_info["dns_list"]:
                    acts_list.append(
                        {
                            "act_name": _("添加从集群域名"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=cluster["bk_cloud_id"],
                                    add_domain_name=dns_name,
                                    dns_op_exec_port=slave_dns_info["slave_port"],
                                    exec_ip=slave_dns_info["slave_ip"],
                                )
                            ),
                        }
                    )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 阶段2 修改集群状态
            sub_pipeline.add_act(
                act_name=_("集群变更ONLINE状态"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_cluster_online.__name__,
                        cluster=cluster,
                    ),
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("启动MySQL高可用集群[{}]").format(cluster["name"]))
            )

        mysql_ha_destroy_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_ha_destroy_pipeline.run_pipeline()
