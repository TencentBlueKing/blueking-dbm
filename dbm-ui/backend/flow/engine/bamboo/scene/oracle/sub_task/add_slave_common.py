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
import os
from dataclasses import asdict
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_ORACLE_USER, DBA_ROOT_USER, DEPENDENCIES_PLUGINS, ManagerDefaultPort
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.oracle.exec_actuator_script import (
    ExecuteOracleActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.oracle.oracle_db_meta import OracleDBMetaComponent
from backend.flow.plugins.components.collections.oracle.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.oracle.upload_file import UploadFileServiceComponent
from backend.flow.utils.common_act_dataclass import InitCheckKwargs, InstallNodemanPluginKwargs
from backend.flow.utils.mysql.mysql_act_dataclass import UpdateDnsRecordKwargs
from backend.flow.utils.oracle.oracle_act_dataclass import DownloadMediaKwargs, UploadFile
from backend.flow.utils.oracle.oracle_act_payload import OracleActPayload
from backend.flow.utils.oracle.oracle_context_dataclass import AddSlaveContext, OracleActKwargs
from backend.flow.utils.oracle.oracle_db_meta import OracleDBMeta

BKREPO_ORACLE_PATH = "oracle/files"


def _make_oracle_act(
    act_name: str,
    exec_ip: str,
    bk_cloud_id: int,
    payload_func_name: str,
    run_as_system_user: Optional[str] = DBA_ORACLE_USER,
    write_payload_var: Optional[str] = None,
) -> Dict:
    """
    构造一个执行 oracle actuator 脚本的 act 描述 dict.
    返回的 dict 可直接被 SubBuilder.add_act(**dict) 使用.
    """
    act = {
        "act_name": act_name,
        "act_component_code": ExecuteOracleActuatorScriptComponent.code,
        "kwargs": asdict(
            OracleActKwargs(
                exec_ip=exec_ip,
                bk_cloud_id=bk_cloud_id,
                run_as_system_user=run_as_system_user,
                get_oracle_payload_func=payload_func_name,
            )
        ),
    }
    if write_payload_var is not None:
        act["write_payload_var"] = write_payload_var
    return act


def build_precheck_sub_flow(root_id: str, data: Dict, new_slave: str, bk_cloud_id: int) -> SubBuilder:
    """
    公共前置检查子流程: 空闲检查 + 并发安装依赖插件.
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=data)
    sub_pipeline.add_act(
        act_name=_("空闲检查[{}]".format(new_slave)),
        act_component_code=CheckMachineIdleComponent.code,
        kwargs=asdict(InitCheckKwargs(ips=[new_slave], bk_cloud_id=bk_cloud_id)),
    )

    acts_list = []
    for plugin_name in DEPENDENCIES_PLUGINS:
        acts_list.append(
            {
                "act_name": _("安装[{}]插件".format(plugin_name)),
                "act_component_code": InstallNodemanPluginServiceComponent.code,
                "kwargs": asdict(
                    InstallNodemanPluginKwargs(ips=[new_slave], plugin_name=plugin_name, bk_cloud_id=bk_cloud_id)
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("环境预检查与依赖安装"))


def build_media_transfer_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    old_hosts: List[str],
    new_slave: str,
    db_version: str,
    patch_list: List,
) -> SubBuilder:
    """
    介质下发子流程: 旧实例侧下发 actuator + 新备库下发 actuator 与 oracle 介质.
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=data)
    sub_pipeline.add_act(
        act_name=_("旧实例下发actuator"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=old_hosts,
                file_list=GetFileList(db_type=DBType.Oracle).get_db_actuator_package(),
            )
        ),
    )
    sub_pipeline.add_act(
        act_name=_("新备库下发actuator以及oracle介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=new_slave,
                file_list=GetFileList(db_type=DBType.Oracle).oracle_install_package(db_version, patch_list),
            )
        ),
    )
    return sub_pipeline.build_sub_process(sub_name=_("下发介质"))


def build_fetch_and_dispatch_files_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    old_node: str,
    new_slave: str,
    uid: str,
) -> SubBuilder:
    """
    获取并下发参数/密码文件子流程.
    包含: 获取参数文件 -> 获取密码文件 -> 上传参数文件 -> 上传密码文件 -> 下发到新备库.
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=data)

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("获取参数文件"),
            exec_ip=old_node,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_pfile_payload.__name__,
            write_payload_var=AddSlaveContext.get_pfile_var_name(),
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("获取密码文件"),
            exec_ip=old_node,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_password_file_payload.__name__,
            write_payload_var=AddSlaveContext.get_orapw_var_name(),
        )
    )

    pfile = _("{}.pfile.ora".format(uid))
    orapw = _("{}.orapw.ora".format(uid))

    sub_pipeline.add_act(
        act_name=_("上传参数文件"),
        act_component_code=UploadFileServiceComponent.code,
        kwargs=asdict(
            UploadFile(
                path=os.path.join(BKREPO_ORACLE_PATH, pfile),
                content_var=AddSlaveContext.get_pfile_var_name(),
            )
        ),
    )

    sub_pipeline.add_act(
        act_name=_("上传密码文件"),
        act_component_code=UploadFileServiceComponent.code,
        kwargs=asdict(
            UploadFile(
                path=os.path.join(BKREPO_ORACLE_PATH, orapw),
                content_var=AddSlaveContext.get_orapw_var_name(),
                encoding="base64",
            )
        ),
    )

    sub_pipeline.add_act(
        act_name=_("下发参数与密码文件"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=new_slave,
                file_list=GetFileList(db_type=DBType.Oracle).oracle_file(
                    path=BKREPO_ORACLE_PATH, filelist=[pfile, orapw]
                ),
            )
        ),
    )
    return sub_pipeline.build_sub_process(sub_name=_("获取并下发参数与密码文件"))


def build_new_slave_setup_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    old_node: str,
    new_slave: str,
    via_cascading: bool = False,
) -> SubBuilder:
    """
    新备库初始化子流程: 获取软链接配置 -> 系统配置初始化 -> 部署 Oracle 软件 -> 部署 Oracle 实例.

    @param via_cascading: 是否为级联模式.
                          True  -> 部署实例使用 get_install_instance_via_cascading_trans_payload;
                          False -> 部署实例使用 get_install_instance_trans_payload.
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=data)

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("获取软链接配置"),
            exec_ip=old_node,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_symbolic_link_payload.__name__,
            run_as_system_user=None,
            write_payload_var=AddSlaveContext.get_path_var_name(),
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("系统配置初始化"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_sysinit_payload.__name__,
            run_as_system_user=DBA_ROOT_USER,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("部署Oracle软件"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_install_trans_payload.__name__,
            run_as_system_user=None,
        )
    )

    install_instance_payload = (
        OracleActPayload.get_install_instance_via_cascading_trans_payload.__name__
        if via_cascading
        else OracleActPayload.get_install_instance_trans_payload.__name__
    )
    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("部署Oracle实例"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=install_instance_payload,
            run_as_system_user=None,
        )
    )
    return sub_pipeline.build_sub_process(sub_name=_("新备库软件与实例部署"))


def build_dg_and_duplicate_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    old_node: str,
    new_slave: str,
    cluster_master: str,
) -> SubBuilder:
    """
    配置 DataGuard 与 RMAN 复制子流程.
    包含: 配置 DG(via_statistic) -> RMAN 在线复制 -> 切换日志 -> 检查同步 ->
          实时应用日志 -> 切换日志 -> 检查同步 -> 启动动态监听.
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=data)

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("配置DataGuard"),
            exec_ip=old_node,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_config_data_guard_via_statistic_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("RMAN在线复制搭建备库"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_rman_duplicate_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("切换日志"),
            exec_ip=cluster_master,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_switch_log_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("检查同步状态"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_check_sync_status_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("实时应用日志"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_real_time_apply_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("切换日志"),
            exec_ip=cluster_master,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_switch_log_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("检查同步状态"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_check_sync_status_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("启动动态监听"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_start_listener_payload.__name__,
        )
    )
    return sub_pipeline.build_sub_process(sub_name=_("配置DataGuard与RMAN复制"))


def build_cascading_switch_to_master_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    old_master: str,
    new_slave: str,
    cluster_master: str,
) -> SubBuilder:
    """
    级联模式独有的子流程: 将新备库的同步源由 RMAN 拷贝源切换到原主.
    包含: 暂停同步 -> 在原主上配置 DataGuard -> 实时应用日志 -> 切换日志 -> 检查同步.
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=data)

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("暂停同步"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_pause_sync_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("配置DataGuard与原主同步"),
            exec_ip=old_master,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_config_data_guard_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("实时应用日志"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_real_time_apply_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("切换日志"),
            exec_ip=cluster_master,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_switch_log_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("检查同步状态"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_check_sync_status_payload.__name__,
        )
    )
    return sub_pipeline.build_sub_process(sub_name=_("切换同步源至原主"))


def build_new_machine_meta_kwargs(
    bk_cloud_id: int,
    bk_biz_id: int,
    new_ip: str,
    resource_spec: Dict,
    created_by: str,
    cluster_type: str,
) -> Dict:
    """
    构造 "写入元数据-新增机器" 的 kwargs.
    """
    return {
        "meta_func_name": OracleDBMeta.new_machine.__name__,
        "bk_cloud_id": bk_cloud_id,
        "bk_biz_id": int(bk_biz_id),
        "new_ip": new_ip,
        "resource_spec": resource_spec,
        "created_by": created_by,
        "cluster_type": cluster_type,
    }


def build_replace_common_sub_flow(
    root_id: str,
    data: Dict,
    cluster: Cluster,
    bk_cloud_id: int,
    old_node: str,
    new_slave: str,
    cluster_master: str,
    meta_kwargs: Dict,
    dns_role: str,
) -> SubBuilder:
    """
    replace_flag=True 时的公共替换子流程.
    包含: 人工确认 -> 切换日志 -> 检查同步 -> 写入元数据(替换) -> 替换域名映射 -> 人工确认 -> 关闭旧实例与监听.

    @param meta_kwargs 已经构造好的写元数据 kwargs (add_slave 需按集群类型区分,
                       cascading 固定为 replace_instance).
    @param dns_role    ClusterEntryRole.SLAVE_ENTRY.value 或 MASTER_ENTRY.value.
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=data)

    sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("切换日志"),
            exec_ip=cluster_master,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_switch_log_payload.__name__,
        )
    )

    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("检查同步状态"),
            exec_ip=new_slave,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_check_sync_status_payload.__name__,
        )
    )

    # 写入元数据 - 由调用方按集群类型决定 meta_func_name 与字段
    meta_act_name = (
        _("写入元数据-替换单节点实例")
        if meta_kwargs.get("meta_func_name") == OracleDBMeta.replace_single_instance.__name__
        else _("写入元数据-替换备库实例")
    )
    sub_pipeline.add_act(
        act_name=meta_act_name,
        act_component_code=OracleDBMetaComponent.code,
        kwargs=meta_kwargs,
    )

    dns = cluster.clusterentry_set.get(role=dns_role).entry
    sub_pipeline.add_act(
        act_name=_("[{}]替换域名映射".format(dns)),
        act_component_code=MySQLDnsManageComponent.code,
        kwargs=asdict(
            UpdateDnsRecordKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                old_instance=_("{}#{}".format(old_node, ManagerDefaultPort.ORACLE_PORT.value)),
                new_instance=_("{}#{}".format(new_slave, ManagerDefaultPort.ORACLE_PORT.value)),
                update_domain_name=dns,
            ),
        ),
    )

    sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
    sub_pipeline.add_act(
        **_make_oracle_act(
            act_name=_("关闭实例与监听"),
            exec_ip=old_node,
            bk_cloud_id=bk_cloud_id,
            payload_func_name=OracleActPayload.get_shutdown_payload.__name__,
        )
    )
    return sub_pipeline.build_sub_process(sub_name=_("替换旧实例"))


def build_replace_meta_kwargs_for_primary_standby(
    cluster_id: int, bk_biz_id: int, new_slave: str, old_node: str
) -> Dict:
    """OraclePrimaryStandby 集群替换备库实例的元数据 kwargs."""
    return {
        "meta_func_name": OracleDBMeta.replace_instance.__name__,
        "cluster_id": cluster_id,
        "bk_biz_id": int(bk_biz_id),
        "new_instance_ip": new_slave,
        "new_instance_port": ManagerDefaultPort.ORACLE_PORT.value,
        "old_instance_ip": old_node,
        "old_instance_port": ManagerDefaultPort.ORACLE_PORT.value,
    }


def build_replace_meta_kwargs_for_single_none(cluster_id: int, bk_biz_id: int, new_slave: str) -> Dict:
    """OracleSingleNone 集群替换单节点实例的元数据 kwargs."""
    return {
        "meta_func_name": OracleDBMeta.replace_single_instance.__name__,
        "cluster_id": cluster_id,
        "bk_biz_id": int(bk_biz_id),
        "new_ip": new_slave,
        "new_port": ManagerDefaultPort.ORACLE_PORT.value,
    }
