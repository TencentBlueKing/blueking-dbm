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
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.delete_cc_service_instance import DelCCServiceInstComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DBMetaOPKwargs,
    DelServiceInstKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLSingleDestroyFlow(object):
    """
    构建mysql单节点版下架流程抽象类
    支持不同云区域的db集群合并下架
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_single_cluster_info(cluster_id: int, bk_biz_id: int) -> dict:
        """
        根据cluster_id 获取到单节点集群实例信息，单节点只有一个实例
        @param cluster_id: 需要下架的集群id
        @param bk_biz_id: 需要下架集群的对应的业务id
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=cluster_id, bk_biz_id=bk_biz_id, message=_("集群不存在"))

        backend_info = StorageInstance.objects.get(cluster=cluster)
        return {
            "id": cluster_id,
            "name": cluster.name,
            "backend_port": backend_info.port,
            "backend_ip": backend_info.machine.ip,
            "bk_cloud_id": cluster.bk_cloud_id,
        }

    def destroy_mysql_single_flow(self):
        """
        定义mysql单节点版下架流程，支持多集群下架模式
        """
        mysql_single_destroy_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群下架时循环加入集群下架子流程
        for cluster_id in self.data["cluster_ids"]:

            # 获取集群的实例信息
            cluster = self.__get_single_cluster_info(cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            sub_pipeline.add_act(
                act_name=_("删除注册CC系统的服务实例"),
                act_component_code=DelCCServiceInstComponent.code,
                kwargs=asdict(
                    DelServiceInstKwargs(
                        cluster_id=cluster["id"],
                        del_instance_list=[{"ip": cluster["backend_ip"], "port": cluster["backend_port"]}],
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster["bk_cloud_id"],
                        exec_ip=cluster["backend_ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("清理实例级别周边配置"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=cluster["backend_ip"],
                        cluster_type=ClusterType.TenDBSingle,
                        bk_cloud_id=cluster["bk_cloud_id"],
                        cluster=cluster,
                        get_mysql_payload_func=MysqlActPayload.get_clear_surrounding_config_payload.__name__,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("卸载mysql实例"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=cluster["backend_ip"],
                        cluster_type=ClusterType.TenDBSingle,
                        bk_cloud_id=cluster["bk_cloud_id"],
                        cluster=cluster,
                        get_mysql_payload_func=MysqlActPayload.get_uninstall_mysql_payload.__name__,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("清理db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_single_destroy.__name__,
                        cluster=cluster,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("清理机器配置"),
                act_component_code=MySQLClearMachineComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=cluster["backend_ip"],
                        cluster_type=ClusterType.TenDBSingle,
                        bk_cloud_id=cluster["bk_cloud_id"],
                        get_mysql_payload_func=MysqlActPayload.get_clear_machine_crontab.__name__,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("下架MySQL单节点集群[{}]").format(cluster["name"]))
            )

        mysql_single_destroy_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_single_destroy_pipeline.run_pipeline()
