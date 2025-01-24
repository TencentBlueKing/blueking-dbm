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
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.consts import MIN_TENDB_PROXY_COUNT
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.plugins.components.collections.common.delete_cc_service_instance import DelCCServiceInstComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.check_client_connections import CheckClientConnComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.drop_proxy_client_in_backend import (
    DropProxyUsersInBackendComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckClientConnKwargs,
    DBMetaOPKwargs,
    DelServiceInstKwargs,
    DownloadMediaKwargs,
    DropProxyUsersInBackendKwargs,
    ExecActuatorKwargs,
    RecycleDnsRecordKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLProxyClusterReduceFlow(object):
    """
    构建mysql集群下架proxy实例申请流程抽象类
    替换proxy 是属于实例级别下架
    兼容跨云区域的场景支持
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def reduce_mysql_proxy_flow(self):
        """
        定义proxy下架流程, 可并行操作
        1：下发dbactor介质包（整机级别操作）
        2：安全模式下：检查proxy实例是否在连接，是连接则报异常。
        3：回收proxy实例对应域名
        4：回收proxy实例在backend的权限，脱离集群
        5：人工确认
        6：清理cc服务实例，避免后续卸载产生误告 （实例级别操作）
        7：卸载proxy周边配置 （实例级别操作）
        8：卸载proxy实例 （实例级别操作）
        9：删除元数据 （实例级别操作）
        20：清理机器级别数据（整机级别操作）
        """

        mysql_proxy_cluster_reduce_pipeline = Builder(root_id=self.root_id, data=self.data)
        main_sub_pipelines = []

        # 多集群操作时循环加入集群proxy下架子流程
        for info in self.data["infos"]:

            # 拼接子流程需要全局参数
            flow_context = copy.deepcopy(self.data)
            flow_context.pop("infos")

            # 针对机器维度声明子流程
            machine_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(flow_context))

            # 1：下发dbactor介质包（整机级别操作）
            machine_sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=info["origin_proxy_ip"]["bk_cloud_id"],
                        exec_ip=info["origin_proxy_ip"]["ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    ),
                ),
            )

            sub_pipelines = []
            for cluster_id in info["cluster_ids"]:
                cluster = Cluster.objects.get(id=cluster_id)
                # 这里要判断集群的当前proxy数量，目前低于两台的proxy实例，直接异常处理
                if (
                    cluster.proxyinstance_set.exclude(machine__ip=info["origin_proxy_ip"]["ip"]).count()
                    < MIN_TENDB_PROXY_COUNT
                ):
                    raise NormalTenDBFlowException(
                        message=f"[{cluster.immute_domain}] The number of clusters is less than {MIN_TENDB_PROXY_COUNT}"
                        f" after reducing, check"
                    )

                origin_proxy = cluster.proxyinstance_set.get(machine__ip=info["origin_proxy_ip"]["ip"])

                # 针对集群维度声明子流程
                cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(flow_context))

                # 安全模式下：检查proxy实例是否在连接，是连接则报异常
                if self.data["is_safe"]:
                    cluster_sub_pipeline.add_act(
                        act_name=_("检测Proxy端连接情况"),
                        act_component_code=CheckClientConnComponent.code,
                        kwargs=asdict(
                            CheckClientConnKwargs(
                                bk_cloud_id=cluster.bk_cloud_id,
                                check_instances=[
                                    f"{origin_proxy.machine.ip}{IP_PORT_DIVIDER}{origin_proxy.admin_port}"
                                ],
                                is_proxy=True,
                            )
                        ),
                    )

                cluster_sub_pipeline.add_act(
                    act_name=_("回收proxy域名映射"),
                    act_component_code=MySQLDnsManageComponent.code,
                    kwargs=asdict(
                        RecycleDnsRecordKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            dns_op_exec_port=origin_proxy.port,
                            exec_ip=origin_proxy.machine.ip,
                        ),
                    ),
                )

                cluster_sub_pipeline.add_act(
                    act_name=_("回收旧proxy在backend权限"),
                    act_component_code=DropProxyUsersInBackendComponent.code,
                    kwargs=asdict(
                        DropProxyUsersInBackendKwargs(
                            cluster_id=cluster_id,
                            origin_proxy_host=origin_proxy.machine.ip,
                        ),
                    ),
                )

                cluster_sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

                # 2：清理cc服务实例，避免后续卸载产生误告 （实例级别操作）
                cluster_sub_pipeline.add_act(
                    act_name=_("删除注册CC系统的服务实例"),
                    act_component_code=DelCCServiceInstComponent.code,
                    kwargs=asdict(
                        DelServiceInstKwargs(
                            cluster_id=cluster_id,
                            del_instance_list=[{"ip": origin_proxy.machine.ip, "port": origin_proxy.port}],
                        )
                    ),
                )

                # 3：卸载proxy周边配置 （实例级别操作）
                cluster_sub_pipeline.add_act(
                    act_name=_("清理proxy实例级别周边配置"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            exec_ip=origin_proxy.machine.ip,
                            get_mysql_payload_func=MysqlActPayload.get_clear_surrounding_config_payload.__name__,
                            cluster={"proxy_port": origin_proxy.port},
                        )
                    ),
                )

                # 4：卸载proxy实例 （实例级别操作）
                cluster_sub_pipeline.add_act(
                    act_name=_("卸载proxy实例"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            exec_ip=origin_proxy.machine.ip,
                            get_mysql_payload_func=MysqlActPayload.get_uninstall_proxy_payload.__name__,
                            cluster={"proxy_port": origin_proxy.port},
                        )
                    ),
                )
                # 5：删除元数据 （实例级别操作）
                cluster_sub_pipeline.add_act(
                    act_name=_("回收旧proxy实例的元数据信息"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_proxy_reduce.__name__,
                            cluster={"cluster_ids": [cluster_id], "origin_proxy_ip": info["origin_proxy_ip"]},
                        )
                    ),
                )

                sub_pipelines.append(
                    cluster_sub_pipeline.build_sub_process(
                        sub_name=_("下架proxy子流程[{}:{}]".format(origin_proxy.machine.ip, origin_proxy.port))
                    )
                )

            machine_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

            # 6：清理机器级别数据（整机级别操作）
            machine_sub_pipeline.add_act(
                act_name=_("清理机器配置"),
                act_component_code=MySQLClearMachineComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=info["origin_proxy_ip"]["bk_cloud_id"],
                        exec_ip=info["origin_proxy_ip"]["ip"],
                        get_mysql_payload_func=MysqlActPayload.get_clear_machine_crontab.__name__,
                    )
                ),
            )

            main_sub_pipelines.append(
                machine_sub_pipeline.build_sub_process(
                    sub_name=_("在机器[{}]下架proxy".format(info["origin_proxy_ip"]["ip"]))
                )
            )

        mysql_proxy_cluster_reduce_pipeline.add_parallel_sub_pipeline(sub_flow_list=main_sub_pipelines)
        mysql_proxy_cluster_reduce_pipeline.run_pipeline()
