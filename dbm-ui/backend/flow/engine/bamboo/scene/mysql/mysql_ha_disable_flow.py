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
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, ProxyInstance
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

logger = logging.getLogger("flow")


class MySQLHADisableFlow(object):
    """
    构建mysql主从版禁用流程抽象类，集群禁用功能是将集群理论上不让外部业务机器还能访问到，保证数据是静止状态
    这里不考虑直连IP访问数据等这种不规范的访问情况
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
        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "proxy_port": proxy_info[0].port,
            "proxy_ip_list": [p.machine.ip for p in proxy_info],
        }

    def disable_mysql_ha_flow(self):
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

            # 阶段1 回收集群相关域名
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

            # 阶段2 重启proxy实例，来清空已存在的长连接
            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster["bk_cloud_id"],
                        exec_ip=cluster["proxy_ip_list"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            acts_list = []
            for proxy_ip in cluster["proxy_ip_list"]:
                acts_list.append(
                    {
                        "act_name": _("重启proxy实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                exec_ip=proxy_ip,
                                cluster_type=ClusterType.TenDBSingle,
                                bk_cloud_id=cluster["bk_cloud_id"],
                                cluster=cluster,
                                get_mysql_payload_func=MysqlActPayload.get_restart_proxy_payload.__name__,
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 阶段3 更改集群信息状态
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

        mysql_ha_destroy_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_ha_destroy_pipeline.run_pipeline()
