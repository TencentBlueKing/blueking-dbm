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

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.consts import ACCOUNT_PREFIX, AUTH_ADDRESS_DIVIDER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_surrounding_apps_sub_flow,
    check_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.plugins.components.collections.mysql.add_user_for_cluster_switch import AddSwitchUserComponent
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.tbinlogdumper.link_tbinlogdumper_switch import (
    LinkTBinlogDumperSwitchComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSwitchUserKwargs,
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    InstanceUserCloneKwargs,
    RecycleDnsRecordKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterSwitchContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.tbinlogdumper.context_dataclass import LinkTBinlogDumperSwitchKwargs

logger = logging.getLogger("flow")


class MySQLMasterSlaveSwitchFlow(object):
    """
    构建mysql主从版集群master-slave的互切流程，产品形态是整机切换，保证同一台机器的所有实例要不master角色，要不slave角色
    目前集群级别的互切的流程如下：
    1：下发db-actuator介质到slave机器
    2：添加主从切换的临时远程账号（第4步执行会回收）
    3: 克隆master实例的权限到slave实例（待升级为master的slave实例）
    4：在slave节点执行故障场景的集群切换逻辑（db-actuator）
    5：如果存在其他的slave实例，则剩余的slave实例同步新的master数据（master也会同步）（db-actuator）
    6：回收新master之前的从域名映射信息
    7：添加旧master的从域名映射信息
    8：修改db-meta元数据
    9：重建备份程序和数据校验
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def get_cluster_info(cluster_id: int, bk_biz_id: int, new_master_ip: str, old_master_ip: str) -> dict:
        """
        定义获取切换集群的基本信息的方法
        @param cluster_id :集群id
        @param bk_biz_id: 业务id
        @param new_master_ip: 待升主的slave ip
        @param old_master_ip: 目前的集群的master ip
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=cluster_id, bk_biz_id=bk_biz_id, message=_("集群不存在"))

        proxy_info = ProxyInstance.objects.filter(cluster=cluster).all()
        new_master = StorageInstance.objects.get(machine__ip=new_master_ip, cluster=cluster)

        if not new_master.is_stand_by:
            # 传来的待新主实例，is_stand_by为False，则中断流程，报异常
            raise NormalTenDBFlowException(
                message=_("the is_stand_by of new-master-instance [{}] is False ".format(new_master.ip_port))
            )

        other_slave_info = (
            StorageInstance.objects.filter(cluster=cluster, instance_inner_role=InstanceInnerRole.SLAVE)
            .exclude(machine__ip=new_master_ip)
            .all()
        )

        slave_dns_list = new_master.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()

        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "proxy_port": proxy_info[0].port,
            "proxy_ip_list": [p.machine.ip for p in proxy_info],
            "mysql_port": new_master.port,
            "other_slave_info": [m.machine.ip for m in other_slave_info],
            "slave_dns_list": [i.entry for i in slave_dns_list],
            "new_master_ip": new_master_ip,
            "old_master_ip": old_master_ip,
        }

    @staticmethod
    def get_handle_domain_act_list(
        master_ip: str,
        slave_ip: str,
        mysql_port: int,
        slave_dns_list: list,
        bk_cloud_id: int,
    ):
        """
        拼接主从切换后域名处理的并发执行act的列表
        @param master_ip: 原主实例的ip
        @param slave_ip: 原从实例的ip
        @param mysql_port: 集群实例端口
        @param slave_dns_list: 从实例对应的域名信息列表
        @param bk_cloud_id: 云区域id
        """
        acts_list = [
            {
                "act_name": _("回收新master的域名映射"),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    RecycleDnsRecordKwargs(
                        dns_op_exec_port=mysql_port,
                        exec_ip=slave_ip,
                        bk_cloud_id=bk_cloud_id,
                    )
                ),
            }
        ]

        for slave_domain in slave_dns_list:
            acts_list.append(
                {
                    "act_name": _("对旧master添加域名映射"),
                    "act_component_code": MySQLDnsManageComponent.code,
                    "kwargs": asdict(
                        CreateDnsKwargs(
                            bk_cloud_id=bk_cloud_id,
                            dns_op_exec_port=mysql_port,
                            exec_ip=master_ip,
                            add_domain_name=slave_domain,
                        )
                    ),
                }
            )
        return acts_list

    def master_slave_switch_flow(self):
        """
        定义mysql集群主从互切的流程
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = []
        for i in self.data["infos"]:
            cluster_ids.extend(i["cluster_ids"])

        mysql_switch_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids))
        )
        sub_pipelines = []

        # 定义切换流程中用的账号密码，密码是随机生成16位字符串，并利用公钥进行加密
        switch_pwd = get_random_string(length=16)

        switch_account = f"{ACCOUNT_PREFIX}{get_random_string(length=8)}"

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
                sub_sub_flow_context["is_dead_master"] = False
                sub_sub_flow_context["grant_repl"] = True
                sub_sub_flow_context["locked_switch"] = True
                sub_sub_flow_context["switch_pwd"] = switch_pwd
                sub_sub_flow_context["switch_account"] = switch_account
                sub_sub_flow_context["change_master_force"] = True

                # 获取对应的集群信息
                cluster = self.get_cluster_info(
                    cluster_id=cluster_id,
                    bk_biz_id=sub_sub_flow_context["bk_biz_id"],
                    new_master_ip=info["slave_ip"]["ip"],
                    old_master_ip=info["master_ip"]["ip"],
                )

                # 拼接切换执行活动节点需要的通用的私有参数
                cluster_sw_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=cluster["bk_cloud_id"])

                # 针对集群维度声明子流程
                cluster_switch_sub_pipeline = SubBuilder(
                    root_id=self.root_id, data=copy.deepcopy(sub_sub_flow_context)
                )

                # 切换前做预检测
                sub_flow = check_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=Cluster.objects.get(id=cluster_id, bk_biz_id=sub_sub_flow_context["bk_biz_id"]),
                    is_check_client_conn=sub_sub_flow_context["is_check_process"],
                    is_verify_checksum=sub_sub_flow_context["is_verify_checksum"],
                    check_client_conn_inst=[
                        f"{cluster['old_master_ip']}{IP_PORT_DIVIDER}{cluster['mysql_port']}",
                        f"{cluster['new_master_ip']}{IP_PORT_DIVIDER}{cluster['mysql_port']}",
                    ],
                    verify_checksum_tuples=[
                        {
                            "master": f"{cluster['old_master_ip']}{IP_PORT_DIVIDER}{cluster['mysql_port']}",
                            "slave": f"{cluster['new_master_ip']}{IP_PORT_DIVIDER}{cluster['mysql_port']}",
                        }
                    ],
                )
                if sub_flow:
                    cluster_switch_sub_pipeline.add_sub_pipeline(sub_flow=sub_flow)

                # 阶段1 添加切换的临时账号
                cluster_switch_sub_pipeline.add_act(
                    act_name=_("旧master添加切换临时账号"),
                    act_component_code=AddSwitchUserComponent.code,
                    kwargs=asdict(
                        AddSwitchUserKwargs(
                            bk_cloud_id=cluster["bk_cloud_id"],
                            user=switch_account,
                            psw=switch_pwd,
                            address=f"{cluster['old_master_ip']}{AUTH_ADDRESS_DIVIDER}{cluster['mysql_port']}",
                            hosts=[cluster["new_master_ip"]],
                        ),
                    ),
                )

                # 阶段2 主实例的账号信息克隆到从实例上
                cluster_switch_sub_pipeline.add_act(
                    act_name=_("新master克隆旧master权限"),
                    act_component_code=CloneUserComponent.code,
                    kwargs=asdict(
                        InstanceUserCloneKwargs(
                            clone_data=[
                                {
                                    "source": f"{info['master_ip']['ip']}{AUTH_ADDRESS_DIVIDER}{cluster['mysql_port']}",
                                    "target": f"{info['slave_ip']['ip']}{AUTH_ADDRESS_DIVIDER}{cluster['mysql_port']}",
                                    "bk_cloud_id": cluster["bk_cloud_id"],
                                },
                            ]
                        )
                    ),
                )

                # 阶段3 执行主从切换的原子任务
                cluster_sw_kwargs.exec_ip = info["slave_ip"]["ip"]
                cluster_sw_kwargs.get_mysql_payload_func = (
                    MysqlActPayload.get_set_backend_toward_slave_payload.__name__
                )
                cluster_switch_sub_pipeline.add_act(
                    act_name=_("执行集群切换"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(cluster_sw_kwargs),
                    write_payload_var=ClusterSwitchContext.get_new_master_bin_pos_var_name(),
                )

                # 阶段4 并发change master 的 原子任务，集群所有的slave节点同步new master 的数据
                acts_list = []

                for exec_ip in [info["master_ip"]["ip"]] + cluster["other_slave_info"]:
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

                # 阶段5 更改旧master 和 新master 的域名映射关系，并发执行
                cluster_switch_sub_pipeline.add_parallel_acts(
                    acts_list=self.get_handle_domain_act_list(
                        master_ip=info["master_ip"]["ip"],
                        slave_ip=info["slave_ip"]["ip"],
                        mysql_port=int(cluster["mysql_port"]),
                        slave_dns_list=cluster["slave_dns_list"],
                        bk_cloud_id=cluster["bk_cloud_id"],
                    )
                )

                # 增加tbinlogdumper实例部署切换联动
                if ExtraProcessInstance.objects.filter(cluster_id=cluster_id).exists():
                    cluster_switch_sub_pipeline.add_act(
                        act_name=_("联动TBinlogDumper切换单据"),
                        act_component_code=LinkTBinlogDumperSwitchComponent.code,
                        kwargs=asdict(
                            LinkTBinlogDumperSwitchKwargs(
                                cluster_id=cluster_id,
                                target_ip=info["slave_ip"]["ip"],
                                get_binlog_info=ClusterSwitchContext.get_new_master_bin_pos_var_name(),
                            )
                        ),
                    )

                cluster_switch_sub_list.append(
                    cluster_switch_sub_pipeline.build_sub_process(sub_name=_("{}集群执行主从切换").format(cluster["name"]))
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_switch_sub_list)

            # 阶段6 按照机器维度变更db-meta数据，cluster变量传入info信息
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

            # 阶段7 切换后重建备份程序和数据校验程序
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

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("主从切换流程[整机切换]")))

        mysql_switch_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_switch_pipeline.run_pipeline(init_trans_data_class=ClusterSwitchContext(), is_drop_random_user=True)
