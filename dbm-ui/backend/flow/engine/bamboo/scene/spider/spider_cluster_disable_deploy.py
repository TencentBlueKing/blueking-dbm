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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Cluster, Machine, ProxyInstance
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
    def __get_spider_cluster_info(cluster_id: int) -> dict:
        """
        根据cluster_id获取集群信息
        """
        cluster = Cluster.objects.get(id=cluster_id)
        # 需要咨询一下spider相关的表与字段
        # spider_info = SpiderInstance.objects.filter(cluster=cluster).all()
        # return {
        #     "id": cluster_id,
        #     "bk_cloud_id": cluster.bk_cloud_id,
        #     "name": cluster.name,
        #     "spider_port": spider_info[0].port,
        #     "spider_ip_list": [s.machine.ip for s in spider_info]
        # }
        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "spider_port": cluster.proxyinstance_set.first().port,
            "spider_ip_list": [ele.machine.ip for ele in cluster.proxyinstance_set.all()],
        }

    def disable_spider_cluster_flow(self):
        """
        定义spider集群禁用流程
        """
        spider_cluster_disable_pipleline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群禁用时，循环加入禁用子流程
        for cluster_id in self.data["cluster_ids"]:
            # 获取集群实例信息
            cluster = self.__get_spider_cluster_info(cluster_id=cluster_id)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_act(
                act_name=_("删除集群域名"),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    DeleteClusterDnsKwargs(
                        bk_cloud_id=cluster["bk_cloud_id"],
                        delete_cluster_id=cluster_id,
                    ),
                ),
            )

            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster["bk_cloud_id"],
                        exec_ip=cluster["spider_ip_list"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            acts_list = []
            for spider_ip in cluster["spider_ip_list"]:
                acts_list.append(
                    {
                        "act_name": _("重启spider实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                exec_ip=spider_ip,
                                cluster_type=ClusterType.TenDBCluster,
                                bk_cloud_id=cluster["bk_cloud_id"],
                                cluster=cluster,
                                get_mysql_payload_func=MysqlActPayload.get_restart_spider_payload.__name__,
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            sub_pipeline.add_act(
                act_name=_("集群变更OFFLINE状态"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_cluster_offline.__name__,
                        cluster=cluster,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("禁用MySQL高可用集群[{}]").format(cluster["name"]))
            )

        spider_cluster_disable_pipleline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        spider_cluster_disable_pipleline.run_pipeline()
