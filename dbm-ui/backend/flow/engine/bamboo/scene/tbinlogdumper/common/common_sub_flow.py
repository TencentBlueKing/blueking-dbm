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
import uuid
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, Machine
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.atom_jobs.set_dns_sub_job import set_dns_atom_job
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import build_repl_by_manual_input_sub_flow
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import NormalTBinlogDumperFlowException
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.util import (
    get_tbinlogdumper_charset,
    get_tbinlogdumper_server_id,
)
from backend.flow.plugins.components.collections.common.L5_agent_install import L5AgentInstallComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.tbinlogdumper.dumper_data import TBinlogDumperFullSyncDataComponent
from backend.flow.plugins.components.collections.tbinlogdumper.stop_slave import TBinlogDumperStopSlaveComponent
from backend.flow.plugins.components.collections.tbinlogdumper.trans_backup_file import TBinlogDumperTransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs, P2PFileKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.tbinlogdumper.context_dataclass import StopSlaveKwargs, TBinlogDumperFullSyncDataKwargs
from backend.flow.utils.tbinlogdumper.tbinlogdumper_act_payload import TBinlogDumperActPayload

"""
定义一些TBinlogDumper流程上可能会用到的子流程，以便于减少代码的重复率
"""


def add_tbinlogdumper_sub_flow(
    cluster: Cluster,
    root_id: str,
    uid: str,
    is_install_l5_agent: bool,
    add_conf_list: list,
    created_by: str = "",
):
    """
    定义添加TBinlogdumper实例的公共子流程
    @param cluster: 待操作的集群
    @param uid: 单据uid
    @param root_id: flow流程的root_id
    @param is_install_l5_agent: 是否安装l5_agent
    @param add_conf_list: 本次上架的配置列表，每个的元素的格式为dict
    @param created_by: 单据发起者
    """
    # 查找集群的当前master实例, tendb-ha架构无论什么时候只有一个master角色
    master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)

    # 获取TBinlogDumper的字符集配置，以mysql数据源的为准
    charset = get_tbinlogdumper_charset(ip=master.machine.ip, port=master.port, bk_cloud_id=cluster.bk_cloud_id)

    # 计算每个tbinlogdumper的serverid
    for conf in add_conf_list:
        conf["server_id"] = get_tbinlogdumper_server_id(master=master, tbinlogdumper_port=conf["port"])

    # 拼接子流程的只读全局参数
    parent_global_data = {
        "uid": uid,
        "add_conf_list": add_conf_list,
        "bk_biz_id": cluster.bk_biz_id,
        "created_by": created_by,
        "charset": charset,
    }
    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 初始化机器,为了安装tbinlogdumper
    sub_pipeline.add_sub_pipeline(
        sub_flow=init_machine_sub_flow(
            root_id=root_id,
            uid=uid,
            init_machine=master.machine.ip,
            is_install_l5_agent=is_install_l5_agent,
        )
    )

    # 阶段1 并行分发安装文件
    sub_pipeline.add_act(
        act_name=_("下发TBinlogDumper介质包"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=master.machine.ip,
                file_list=GetFileList(db_type=DBType.MySQL).get_tbinlogdumper_package(),
            )
        ),
    )

    # 阶段2 并发安装TBinlogDumper实例
    sub_pipeline.add_act(
        act_name=_("安装TBinlogDumper实例"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                cluster_type=cluster.cluster_type,
                exec_ip=master.machine.ip,
                get_mysql_payload_func=TBinlogDumperActPayload.install_tbinlogdumper_payload.__name__,
            )
        ),
    )
    # 返回子流程
    return sub_pipeline.build_sub_process(sub_name=_("安装TBinlogDumper实例flow"))


def reduce_tbinlogdumper_sub_flow(
    bk_biz_id: int,
    bk_cloud_id: int,
    root_id: str,
    uid: str,
    reduce_ids: list,
    created_by: str = "",
):
    """
    定义针对集群维度卸载TBinlogdumper实例的公共子流程
    @param bk_biz_id: 业务id
    @param bk_cloud_id: 云区域id
    @param uid: 单据uid
    @param root_id: flow流程的root_id
    @param reduce_ids: 本次卸载的实例id列表
    @param created_by: 单据发起者
    """

    parent_global_data = {
        "uid": uid,
        "bk_biz_id": bk_biz_id,
        "created_by": created_by,
    }
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 阶段1 下发db-actuator介质包
    tbinlogdumpers = ExtraProcessInstance.objects.filter(id__in=reduce_ids, bk_cloud_id=bk_cloud_id)
    if len(tbinlogdumpers) == 0:
        # 如果根据下架的id list 获取的元信息为空，则作为异常处理
        raise NormalTBinlogDumperFlowException(message=_("传入的TBinlogDumper进程信息已不存在[{}]，请联系系统管理员".format(reduce_ids)))

    # 聚合并行下发dbactor, 避免出现下发异常
    sub_pipeline.add_act(
        act_name=_("下发db-actuator介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=list(set([t.ip for t in tbinlogdumpers])),
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )

    # 阶段2 按照实例并发卸载
    acts_list = []
    for inst in tbinlogdumpers:
        acts_list.append(
            {
                "act_name": _("卸载TBinlogDumper实例[{}:{}]".format(inst.ip, inst.listen_port)),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=inst.bk_cloud_id,
                        exec_ip=inst.ip,
                        get_mysql_payload_func=TBinlogDumperActPayload.uninstall_tbinlogdumper_payload.__name__,
                        cluster={"listen_ports": [inst.listen_port]},
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 返回子流程
    return sub_pipeline.build_sub_process(sub_name=_("云区域[{}]卸载TBinlogDumper实例flow".format(bk_cloud_id)))


def switch_sub_flow(
    cluster: Cluster,
    root_id: str,
    uid: str,
    is_safe: bool,
    switch_instances: list,
    created_by: str = "",
):
    """
    定义TBinlogDumper切换的子流程
    @param cluster: 操作的云区域id
    @param root_id: flow流程的root_id
    @param uid: 单据uid
    @param is_safe: 是否做安全切换
    @param switch_instances: 待切换的TBinlogDumper实例对列表
    @param created_by: 单据发起者
    """

    # 先获取集群的最新的master对象
    master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)

    # 拼接子流程的全局只读参数
    parent_global_data = {
        "uid": uid,
        "bk_biz_id": cluster.bk_biz_id,
        "created_by": created_by,
        "cluster_id": cluster.id,
    }

    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)
    sub_sub_pipelines = []

    # 根据传入的待切换部署 TBinlogDumper id 列表变量，做切换处理
    for inst in switch_instances:
        old_dumper = ExtraProcessInstance.objects.get(id=inst["reduce_id"])

        # 按照实例维度声明子流程
        global_data = copy.deepcopy(parent_global_data)
        global_data["add_tbinlogdumper_conf"] = {"port": old_dumper.listen_port}
        sub_sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

        # 同步表结构到新的tbinlogdumper实例
        sub_sub_pipeline.add_act(
            act_name=_("导入相关表结构"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    exec_ip=master.machine.ip,
                    get_mysql_payload_func=TBinlogDumperActPayload.tbinlogdumper_load_schema_payload.__name__,
                    run_as_system_user=DBA_SYSTEM_USER,
                )
            ),
        )

        # 旧实例断开同步
        sub_sub_pipeline.add_act(
            act_name=_("中断同步"),
            act_component_code=TBinlogDumperStopSlaveComponent.code,
            kwargs=asdict(
                StopSlaveKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    is_safe=is_safe,
                    tbinlogdumper_ip=old_dumper.ip,
                    tbinlogdumper_port=old_dumper.listen_port,
                )
            ),
        )

        # 增加同步账号
        sub_sub_pipeline.add_act(
            act_name=_("新增repl帐户"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    exec_ip=master.machine.ip,
                    get_mysql_payload_func=MysqlActPayload.get_grant_mysql_repl_user_payload.__name__,
                    cluster={"new_slave_ip": master.machine.ip, "mysql_port": master.port},
                    run_as_system_user=DBA_SYSTEM_USER,
                )
            ),
        )

        # 根据传入的位点信息建立数据同步关系
        sub_sub_pipeline.add_act(
            act_name=_("建立主从关系"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    exec_ip=master.machine.ip,
                    get_mysql_payload_func=TBinlogDumperActPayload.tbinlogdumper_sync_data_payload.__name__,
                    cluster={
                        "master_ip": master.machine.ip,
                        "master_port": master.port,
                        "listen_port": inst["port"],
                        "bin_file": inst["repl_binlog_file"],
                        "bin_position": inst["repl_binlog_pos"],
                    },
                    run_as_system_user=DBA_SYSTEM_USER,
                )
            ),
        )
        sub_sub_pipelines.append(
            sub_sub_pipeline.build_sub_process(sub_name=_("切换到新实例[{}:{}]".format(master.machine.ip, inst["port"])))
        )

    # 在将实例子流程聚合到上层
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_sub_pipelines)

    return sub_pipeline.build_sub_process(sub_name=_("集群[{}]切换TBinlogDumper".format(cluster.name)))


def incr_sync_sub_flow(
    cluster: Cluster,
    root_id: str,
    uid: str,
    add_tbinlogdumper_conf: dict,
    created_by: str = "",
):
    """
    定义TBinlogDumper增量同步的子流程
    @param cluster: 操作的云区域id
    @param root_id: flow流程的root_id
    @param uid: 单据uid
    @param add_tbinlogdumper_conf: 待添加TBinlogdumper的实例配置
    @param created_by: 单据发起者
    """
    # 先获取集群的最新的master对象
    master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)

    # 拼接子流程的全局只读参数
    parent_global_data = {
        "uid": uid,
        "bk_biz_id": cluster.bk_biz_id,
        "created_by": created_by,
        "cluster_id": cluster.id,
        "add_tbinlogdumper_conf": add_tbinlogdumper_conf,
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 阶段1 对新TBinlogDumper做全表结构导入
    sub_pipeline.add_act(
        act_name=_("导入相关表结构"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=master.machine.ip,
                get_mysql_payload_func=TBinlogDumperActPayload.tbinlogdumper_load_schema_payload.__name__,
                run_as_system_user=DBA_SYSTEM_USER,
            )
        ),
    )

    # 阶段2 对新TBinlogDumper跟数据源做数据同步
    sub_pipeline.add_sub_pipeline(
        build_repl_by_manual_input_sub_flow(
            bk_cloud_id=cluster.bk_cloud_id,
            root_id=root_id,
            parent_global_data=parent_global_data,
            master_ip=master.machine.ip,
            slave_ip=master.machine.ip,
            master_port=master.port,
            slave_port=add_tbinlogdumper_conf["port"],
            is_tbinlogdumper=True,
        )
    )
    # 返回子流程
    return sub_pipeline.build_sub_process(
        sub_name=_("实例TBinlogDumper[{}:{}]做增量同步".format(master.machine.ip, add_tbinlogdumper_conf["port"]))
    )


def full_sync_sub_flow(
    cluster: Cluster,
    root_id: str,
    uid: str,
    add_tbinlogdumper_conf: dict,
    created_by: str = "",
):
    """
    定义TBinlogDumper全量同步的子流程
    @param cluster: 操作的云区域id
    @param root_id: flow流程的root_id
    @param uid: 单据uid
    @param add_tbinlogdumper_conf: 待添加TBinlogdumper的实例配置
    @param created_by: 单据发起者
    """
    # 先获取集群的最新的master、backup对象
    master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
    backup = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_SLAVE, is_stand_by=True)

    # 拼接子流程的全局只读参数
    parent_global_data = {
        "uid": uid,
        "bk_biz_id": cluster.bk_biz_id,
        "created_by": created_by,
        "cluster_id": cluster.id,
        "add_tbinlogdumper_conf": add_tbinlogdumper_conf,
        "backup_id": uuid.uuid1(),
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 阶段1 对新TBinlogDumper做全表结构导入
    sub_pipeline.add_act(
        act_name=_("导入相关表结构"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=master.machine.ip,
                get_mysql_payload_func=TBinlogDumperActPayload.tbinlogdumper_load_schema_payload.__name__,
                run_as_system_user=DBA_SYSTEM_USER,
            )
        ),
    )

    # 阶段2 添加同步账号
    sub_pipeline.add_act(
        act_name=_("新增repl帐户"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=master.machine.ip,
                get_mysql_payload_func=MysqlActPayload.get_grant_mysql_repl_user_payload.__name__,
                cluster={"new_slave_ip": master.machine.ip, "mysql_port": master.port},
                run_as_system_user=DBA_SYSTEM_USER,
            )
        ),
        write_payload_var="master_ip_sync_info",
    )

    # 阶段3 根据TBinlogDumper的同步数据配置，在从节点触发一次逻辑备份请求
    sub_pipeline.add_act(
        act_name=_("在slave[{}:{}]备份数据".format(backup.machine.ip, backup.port)),
        act_component_code=TBinlogDumperFullSyncDataComponent.code,
        kwargs=asdict(
            TBinlogDumperFullSyncDataKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                backup_ip=backup.machine.ip,
                backup_port=backup.port,
                backup_role=backup.instance_role,
                repl_tables=add_tbinlogdumper_conf["repl_tables"],
            )
        ),
        write_payload_var="backup_info",
    )

    # 阶段4 备份文件传输到TBinlogDumper机器，做导入数据准备
    sub_pipeline.add_act(
        act_name=_("传输备份文件到TBinlogDumper[{}]".format(master.machine.ip)),
        act_component_code=TBinlogDumperTransFileComponent.code,
        kwargs=asdict(
            P2PFileKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                file_list=[],
                file_target_path="",
                source_ip_list=[backup.machine.ip],
                exec_ip=master.machine.ip,
                run_as_system_user=DBA_SYSTEM_USER,
            )
        ),
    )

    # 阶段5 发起导入备份数据，同步与数据源建立同步
    sub_pipeline.add_act(
        act_name=_("导入备份数据"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=master.machine.ip,
                get_mysql_payload_func=TBinlogDumperActPayload.tbinlogdumper_restore_payload.__name__,
                run_as_system_user=DBA_SYSTEM_USER,
            )
        ),
    )

    # 返回子流程
    return sub_pipeline.build_sub_process(
        sub_name=_("实例TBinlogDumper[{}:{}]做全量同步".format(master.machine.ip, add_tbinlogdumper_conf["port"]))
    )


def init_machine_sub_flow(
    uid: str,
    root_id: str,
    init_machine: Machine,
    is_install_l5_agent: bool,
):
    """
    定义安装tbinlogdumper之前初始化内容
    初始化内容：
    1：安全初始化机器的dns_dbm域名解析（必选）
    2：安装L5客户端（可选）
    @param uid: 单据uid
    @param root_id: 主流程的root_id
    @param init_machine: 需要初始化的机器对象
    @param is_install_l5_agent: 是否安装L5 agent
    """

    # 声明子流程
    parent_global_data = {"uid": uid}
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    if is_install_l5_agent:
        sub_pipeline.add_act(
            act_name=_("安装L5agent"),
            act_component_code=L5AgentInstallComponent.code,
            kwargs={
                "ip": init_machine.ip,
                "bk_host_id": init_machine.bk_host_id,
            },
        )

    else:
        sub_pipeline.add_sub_pipeline(
            set_dns_atom_job(
                root_id=root_id,
                ticket_data=parent_global_data,
                act_kwargs=ActKwargs(),
                param={
                    "force": False,
                    "ip": init_machine.ip,
                    "bk_biz_id": init_machine.bk_biz_id,
                    "bk_cloud_id": init_machine.bk_cloud_id,
                    "bk_city": init_machine.bk_city,
                },
            )
        )
    # 返回子流程
    return sub_pipeline.build_sub_process(sub_name=_("初始化tbinlogdumper机器"))
