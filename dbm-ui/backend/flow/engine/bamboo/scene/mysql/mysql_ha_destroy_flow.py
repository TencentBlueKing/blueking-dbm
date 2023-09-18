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
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
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


class MySQLHADestroyFlow(object):
    """
    构建mysql主从版下架流程抽象类
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
        backend_info = StorageInstance.objects.filter(cluster=cluster).all()
        proxy_info = ProxyInstance.objects.filter(cluster=cluster).all()
        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "backend_port": backend_info[0].port,
            "proxy_port": proxy_info[0].port,
            "backend_ip_list": [b.machine.ip for b in backend_info],
            "proxy_ip_list": [p.machine.ip for p in proxy_info],
        }

    def destroy_mysql_ha_flow(self):
        """
        定义mysql主从版下架流程，支持多集群下架模式
        """
        mysql_ha_destroy_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群下架时循环加入集群下架子流程
        for cluster_id in self.data["cluster_ids"]:

            # 获取集群的实例信息
            cluster = self.__get_ha_cluster_info(cluster_id=cluster_id)

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=int(cluster["bk_cloud_id"]),
                cluster=cluster,
            )

            # 先回收集群所有服务实例内容
            del_instance_list = []
            for ip in cluster["backend_ip_list"]:
                del_instance_list.append({"ip": ip, "port": cluster["backend_port"]})
            for ip in cluster["proxy_ip_list"]:
                del_instance_list.append({"ip": ip, "port": cluster["proxy_port"]})
            sub_pipeline.add_act(
                act_name=_("删除注册CC系统的服务实例"),
                act_component_code=DelCCServiceInstComponent.code,
                kwargs=asdict(
                    DelServiceInstKwargs(
                        cluster_id=cluster["id"],
                        del_instance_list=del_instance_list,
                    )
                ),
            )

            # 阶段1 下发db-actuator介质包
            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster["bk_cloud_id"],
                        exec_ip=cluster["backend_ip_list"] + cluster["proxy_ip_list"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            # 阶段2 清理周边配置，包括事件监控
            # acts_list = []
            # for ip in cluster["backend_ip_list"] + cluster["proxy_ip_list"]:
            #     exec_act_kwargs.exec_ip = ip
            #     exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_surrounding_config_payload.__name__
            #     acts_list.append(
            #         {
            #             "act_name": _("清理实例周边配置"),
            #             "act_component_code": ExecuteDBActuatorScriptComponent.code,
            #             "kwargs": asdict(exec_act_kwargs),
            #         }
            #     )
            # sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 阶段3 卸载相关db组件
            acts_list = []
            for proxy_ip in cluster["proxy_ip_list"]:
                exec_act_kwargs.exec_ip = proxy_ip
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_proxy_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("卸载proxy实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            acts_list = []
            for mysql_ip in cluster["backend_ip_list"]:
                exec_act_kwargs.exec_ip = mysql_ip
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_mysql_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("卸载mysql实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 阶段4 清空相关集群云信息；相关的bkcc注册信息
            sub_pipeline.add_act(
                act_name=_("清理db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_ha_destroy.__name__,
                        cluster=cluster,
                    )
                ),
            )

            # 阶段5 判断是否清理机器级别配置
            exec_act_kwargs.exec_ip = cluster["backend_ip_list"] + cluster["proxy_ip_list"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_machine_crontab.__name__
            sub_pipeline.add_act(
                act_name=_("清理机器级别配置"),
                act_component_code=MySQLClearMachineComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("下架MySQL高可用集群[{}]").format(cluster["name"]))
            )

        mysql_ha_destroy_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_ha_destroy_pipeline.run_pipeline()
