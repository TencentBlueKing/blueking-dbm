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
from backend.flow.consts import ACCOUNT_PREFIX, AUTH_ADDRESS_DIVIDER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import build_surrounding_apps_sub_flow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.add_user_for_cluster_switch import AddSwitchUserComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.slave_trans_flies import SlaveTransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import (
    get_cluster_info,
    get_cluster_ports,
    get_version_and_charset,
)
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSwitchUserKwargs,
    ClearMachineKwargs,
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    InstanceUserCloneKwargs,
    P2PFileKwargs,
    RecycleDnsRecordKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLMigrateClusterFlow(object):
    """
    构建mysql主从成对迁移抽象类
    支持多云区域操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

        # 定义备份文件存放到目标机器目录位置
        self.backup_target_path = f"/data/dbbak/{self.root_id}"

    def deploy_migrate_cluster_flow(self):
        """
        成对迁移集群主从节点。
        元数据信息修改顺序：
        1 mysql_migrate_cluster_add_instance
        2 mysql_migrate_cluster_add_tuple
        3 mysql_migrate_cluster_switch_storage
        """
        # 构建流程
        mysql_migrate_cluster_pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.data))
        sub_pipeline_list = []

        # 按照传入的infos信息，循环拼接子流程
        for one_machine in self.data["infos"]:
            ticket_data = copy.deepcopy(self.data)
            # 根据ip级别安装 mysql 列表
            cluster_ports = get_cluster_ports(one_machine["cluster_ids"])
            one_machine.update(cluster_ports)
            charset, db_version = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=one_machine["db_module_id"],
                cluster_type=one_machine["cluster_type"],
            )
            ticket_data["clusters"] = one_machine["clusters"]
            ticket_data["mysql_ports"] = one_machine["cluster_ports"]
            ticket_data["charset"] = charset
            ticket_data["db_version"] = db_version

            #  生成子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=one_machine["bk_cloud_id"],
                cluster_type=one_machine["cluster_type"],
                cluster=one_machine,
            )

            # 下发介质包
            sub_pipeline.add_act(
                act_name=_("下发MySQL介质{}").format([one_machine["new_slave_ip"], one_machine["new_master_ip"]]),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=one_machine["bk_cloud_id"],
                        exec_ip=[one_machine["new_slave_ip"], one_machine["new_master_ip"]],
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                            db_version=ticket_data["db_version"]
                        ),
                    )
                ),
            )

            # 初始化机器配置
            exec_act_kwargs.exec_ip = [one_machine["new_slave_ip"], one_machine["new_master_ip"]]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_sys_init_payload.__name__
            sub_pipeline.add_act(
                act_name=_("初始化机器{}").format(exec_act_kwargs.exec_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 并发安装mysql-crond
            acts_list = []
            for ip in [one_machine["new_slave_ip"], one_machine["new_master_ip"]]:
                exec_act_kwargs.exec_ip = ip
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("部署mysql-crond"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 安装mysql实例
            acts_list = []
            for ip in [one_machine["new_slave_ip"], one_machine["new_master_ip"]]:
                exec_act_kwargs.exec_ip = ip
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_mysql_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("安装MySQL实例:{}").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list)

            # 先记录元数据信息，关联对应的集群
            sub_pipeline.add_act(
                act_name=_("写入初始化实例的db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_migrate_cluster_add_instance.__name__,
                        cluster=one_machine,
                        is_update_trans_data=True,
                    )
                ),
            )

            # 先安装周边程序
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=one_machine["bk_cloud_id"],
                    master_ip_list=[one_machine["new_master_ip"]],
                    slave_ip_list=[one_machine["new_slave_ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(ticket_data),
                    is_init=True,
                    cluster_type=one_machine["cluster_type"],
                )
            )

            # 循环每个机器下的实例，做重建。
            restore_sub_list = []
            clusters_info = []
            # 第一步：恢复数据
            for one_id in one_machine["cluster_ids"]:
                one_cluster = get_cluster_info(one_id)
                # 复制一下2个值用于切换
                one_cluster["new_master_ip"] = one_machine["new_master_ip"]
                one_cluster["new_slave_ip"] = one_machine["new_slave_ip"]

                one_cluster["charset"] = charset
                one_cluster["change_master"] = False
                one_cluster["file_target_path"] = self.backup_target_path
                clusters_info.append(one_cluster)

                restore_slave_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))

                # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
                exec_act_kwargs = ExecActuatorKwargs(
                    bk_cloud_id=one_cluster["bk_cloud_id"],
                    cluster_type=one_cluster["cluster_type"],
                    cluster=one_cluster,
                )

                restore_slave_sub_pipeline.add_act(
                    act_name=_("下发db-actor到新节点{}").format([one_cluster["master_ip"], one_cluster["old_slave_ip"]]),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            exec_ip=[one_cluster["master_ip"], one_cluster["old_slave_ip"]],
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                )

                # 通过master、slave 获取备份的文件
                exec_act_kwargs.exec_ip = one_cluster["master_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("获取MASTER节点备份介质{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="master_backup_file",
                )

                exec_act_kwargs.exec_ip = one_cluster["old_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("获取SLAVE节点备份介质{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="slave_backup_file",
                )

                # 判断备份来源
                restore_slave_sub_pipeline.add_act(
                    act_name=_("判断备份文件来源,并传输备份文件新机器"),
                    act_component_code=SlaveTransFileComponent.code,
                    kwargs=asdict(
                        P2PFileKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            file_list=[],
                            file_target_path=self.backup_target_path,
                            source_ip_list=[],
                            exec_ip=[one_cluster["new_slave_ip"], one_cluster["new_master_ip"]],
                        )
                    ),
                )

                # 恢复数据
                restore_list = []
                exec_act_kwargs.exec_ip = one_cluster["new_master_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_restore_slave_payload.__name__
                restore_list.append(
                    {
                        "act_name": _("恢复新主节点数据{}:{}").format(exec_act_kwargs.exec_ip, one_cluster["backend_port"]),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                        "write_payload_var": "change_master_info",
                    }
                )

                exec_act_kwargs.exec_ip = one_cluster["new_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_restore_slave_payload.__name__
                restore_list.append(
                    {
                        "act_name": _("恢复新从节点数据{}:{}").format(exec_act_kwargs.exec_ip, one_cluster["backend_port"]),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
                restore_slave_sub_pipeline.add_parallel_acts(acts_list=restore_list)

                # 恢复完毕后。change master。先change 新从库的，再change新主库的
                exec_act_kwargs.exec_ip = one_cluster["new_master_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_grant_mysql_repl_user_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("新增repl帐户{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="master_ip_sync_info",
                )

                exec_act_kwargs.exec_ip = one_cluster["new_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_change_master_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("建立主从关系{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )

                # 主节点执行change master
                exec_act_kwargs.exec_ip = one_cluster["master_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_grant_repl_for_migrate_cluster.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("新增repl帐户{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )
                exec_act_kwargs.exec_ip = one_cluster["new_master_ip"]
                exec_act_kwargs.get_mysql_payload_func = (
                    MysqlActPayload.get_change_master_payload_for_migrate_cluster.__name__
                )
                restore_slave_sub_pipeline.add_act(
                    act_name=_("建立主从关系 {}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )

                # 数据同步完毕，需要写入 新主和旧主之间的关系链
                restore_slave_sub_pipeline.add_act(
                    act_name=_("数据恢复完毕,写入新主节点和旧主节点的关系链元数据"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_migrate_cluster_add_tuple.__name__,
                            cluster=one_cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                restore_sub_list.append(restore_slave_sub_pipeline.build_sub_process(sub_name=_("恢复实例数据")))

            # 第二步 切换
            switch_sub_list = []
            for one_cluster in clusters_info:
                switch_slave_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
                switch_slave_sub_pipeline.add_sub_pipeline(
                    sub_flow=self.build_cluster_switch_sub_flow(cluster=one_cluster)
                )

                switch_slave_sub_pipeline.add_act(
                    act_name=_("写入切换集群 {} 的元信息".format(one_cluster["cluster_id"])),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_migrate_cluster_switch_storage.__name__,
                            cluster=one_cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                switch_sub_list.append(switch_slave_sub_pipeline.build_sub_process(sub_name=_("切换实例")))

            # 第四步 卸载实例
            uninstall_sub_list = []
            for one_cluster in clusters_info:
                uninstall_slave_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
                uninstall_slave_sub_pipeline.add_sub_pipeline(
                    sub_flow=self.uninstall_instance_sub_flow(ticket_data=ticket_data, cluster_info=one_cluster)
                )
                uninstall_sub_list.append(uninstall_slave_sub_pipeline.build_sub_process(sub_name=_("卸载实例")))

            # 流程: 恢复数据>切换>安装周边>卸载
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=restore_sub_list)
            # 切换前安装周边组件
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=one_machine["bk_cloud_id"],
                    master_ip_list=[one_machine["new_master_ip"]],
                    slave_ip_list=[one_machine["new_slave_ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(ticket_data),
                    is_init=True,
                    cluster_type=one_machine["cluster_type"],
                )
            )
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_list)
            # 第三步，机器级别再次先安装周边程序
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=one_machine["bk_cloud_id"],
                    master_ip_list=[one_machine["new_master_ip"]],
                    slave_ip_list=[one_machine["new_slave_ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(ticket_data),
                    is_init=True,
                    cluster_type=one_machine["cluster_type"],
                )
            )
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_sub_list)
            sub_pipeline_list.append(sub_pipeline.build_sub_process(sub_name=_("成对迁移集群的主从节点")))
        mysql_migrate_cluster_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_migrate_cluster_pipeline.run_pipeline(init_trans_data_class=ClusterInfoContext())

    def build_cluster_switch_sub_flow(self, cluster: dict):
        """
        定义成对迁移完成，做成对切换的子流程(子流程是已集群维度做成对切换)
        成对切换更多解决一主一从的集群机器裁撤场景；对于一主多从的集群，
        并不实现集群所有节点的替换，剩余的从实例节点需要同步新主的数据，保证集群数据一致性
        @param cluster: 集群信息
        """

        # 随机生成切换测试账号和密码
        switch_account = f"{ACCOUNT_PREFIX}{get_random_string(length=8)}"
        switch_pwd = get_random_string(length=16)

        # 拼接子流程需要全局参数
        switch_sub_flow_context = copy.deepcopy(self.data)
        switch_sub_flow_context.pop("infos")

        # 把公共参数拼接到子流程的全局只读上下文
        switch_sub_flow_context["is_safe"] = True
        switch_sub_flow_context["is_dead_master"] = False
        switch_sub_flow_context["grant_repl"] = True
        switch_sub_flow_context["locked_switch"] = True
        switch_sub_flow_context["switch_pwd"] = switch_pwd
        switch_sub_flow_context["switch_account"] = switch_account
        switch_sub_flow_context["change_master_force"] = True

        # 拼接执行原子任务的活动节点需要的通用的私有参数，引用注意参数覆盖的问题
        cluster_sw_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=cluster["bk_cloud_id"])

        # 针对集群维度声明子流程
        cluster_switch_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(switch_sub_flow_context))

        add_sw_user_kwargs = AddSwitchUserKwargs(
            bk_cloud_id=cluster["bk_cloud_id"],
            user=switch_account,
            psw=switch_pwd,
            hosts=[cluster["new_master_ip"]],
        )
        acts_list = []
        add_sw_user_kwargs.address = f"{cluster['master_ip']}{AUTH_ADDRESS_DIVIDER}{cluster['mysql_port']}"
        acts_list.append(
            {
                "act_name": _("给master添加切换临时账号"),
                "act_component_code": AddSwitchUserComponent.code,
                "kwargs": asdict(add_sw_user_kwargs),
            }
        )
        add_sw_user_kwargs.address = f"{cluster['new_slave_ip']}{AUTH_ADDRESS_DIVIDER}{cluster['mysql_port']}"
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
                    "source": f"{cluster['old_master_ip']}{AUTH_ADDRESS_DIVIDER}{cluster['mysql_port']}",
                    "target": f"{cluster['new_master_ip']}{AUTH_ADDRESS_DIVIDER}{cluster['mysql_port']}",
                    "bk_cloud_id": cluster["bk_cloud_id"],
                },
                {
                    "source": f"{cluster['old_slave_ip']}{AUTH_ADDRESS_DIVIDER}{cluster['mysql_port']}",
                    "target": f"{cluster['new_slave_ip']}{AUTH_ADDRESS_DIVIDER}{cluster['mysql_port']}",
                    "bk_cloud_id": cluster["bk_cloud_id"],
                },
            ]
        )
        cluster_switch_sub_pipeline.add_act(
            act_name=_("新master克隆旧master权限"),
            act_component_code=CloneUserComponent.code,
            kwargs=asdict(clone_kwargs),
        )

        cluster_sw_kwargs.exec_ip = cluster["new_master_ip"]
        cluster_sw_kwargs.get_mysql_payload_func = MysqlActPayload.get_set_backend_toward_slave_payload.__name__
        cluster_switch_sub_pipeline.add_act(
            act_name=_("执行集群切换"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(cluster_sw_kwargs),
            write_payload_var=ClusterInfoContext.get_sync_info_var_name(),
        )

        # 并发change master 的 原子任务，集群所有的slave节点同步new master 的数据
        if cluster["other_slave_info"]:
            # 如果集群存在其他slave节点，则建立新的你主从关系
            acts_list = []
            for exec_ip in cluster["other_slave_info"]:
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
                        dns_op_exec_port=cluster["mysql_port"],
                        exec_ip=cluster["old_slave_ip"],
                        bk_cloud_id=cluster["bk_cloud_id"],
                    )
                ),
            }
        ]

        for slave_domain in cluster["slave_dns_list"]:
            acts_list.append(
                {
                    "act_name": _("对新slave添加域名映射"),
                    "act_component_code": MySQLDnsManageComponent.code,
                    "kwargs": asdict(
                        CreateDnsKwargs(
                            bk_cloud_id=cluster["bk_cloud_id"],
                            dns_op_exec_port=cluster["mysql_port"],
                            exec_ip=cluster["new_slave_ip"],
                            add_domain_name=slave_domain,
                        )
                    ),
                }
            )

        cluster_switch_sub_pipeline.add_parallel_acts(acts_list=acts_list)

        return cluster_switch_sub_pipeline.build_sub_process(sub_name=_("{}集群执行成对切换").format(cluster["name"]))

    # 实例卸载子流程
    def uninstall_instance_sub_flow(self, ticket_data: dict, cluster_info: dict):
        sub_ticket_data = copy.deepcopy(ticket_data)
        sub_ticket_data["force"] = True
        uninstall_sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_ticket_data)

        sub_acts_list = []
        for exec_ip in [cluster_info["old_master_ip"], cluster_info["old_slave_ip"]]:
            sub_acts_list.append(
                {
                    "act_name": _("清理实例周边配置"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            exec_ip=exec_ip,
                            bk_cloud_id=cluster_info["bk_cloud_id"],
                            cluster=cluster_info,
                            get_mysql_payload_func=MysqlActPayload.get_clear_surrounding_config_payload.__name__,
                        )
                    ),
                }
            )
        uninstall_sub_pipeline.add_parallel_acts(acts_list=sub_acts_list)

        sub_acts_list = []
        for exec_ip in [cluster_info["old_master_ip"], cluster_info["old_slave_ip"]]:
            sub_acts_list.append(
                {
                    "act_name": _("卸载MySQL实例:{}:{}").format(exec_ip, cluster_info["backend_port"]),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            exec_ip=exec_ip,
                            bk_cloud_id=cluster_info["bk_cloud_id"],
                            cluster=cluster_info,
                            get_mysql_payload_func=MysqlActPayload.get_uninstall_mysql_payload.__name__,
                        )
                    ),
                }
            )
        uninstall_sub_pipeline.add_parallel_acts(sub_acts_list)
        # 卸载完毕修改元数据
        uninstall_sub_pipeline.add_act(
            act_name=_("卸载主从实例完毕，修改元数据"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.mysql_cluster_migrate_remote_instance.__name__,
                    cluster=cluster_info,
                )
            ),
        )
        # 清理机器。会自动判断机器是否存在实例
        exec_ips = [cluster_info["old_master_ip"], cluster_info["old_slave_ip"]]
        uninstall_sub_pipeline.add_act(
            act_name=_("清理机器配置"),
            act_component_code=MySQLClearMachineComponent.code,
            kwargs=asdict(
                ClearMachineKwargs(
                    exec_ip=exec_ips,
                    bk_cloud_id=cluster_info["bk_cloud_id"],
                )
            ),
        )
        return uninstall_sub_pipeline.build_sub_process(_("卸载实例"))
