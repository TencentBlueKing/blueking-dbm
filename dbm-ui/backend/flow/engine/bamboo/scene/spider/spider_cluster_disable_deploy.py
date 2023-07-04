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
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, ClusterType, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ClusterEntry, Machine, ProxyInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DBMetaOPKwargs,
    DeleteClusterDnsKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta


class SpiderClusterDisableFlow(object):
    def __init__(self, root_id: str, data: Optional[dict]):
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_tendb_cluster_info(cluster_id: int, is_only_delete_slave_domain: bool):
        """
        获取集群信息，主要获取代理层ip信息spider_ip_list spider_port
        """
        cluster = Cluster.objects.get(id=cluster_id)
        if is_only_delete_slave_domain:
            entry = ClusterEntry.objects.filter(
                cluster=cluster, cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
            ).all()
            instance_list = entry[0].proxyinstance_set.all()
            spider_port = instance_list[0].port
            spider_ip_list = [instance.machine.ip for instance in instance_list]
        else:
            # 从域名端口是否和主域名是一致的？
            spider_port = cluster.proxyinstance_set.first().port
            spider_ip_list = [instance.machine.ip for instance in cluster.proxyinstance_set.all()]

        cluster_info = {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "spider_port": spider_port,
            "spider_ip_list": spider_ip_list,
        }
        return cluster_info

    def disable_spider_cluster_flow(self):
        """
        定义spider集群禁用流程
        """
        pipleline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群禁用时，循环加入禁用子流程
        for cluster_id in self.data["cluster_ids"]:
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("cluster_ids")
            cluster_info = self.__get_tendb_cluster_info(cluster_id, self.data["is_only_delete_slave_domain"])
            sub_flow_context.update(cluster_info)
            print(sub_flow_context)
            # 开始流程编排
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
            sub_pipeline.add_act(
                act_name=_("删除集群域名"),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    DeleteClusterDnsKwargs(
                        bk_cloud_id=cluster_info["bk_cloud_id"],
                        delete_cluster_id=cluster_id,
                        is_only_delete_slave_domain=self.data["is_only_delete_slave_domain"],
                    ),
                ),
            )

            # 传入需要下发的ip列表
            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster_info["bk_cloud_id"],
                        exec_ip=cluster_info["spider_ip_list"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            # 以目标ip为单位，分别下发命令，执行重启spider命令
            acts_list = []
            for spider_ip in cluster_info["spider_ip_list"]:
                acts_list.append(
                    {
                        "act_name": _("重启spider实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                exec_ip=spider_ip,
                                cluster_type=ClusterType.TenDBCluster,
                                bk_cloud_id=cluster_info["bk_cloud_id"],
                                cluster=cluster_info,
                                get_mysql_payload_func=MysqlActPayload.get_restart_spider_payload.__name__,
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)
            if not self.data["is_only_delete_slave_domain"]:
                sub_pipeline.add_act(
                    act_name=_("集群变更OFFLINE状态"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_cluster_offline.__name__,
                            cluster=cluster_info,
                        )
                    ),
                )
            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("禁用MySQL高可用集群[{}]").format(cluster_info["name"]))
            )

        pipleline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipleline.run_pipeline()
