"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import NormalTBinlogDumperFlowException
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.util import get_tbinlogdumper_charset
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.tbinlogdumper.stop_slave import TBinlogDumperStopSlaveComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.tbinlogdumper.context_dataclass import StopSlaveKwargs

"""
定义一些TBinlogDumper流程上可能会用到的子流程，以便于减少代码的重复率
"""


def add_tbinlogdumper_sub_flow(
    cluster: Cluster,
    root_id: str,
    uid: str,
    add_conf_list: list,
    created_by: str = "",
):
    """
    定义添加TBinlogdumper实例的公共子流程
    @param cluster: 待操作的集群
    @param uid: 单据uid
    @param root_id: flow流程的root_id
    @param add_conf_list: 本次上架的配置列表，每个的元素的格式为：{"module_id":x,"area_name":x,add_type:x}
    @param created_by: 单据发起者
    """
    # 查找集群的当前master实例, tendb-ha架构无论什么时候只有一个master角色
    master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)

    # 获取TBinlogDumper的字符集配置，以mysql数据源的为准
    charset = get_tbinlogdumper_charset(ip=master.machine.ip, port=master.port, bk_cloud_id=cluster.bk_cloud_id)

    # 拼接子流程的只读全局参数
    parent_global_data = {
        "uid": uid,
        "add_conf_list": add_conf_list,
        "bk_biz_id": cluster.bk_biz_id,
        "created_by": created_by,
        "charset": charset,
    }
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

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
                get_mysql_payload_func=MysqlActPayload.install_tbinlogdumper_payload.__name__,
            )
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=_("安装TBinlogDumper实例flow"))


def reduce_tbinlogdumper_sub_flow(
    cluster: Cluster,
    root_id: str,
    uid: str,
    reduce_ids: list,
    created_by: str = "",
):
    """
    定义针对集群维度卸载TBinlogdumper实例的公共子流程
    @param cluster: 关联的cluster信息
    @param uid: 单据uid
    @param root_id: flow流程的root_id
    @param reduce_ids: 本次卸载的实例id列表
    @param created_by: 单据发起者
    """

    parent_global_data = {
        "uid": uid,
        "bk_biz_id": cluster.bk_biz_id,
        "created_by": created_by,
    }
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 阶段1 下发db-actuator介质包
    tbinlogdumpers = ExtraProcessInstance.objects.filter(id__in=reduce_ids)
    if len(tbinlogdumpers) == 0:
        # 如果根据下架的id list 获取的元信息为空，则作为异常处理
        raise NormalTBinlogDumperFlowException(message=_("传入的TBinlogDumper进程信息已不存在[{}]，请联系系统管理员".format(reduce_ids)))

    # 聚合并行下发dbactor, 避免出现下发异常
    sub_pipeline.add_act(
        act_name=_("下发db-actuator介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
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
                        get_mysql_payload_func=MysqlActPayload.uninstall_tbinlogdumper_payload.__name__,
                        cluster={"listen_ports": [inst.listen_port]},
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("集群[{}]卸载TBinlogDumper实例flow".format(cluster.name)))


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
    }

    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)
    sub_sub_pipelines = []

    # 根据传入的待切换部署 TBinlogDumper id 列表变量，做切换处理
    for inst in switch_instances:
        old_dumper = ExtraProcessInstance.objects.get(id=inst["reduce_id"])

        sub_sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

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
                    cluster={"new_slave_ip": master.machine.ip, "mysql_port": inst["port"]},
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
                    get_mysql_payload_func=MysqlActPayload.tbinlogdumper_sync_data_payload.__name__,
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

    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_sub_pipelines)

    return sub_pipeline.build_sub_process(sub_name=_("集群[{}]切换TBinlogDumper".format(cluster.name)))
