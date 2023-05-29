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
from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import build_surrounding_apps_sub_flow
from backend.flow.engine.bamboo.scene.mysql.mysql_master_slave_switch import MySQLMasterSlaveSwitchFlow
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterSwitchContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLMasterFailOverFlow(object):
    """
    构建mysql主从版集群主机器故障切换的流程，产品形态是整机切换，保证同一台机器的所有实例要不master角色，要不slave角色,切换过程不能保证数据不会丢失
    目前流程如下：
    1：下发db-actuator介质到slave机器
    2：在slave节点执行故障场景的集群切换逻辑（db-actuator）
    3：如果存在其他的slave实例，则剩余的slave实例同步新的master数据（db-actuator）
    4：回收新master之前的从域名映射信息
    5：添加旧master的从域名映射信息
    6：修改db-meta元数据
    7: 重建备份程序和数据校验
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def master_fail_over_flow(self):
        """
        定义mysql集群主故障切换的流程
        """
        mysql_switch_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 根据互切任务拼接子流程
        for info in self.data["infos"]:

            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=info["slave_ip"]["bk_cloud_id"],
                        exec_ip=info["slave_ip"]["ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            # 根据需要切换的集群，依次添加
            cluster_switch_sub_list = []

            for cluster_id in info["cluster_ids"]:

                # 拼接子流程需要全局参数
                sub_sub_flow_context = copy.deepcopy(self.data)
                sub_sub_flow_context.pop("infos")

                # 把公共参数拼接到子流程的全局只读上下文
                sub_sub_flow_context["is_safe"] = info["is_safe"]
                sub_sub_flow_context["is_dead_master"] = True
                sub_sub_flow_context["grant_repl"] = True
                sub_sub_flow_context["locked_switch"] = False
                sub_sub_flow_context["change_master_force"] = True

                # 获取对应的集群信息
                cluster = MySQLMasterSlaveSwitchFlow.get_cluster_info(
                    cluster_id=cluster_id, new_master_ip=info["slave_ip"]["ip"], old_master_ip=info["master_ip"]["ip"]
                )

                # 拼接执行原子任务的活动节点需要的通用的私有参数
                cluster_sw_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=cluster["bk_cloud_id"])

                # 针对集群维度声明子流程
                cluster_switch_sub_pipeline = SubBuilder(
                    root_id=self.root_id, data=copy.deepcopy(sub_sub_flow_context)
                )

                # 阶段2 执行故障切换的原子任务
                cluster_sw_kwargs.exec_ip = info["slave_ip"]["ip"]
                cluster_sw_kwargs.get_mysql_payload_func = (
                    MysqlActPayload.get_set_backend_toward_slave_payload.__name__
                )
                cluster_switch_sub_pipeline.add_act(
                    act_name=_("执行集群主故障转移"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(cluster_sw_kwargs),
                    write_payload_var=ClusterSwitchContext.get_new_master_bin_pos_var_name(),
                )

                # 阶段3 并发change master 的 原子任务，如果集群多余的slave节点，剩余所有的slave节点同步new master 的数据

                if cluster["other_slave_info"]:
                    acts_list = []
                    for exec_ip in cluster["other_slave_info"]:
                        cluster_sw_kwargs.exec_ip = exec_ip
                        cluster_sw_kwargs.get_mysql_payload_func = MysqlActPayload.get_change_master_payload.__name__
                        acts_list.append(
                            {
                                "act_name": _("salve节点同步新master数据"),
                                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                                "kwargs": asdict(cluster_sw_kwargs),
                            }
                        )
                    cluster_switch_sub_pipeline.add_parallel_acts(acts_list=acts_list)

                # 阶段4 更改旧master 和 新master 的域名映射关系，并发执行
                cluster_switch_sub_pipeline.add_parallel_acts(
                    acts_list=MySQLMasterSlaveSwitchFlow.get_handle_domain_act_list(
                        master_ip=info["master_ip"]["ip"],
                        slave_ip=info["slave_ip"]["ip"],
                        mysql_port=int(cluster["mysql_port"]),
                        slave_dns_list=cluster["slave_dns_list"],
                        bk_cloud_id=cluster["bk_cloud_id"],
                    )
                )

                cluster_switch_sub_list.append(
                    cluster_switch_sub_pipeline.build_sub_process(sub_name=_("{}集群执行主故障切换").format(cluster["name"]))
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_switch_sub_list)

            # 阶段5 按照机器维度变更db-meta数据，cluster变量传入info信息
            sub_pipeline.add_act(
                act_name=_("变更db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_ha_switch.__name__,
                        cluster=info,
                    )
                ),
            )

            # 阶段6 切换后重建备份程序和数据校验程序
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=info["slave_ip"]["bk_cloud_id"],
                    master_ip_list=[info["master_ip"]["ip"]],
                    slave_ip_list=[info["slave_ip"]["ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(sub_flow_context),
                    is_init=False,
                    cluster_type=ClusterType.TenDBHA.value,
                )
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("主故障切换流程[整机切换]")))

        mysql_switch_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_switch_pipeline.run_pipeline(init_trans_data_class=ClusterSwitchContext())
