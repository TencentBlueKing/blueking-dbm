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
from typing import Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterEntryType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance
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
    def __get_spider_cluster_info(cluster_id: int) -> dict:
        """
        根据cluster_id获取集群信息
        """
        cluster = Cluster.objects.get(id=cluster_id)
        # spider_info = SpiderInstance.objects.filter(cluster=cluster).all()
        #
        # # spider集群的从域名有自己的spider节点，区别于mysql ha集群，咨询下spider集群相关表是哪些
        # slave_info = StorageInstance.objects.filter(
        #     cluster=cluster, instance_inner_role=InstanceInnerRole.SLAVE.value
        # ).all()
        #
        # spider_dns_list = spider_info[0].bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
        #
        # slave_dns_list = []
        # for slave in slave_info:
        #     slave_dns_infos = slave.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
        #     slave_dns_list.append(
        #         {
        #             "slave_ip": slave.machine.ip,
        #             "slave_port": slave.port,
        #             "dns_list": [i.entry for i in slave_dns_infos],
        #         }
        #     )

        # return {
        #     "id": cluster_id,
        #     "bk_cloud_id": cluster.bk_cloud_id,
        #     "name": cluster.name,
        #     "spider_port": spider_info[0].port,
        #     "spider_ip_list": [s.machine.ip for s in spider_info],
        #     "spider_dns_list": [i.entry for i in spider_dns_list],
        #     "slave_dns_list": slave_dns_list,
        # }
        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "spider_port": 25000,
            "spider_ip_list": ["127.0.0.1"],
            "spider_dns_list": ["xxxx.xxxx.xxxx"],
            "slave_dns_list": [{"slave_ip": "127.0.0.1", "slave_port": 20000, "dns_list": ["xxxx.xxxx.xxxx"]}],
        }

    def enable_spider_cluster_flow(self):
        """
        定义spider集群启用流程
        """
        spider_cluster_enable_pipleline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群禁用时，循环加入禁用子流程
        for cluster_id in self.data["cluster_ids"]:
            # 获取集群实例信息
            cluster = self.__get_spider_cluster_info(cluster_id=cluster_id)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            acts_list = []
            for spider_dns_name in cluster["spider_dns_list"]:
                acts_list.append(
                    {
                        "act_name": _("添加主集群域名"),
                        "act_component_code": MySQLDnsManageComponent.code,
                        "kwargs": asdict(
                            CreateDnsKwargs(
                                bk_cloud_id=cluster["bk_cloud_id"],
                                add_domain_name=spider_dns_name,
                                dns_op_exec_port=cluster["spider_port"],
                                exec_ip=cluster["spider_ip_list"],
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

            sub_pipeline.add_act(
                act_name=_("集群变更ONLINE状态"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_cluster_online.__name__,
                        cluster=cluster,
                    )
                ),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("启用spider集群[{}]").format(cluster["name"])))

        spider_cluster_enable_pipleline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        spider_cluster_enable_pipleline.run_pipeline()
