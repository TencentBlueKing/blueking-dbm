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
from typing import Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceInnerRole
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import CreateDnsKwargs, DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta


class SpiderClusterEnableFlow(object):
    def __init__(self, root_id: str, data: Optional[dict]):
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_tendb_cluster_info(cluster_id: int, is_only_add_slave_domain: bool):
        """
        获取集群信息，主要获取代理层ip信息spider_ip_list spider_port
        """
        cluster = Cluster.objects.get(id=cluster_id)

        master_domain_list = []
        spider_master_port = 25000
        spider_master_ip_list = []
        if not is_only_add_slave_domain:
            entry_list = ClusterEntry.objects.filter(cluster=cluster, role=ClusterEntryRole.MASTER_ENTRY.value).all()
            master_domain_list = master_domain_list + [entry.entry for entry in entry_list]
            instance_list = entry_list[0].proxyinstance_set.all()
            spider_master_port = instance_list[0].port
            spider_master_ip_list = spider_master_ip_list + [instance.machine.ip for instance in instance_list]

        entry_list = ClusterEntry.objects.filter(cluster=cluster, role=ClusterEntryRole.SLAVE_ENTRY.value).all()
        slave_domain_list = [entry.entry for entry in entry_list]
        instance_list = entry_list[0].proxyinstance_set.all()
        spider_slave_port = instance_list[0].port
        spider_slave_ip_list = [instance.machine.ip for instance in instance_list]

        cluster_info = {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "master_domain_list": master_domain_list,
            "spider_master_port": spider_master_port,
            "spider_master_ip_list": spider_master_ip_list,
            "slave_domain_list": slave_domain_list,
            "spider_slave_port": spider_slave_port,
            "spider_slave_ip_list": spider_slave_ip_list,
        }
        return cluster_info

    def enable_spider_cluster_flow(self):
        """
        定义spider集群启用流程
        """
        spider_cluster_enable_pipleline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群禁用时，循环加入禁用子流程
        for cluster_id in self.data["cluster_ids"]:
            # 获取集群实例信息
            cluster = Cluster.objects.get(id=cluster_id)
            instance_set = cluster.proxyinstance_set.all()
            # 这里问下，一套集群对应多个域名？
            cluster_info = self.__get_tendb_cluster_info(cluster_id, self.data["is_only_add_slave_domain"])
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("cluster_ids")
            sub_flow_context.update(cluster_info)
            print(sub_flow_context)

            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            if not self.data["is_only_add_slave_domain"]:
                acts_list = []
                for master_domain in cluster_info["master_domain_list"]:
                    acts_list.append(
                        {
                            "act_name": _("添加集群域名"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=cluster_info["bk_cloud_id"],
                                    add_domain_name=master_domain,
                                    dns_op_exec_port=cluster_info["spider_master_port"],
                                    exec_ip=cluster_info["spider_master_ip_list"],
                                )
                            ),
                        }
                    )
                sub_pipeline.add_parallel_acts(acts_list=acts_list)

            acts_list = []
            for slave_domain in cluster_info["slave_domain_list"]:
                acts_list.append(
                    {
                        "act_name": _("添加从集群域名"),
                        "act_component_code": MySQLDnsManageComponent.code,
                        "kwargs": asdict(
                            CreateDnsKwargs(
                                bk_cloud_id=cluster_info["bk_cloud_id"],
                                add_domain_name=slave_domain,
                                dns_op_exec_port=cluster_info["spider_slave_port"],
                                exec_ip=cluster_info["spider_slave_ip_list"],
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            sub_pipeline.add_act(
                act_name=_("集群变更ONLINE状态"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_cluster_online.__name__,
                        cluster=cluster_info,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("启用spider集群[{}]").format(cluster_info["name"]))
            )

        spider_cluster_enable_pipleline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        spider_cluster_enable_pipleline.run_pipeline()
