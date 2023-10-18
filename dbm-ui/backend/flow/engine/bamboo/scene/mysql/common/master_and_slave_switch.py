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

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterEntryType, InstanceInnerRole
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.consts import ACCOUNT_PREFIX, AUTH_ADDRESS_DIVIDER, InstanceStatus
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.add_user_for_cluster_switch import AddSwitchUserComponent
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSwitchUserKwargs,
    CreateDnsKwargs,
    ExecActuatorKwargs,
    InstanceUserCloneKwargs,
    RecycleDnsRecordKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext

logger = logging.getLogger("flow")


def master_and_slave_switch(root_id: str, ticket_data: dict, cluster: Cluster, cluster_info: dict):
    """
    定义成对迁移完成，做成对切换的子流程(子流程是已集群维度做成对切换)
    成对切换更多解决一主一从的集群机器裁撤场景；对于一主多从的集群，
    并不实现集群所有节点的替换，剩余的从实例节点需要同步新主的数据，保证集群数据一致性
    @param root_id: root id
    @param ticket_data: 单据数据
    @param cluster_info: 输入集群信息
    @param cluster: 集群信息
    """

    cluster_info["master_port"] = cluster_info["mysql_port"]
    cluster_info["slave_port"] = cluster_info["mysql_port"]
    cluster_info["slave_ip"] = cluster_info["old_slave_ip"]
    cluster_info["master_ip"] = cluster_info["old_master_ip"]

    # 随机生成切换测试账号和密码
    switch_account = f"{ACCOUNT_PREFIX}{get_random_string(length=8)}"
    switch_pwd = get_random_string(length=16)
    # 拼接子流程需要全局参数
    switch_sub_flow_context = copy.deepcopy(ticket_data)
    # 把公共参数拼接到子流程的全局只读上下文
    switch_sub_flow_context["is_safe"] = True
    switch_sub_flow_context["is_dead_master"] = False
    switch_sub_flow_context["grant_repl"] = True
    switch_sub_flow_context["locked_switch"] = True
    switch_sub_flow_context["switch_pwd"] = switch_pwd
    switch_sub_flow_context["switch_account"] = switch_account

    # 针对集群维度声明子流程
    cluster_switch_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(switch_sub_flow_context))

    # todo ？授权切换账号
    add_sw_user_kwargs = AddSwitchUserKwargs(
        bk_cloud_id=cluster.bk_cloud_id,
        user=switch_account,
        psw=switch_pwd,
        hosts=[cluster_info["new_master_ip"]],
    )
    acts_list = []
    add_sw_user_kwargs.address = f"{cluster_info['old_master_ip']}{AUTH_ADDRESS_DIVIDER}{cluster_info['mysql_port']}"
    acts_list.append(
        {
            "act_name": _("给master添加切换临时账号"),
            "act_component_code": AddSwitchUserComponent.code,
            "kwargs": asdict(add_sw_user_kwargs),
        }
    )
    add_sw_user_kwargs.address = f"{cluster_info['new_slave_ip']}{AUTH_ADDRESS_DIVIDER}{cluster_info['mysql_port']}"
    acts_list.append(
        {
            "act_name": _("给新slave添加切换临时账号"),
            "act_component_code": AddSwitchUserComponent.code,
            "kwargs": asdict(add_sw_user_kwargs),
        }
    )
    cluster_switch_sub_pipeline.add_parallel_acts(acts_list=acts_list)

    clone_kwargs = InstanceUserCloneKwargs(
        clone_data=[
            {
                "source": f"{cluster_info['old_master_ip']}{AUTH_ADDRESS_DIVIDER}{cluster_info['mysql_port']}",
                "target": f"{cluster_info['new_master_ip']}{AUTH_ADDRESS_DIVIDER}{cluster_info['mysql_port']}",
                "bk_cloud_id": cluster.bk_cloud_id,
            },
            {
                "source": f"{cluster_info['old_slave_ip']}{AUTH_ADDRESS_DIVIDER}{cluster_info['mysql_port']}",
                "target": f"{cluster_info['new_slave_ip']}{AUTH_ADDRESS_DIVIDER}{cluster_info['mysql_port']}",
                "bk_cloud_id": cluster.bk_cloud_id,
            },
        ]
    )
    cluster_switch_sub_pipeline.add_act(
        act_name=_("新master克隆旧master权限,新slave克隆旧slave权限"),
        act_component_code=CloneUserComponent.code,
        kwargs=asdict(clone_kwargs),
    )

    # 代理层、账号等等。
    mysql_proxy = cluster.proxyinstance_set.all()
    domain = ClusterEntry.get_cluster_entry_map_by_cluster_ids([cluster.id])
    mysql_storage_slave = cluster.storageinstance_set.filter(
        instance_inner_role=InstanceInnerRole.SLAVE.value, status=InstanceStatus.RUNNING.value
    )
    cluster_info["other_slave_info"] = [
        y.machine.ip for y in mysql_storage_slave.exclude(machine__ip=cluster_info["old_slave_ip"])
    ]
    cluster_info["master_domain"] = domain[cluster.id]["master_domain"]
    cluster_info["slave_domain"] = domain[cluster.id]["slave_domain"]
    cluster_info["proxy_ip_list"] = [x.machine.ip for x in mysql_proxy]
    cluster_info["proxy_port"] = mysql_proxy[0].port

    cluster_sw_kwargs = ExecActuatorKwargs(cluster=cluster_info, bk_cloud_id=cluster.bk_cloud_id)
    cluster_sw_kwargs.exec_ip = cluster_info["new_master_ip"]
    cluster_sw_kwargs.get_mysql_payload_func = MysqlActPayload.get_set_backend_toward_slave_payload.__name__
    cluster_switch_sub_pipeline.add_act(
        act_name=_("执行集群切换"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(cluster_sw_kwargs),
        write_payload_var=ClusterInfoContext.get_sync_info_var_name(),
    )

    # 并发change master 的 原子任务，集群所有的slave节点同步new master 的数据
    if cluster_info["other_slave_info"]:
        # 如果集群存在其他slave节点，则建立新的你主从关系
        acts_list = []
        for exec_ip in cluster_info["other_slave_info"]:
            cluster_sw_kwargs.exec_ip = exec_ip
            cluster_sw_kwargs.get_mysql_payload_func = MysqlActPayload.get_change_master_payload.__name__
            acts_list.append(
                {
                    "act_name": _("其余slave节点同步新master数据"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(cluster_sw_kwargs),
                }
            )
        cluster_switch_sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 更改旧slave 和 新slave 的域名映射关系，并发执行
    acts_list = [
        {
            "act_name": _("回收旧slave的域名映射"),
            "act_component_code": MySQLDnsManageComponent.code,
            "kwargs": asdict(
                RecycleDnsRecordKwargs(
                    dns_op_exec_port=cluster_info["mysql_port"],
                    exec_ip=cluster_info["old_slave_ip"],
                    bk_cloud_id=cluster_info["bk_cloud_id"],
                )
            ),
        }
    ]
    old_slave = cluster.storageinstance_set.get(machine__ip=cluster_info["old_slave_ip"])
    slave_dns_list = old_slave.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
    cluster_info["slave_dns_list"] = [i.entry for i in slave_dns_list]
    for slave_domain in cluster_info["slave_dns_list"]:
        acts_list.append(
            {
                "act_name": _("对新slave添加域名映射"),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    CreateDnsKwargs(
                        bk_cloud_id=cluster_info["bk_cloud_id"],
                        dns_op_exec_port=cluster_info["mysql_port"],
                        exec_ip=cluster_info["new_slave_ip"],
                        add_domain_name=slave_domain,
                    )
                ),
            }
        )

    cluster_switch_sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return cluster_switch_sub_pipeline.build_sub_process(sub_name=_("{}集群执行成对切换").format(cluster_info["cluster_id"]))
