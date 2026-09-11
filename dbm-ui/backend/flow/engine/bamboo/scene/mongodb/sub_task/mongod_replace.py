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

from copy import deepcopy
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import MongoDBClusterRole, MongoDBInstanceType, MongoDBManagerUser
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mongodb.add_domain_to_dns import ExecAddDomainToDnsOperationComponent
from backend.flow.plugins.components.collections.mongodb.add_password_to_db import (
    ExecAddPasswordToDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.deferred_deinstall_ticket import (
    ExecDeferredDeInstallTicketOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.delete_domain_from_dns import (
    ExecDeleteDomainFromDnsOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.delete_password_from_db import (
    ExecDeletePasswordFromDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.instance_deinstall_ticket import (
    ExecInstanceDeInstallTicketOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.mongo_add_alarm_shield import MongoAddAlarmShieldComponent
from backend.flow.plugins.components.collections.mongodb.mongodb_capcity_chgs_meta import MongoDBCapcityMetaComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

# 活机：add → hide → remove；死机/故障：单次 MongoDReplace(sourceDown=True)
CUTOVER_ADD_THEN_REMOVE = "add_then_remove"
CUTOVER_REPLACE_WITH_SOURCE_DOWN = "replace_with_source_down"


def mongod_replace(
    root_id: str,
    ticket_data: Optional[Dict],
    sub_sub_kwargs: ActKwargs,
    cluster_role: str,
    info: dict,
    mongod_scale: bool,
    cutover_mode: Optional[str] = None,
    emit_deinstall_ticket: bool = False,
) -> SubBuilder:
    """
    mongod 替换叶子流程（整机替换 / 故障自愈共用）。

    cutover_mode:
      - add_then_remove: 活机路径（可 Pause 切主）
      - replace_with_source_down: 死机路径（peer 上 sourceDown 原子替换）
    默认：info.down=True → replace_with_source_down，否则 add_then_remove。
    emit_deinstall_ticket: 为 True 时在叶子内创延迟/实例下架单（分片自愈）；
      RS 整机路径由父流程处理旧机，保持 False。
    """

    if cutover_mode is None:
        cutover_mode = CUTOVER_REPLACE_WITH_SOURCE_DOWN if info.get("down") else CUTOVER_ADD_THEN_REMOVE

    sub_sub_get_kwargs = deepcopy(sub_sub_kwargs)
    sub_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    instance_role_exclude_backup = [
        InstanceRole.MONGO_M1.value,
        InstanceRole.MONGO_M2.value,
        InstanceRole.MONGO_M3.value,
        InstanceRole.MONGO_M4.value,
        InstanceRole.MONGO_M5.value,
        InstanceRole.MONGO_M6.value,
        InstanceRole.MONGO_M7.value,
        InstanceRole.MONGO_M8.value,
        InstanceRole.MONGO_M9.value,
        InstanceRole.MONGO_M10.value,
    ]
    new_node = info["target"]
    sub_sub_get_kwargs.payload["app"] = sub_sub_get_kwargs.payload["bk_app_abbr"]
    # 分片自愈可能已在外层设好 replicaset_info（cache/oplog）；RS 路径补 port
    if not getattr(sub_sub_get_kwargs, "replicaset_info", None):
        sub_sub_get_kwargs.replicaset_info = {}
    sub_sub_get_kwargs.replicaset_info["port"] = sub_sub_get_kwargs.db_instance["port"]

    admin_user = MongoDBManagerUser.DbaUser.value
    sub_sub_get_kwargs.payload["nodes"] = [
        {
            "ip": info["ip"],
            "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
            "port": sub_sub_get_kwargs.db_instance["port"],
            "bk_cloud_id": info["bk_cloud_id"],
            "instance_role": sub_sub_get_kwargs.db_instance.get("instance_role", ""),
            "role": MongoDBInstanceType.MongoD.value,
        }
    ]

    get_password = {"usernames": sub_sub_get_kwargs.manager_users}
    sub_sub_get_kwargs.payload["passwords"] = sub_sub_get_kwargs.get_password_from_db(info=get_password)["passwords"]
    admin_password = sub_sub_get_kwargs.payload["passwords"][admin_user]

    port = sub_sub_get_kwargs.db_instance["port"]
    step_down_info = {
        "exec_ip": "",
        "exec_bk_cloud_id": 0,
        "ip": "",
        "port": 0,
        "target_ip": info["ip"],
        "admin_user": admin_user,
        "admin_password": admin_password,
    }
    add_node_info = {
        "exec_ip": new_node["ip"],
        "exec_bk_cloud_id": new_node["bk_cloud_id"],
        "ip": "",
        "port": 0,
        "bk_cloud_id": info["bk_cloud_id"],
        "admin_user": admin_user,
        "admin_password": admin_password,
        "target": {"ip": new_node["ip"], "port": port, "priority": "", "hidden": ""},
    }
    instance_role = sub_sub_get_kwargs.db_instance.get("instance_role")
    if instance_role in instance_role_exclude_backup:
        add_node_info["target"]["priority"] = "1"
        add_node_info["target"]["hidden"] = "0"
    elif instance_role == InstanceRole.MONGO_BACKUP.value:
        add_node_info["target"]["priority"] = "0"
        add_node_info["target"]["hidden"] = "1"

    remove_node_info = {
        "exec_ip": new_node["ip"],
        "exec_bk_cloud_id": new_node["bk_cloud_id"],
        "ip": new_node["ip"],
        "port": port,
        "bk_cloud_id": info["bk_cloud_id"],
        "admin_user": admin_user,
        "admin_password": admin_password,
        "source": {"ip": info["ip"], "port": port},
    }
    nodes_info = [
        {
            "ip": info["ip"],
            "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
            "port": port,
            "bk_cloud_id": info["bk_cloud_id"],
        }
    ]
    node_info = nodes_info[0]

    if cluster_role:
        sub_sub_get_kwargs.cluster_type = ClusterType.MongoShardedCluster.value
        cluster_name = sub_sub_get_kwargs.db_instance["seg_range"]
        sub_sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoShardedCluster.value
        sub_sub_get_kwargs.payload["set_id"] = sub_sub_get_kwargs.db_instance["seg_range"]
        cluster_conf_name = sub_sub_get_kwargs.db_instance["cluster_name"]
        sub_sub_get_kwargs.payload["key_file"] = sub_sub_get_kwargs.get_cluster_key_file(
            cluster_name=cluster_conf_name
        )
        # 分片自愈：cache/oplog 可能已由调用方从 get_conf 写入；缺失时补齐
        if "cacheSizeGB" not in sub_sub_get_kwargs.replicaset_info:
            conf = sub_sub_get_kwargs.get_conf(cluster_name=cluster_conf_name)
            if cluster_role == MongoDBClusterRole.ConfigSvr.value:
                sub_sub_get_kwargs.replicaset_info["cacheSizeGB"] = conf["config_cacheSizeGB"]
                sub_sub_get_kwargs.replicaset_info["oplogSizeMB"] = conf["config_oplogSizeMB"]
            elif cluster_role == MongoDBClusterRole.ShardSvr.value:
                sub_sub_get_kwargs.replicaset_info["cacheSizeGB"] = conf["cacheSizeGB"]
                sub_sub_get_kwargs.replicaset_info["oplogSizeMB"] = conf["oplogSizeMB"]
        sub_sub_get_kwargs.payload["config_nodes"] = []
        sub_sub_get_kwargs.payload["shards_nodes"] = []
        sub_sub_get_kwargs.payload["mongos_nodes"] = []
        if cluster_role == MongoDBClusterRole.ConfigSvr.value:
            sub_sub_get_kwargs.payload["config_nodes"] = [
                {
                    "ip": info["ip"],
                    "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
                    "port": port,
                    "bk_cloud_id": info["bk_cloud_id"],
                }
            ]
        elif cluster_role == MongoDBClusterRole.ShardSvr.value:
            sub_sub_get_kwargs.payload["shards_nodes"].append(
                {
                    "nodes": [
                        {
                            "ip": info["ip"],
                            "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
                            "port": port,
                            "bk_cloud_id": info["bk_cloud_id"],
                        }
                    ]
                }
            )
    else:
        sub_sub_get_kwargs.cluster_type = ClusterType.MongoReplicaSet.value
        cluster_name = sub_sub_get_kwargs.db_instance["cluster_name"]
        sub_sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoReplicaSet.value
        sub_sub_get_kwargs.payload["set_id"] = cluster_name
        key_file = sub_sub_get_kwargs.get_cluster_key_file(cluster_name=cluster_name)
        sub_sub_get_kwargs.replicaset_info["key_file"] = key_file
        sub_sub_get_kwargs.payload["key_file"] = key_file

    sub_sub_get_kwargs.replicaset_info["set_id"] = cluster_name
    sub_sub_get_kwargs.replicaset_info["nodes"] = [
        {
            "ip": new_node["ip"],
            "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
            "bk_cloud_id": info["bk_cloud_id"],
            "port": port,
        }
    ]
    sub_sub_get_kwargs.payload["bk_cloud_id"] = info["bk_cloud_id"]

    # 安装新 mongod
    kwargs = sub_sub_get_kwargs.get_install_mongod_kwargs(node=new_node, cluster_role=cluster_role)
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-mongod安装-{}:{}".format(new_node["ip"], str(port))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    if cutover_mode == CUTOVER_REPLACE_WITH_SOURCE_DOWN:
        _append_source_down_cutover(
            sub_sub_pipeline=sub_sub_pipeline,
            sub_sub_get_kwargs=sub_sub_get_kwargs,
            cluster_role=cluster_role,
            info=info,
            new_node=new_node,
            port=port,
        )
    else:
        _append_add_then_remove_cutover(
            sub_sub_pipeline=sub_sub_pipeline,
            sub_sub_get_kwargs=sub_sub_get_kwargs,
            cluster_role=cluster_role,
            info=info,
            new_node=new_node,
            port=port,
            step_down_info=step_down_info,
            add_node_info=add_node_info,
            remove_node_info=remove_node_info,
            node_info=node_info,
        )

    # 密码
    kwargs = sub_sub_get_kwargs.get_add_password_to_db_kwargs(
        usernames=[
            MongoDBManagerUser.DbaUser.value,
            MongoDBManagerUser.AppDbaUser.value,
            MongoDBManagerUser.MonitorUser.value,
            MongoDBManagerUser.AppMonitorUser.value,
        ],
        info=sub_sub_get_kwargs.replicaset_info,
    )
    kwargs = sub_sub_get_kwargs.get_password_from_db(info=kwargs)
    kwargs["create"] = False
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-保存新实例的dba用户及额外管理用户密码"),
        act_component_code=ExecAddPasswordToDBOperationComponent.code,
        kwargs=kwargs,
    )
    kwargs = sub_sub_get_kwargs.get_delete_pwd_kwargs()
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-删除老实例的dba用户及额外管理用户密码"),
        act_component_code=ExecDeletePasswordFromDBOperationComponent.code,
        kwargs=kwargs,
    )

    if mongod_scale:
        kwargs = sub_sub_get_kwargs.get_scale_change_meta(info=info, instance=sub_sub_get_kwargs.db_instance)
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-mongod修改meta"), act_component_code=MongoDBCapcityMetaComponent.code, kwargs=kwargs
        )

    if emit_deinstall_ticket:
        nodes = sub_sub_get_kwargs.payload["nodes"]
        for node in nodes:
            node.setdefault("instance_type", MongoDBInstanceType.MongoD.value)
            node.setdefault("role", MongoDBInstanceType.MongoD.value)
            if sub_sub_get_kwargs.db_instance.get("cluster_id"):
                node.setdefault("cluster_id", sub_sub_get_kwargs.db_instance["cluster_id"])
            if sub_sub_get_kwargs.db_instance.get("seg_range"):
                node.setdefault("set_id", sub_sub_get_kwargs.db_instance["seg_range"])
        kwargs = {
            "infos": nodes,
            "creator": sub_sub_get_kwargs.payload["created_by"],
            "bk_biz_id": sub_sub_get_kwargs.payload["bk_biz_id"],
            "parent_ticket_id": ticket_data.get("uid") if ticket_data else None,
        }
        if info.get("down"):
            sub_sub_pipeline.add_act(
                act_name=_("MongoDB-延迟下架提单"),
                act_component_code=ExecDeferredDeInstallTicketOperationComponent.code,
                kwargs=kwargs,
            )
        else:
            sub_sub_pipeline.add_act(
                act_name=_("MongoDB-实例下架提单"),
                act_component_code=ExecInstanceDeInstallTicketOperationComponent.code,
                kwargs=kwargs,
            )

    return sub_sub_pipeline.build_sub_process(sub_name=_("MongoDB--mongod替换--{}:{}".format(info["ip"], str(port))))


def _append_source_down_cutover(
    *,
    sub_sub_pipeline,
    sub_sub_get_kwargs,
    cluster_role,
    info,
    new_node,
    port,
):
    """死机/故障：在 peer 上执行 MongoDReplace(sourceDown=True)。"""
    exec_host = sub_sub_get_kwargs.mongod_replace_get_exec_ip(
        cluster_type=sub_sub_get_kwargs.cluster_type,
        cluster_role=cluster_role or "",
        source_ip=info["ip"],
        instance=sub_sub_get_kwargs.db_instance,
    )
    if not exec_host:
        raise ValueError(
            "mongod replace sourceDown: no peer exec ip for source={} cluster_id={}".format(
                info["ip"], sub_sub_get_kwargs.db_instance.get("cluster_id")
            )
        )
    kwargs = sub_sub_get_kwargs.get_instance_replace_kwargs(exec_ip=exec_host["ip"], info=info, source_down=True)
    # get_instance_replace_kwargs 用 exec_ip 字符串；云区域以 peer 为准
    kwargs["bk_cloud_id"] = exec_host.get("bk_cloud_id", info["bk_cloud_id"])
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-mongod替换(sourceDown)-{}:{}".format(info["ip"], str(port))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )
    if not cluster_role:
        kwargs = sub_sub_get_kwargs.get_add_domain_to_dns_kwargs(cluster=False)
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-添加新实例的domain到dns"),
            act_component_code=ExecAddDomainToDnsOperationComponent.code,
            kwargs=kwargs,
        )
        kwargs = sub_sub_get_kwargs.get_delete_domain_kwargs()
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-删除老实例的domain指向"),
            act_component_code=ExecDeleteDomainFromDnsOperationComponent.code,
            kwargs=kwargs,
        )
    act_name = _("MongoDB-mongod下架前屏蔽告警-{}:{}".format(info["ip"], str(port)))
    kwargs = sub_sub_get_kwargs.get_add_alarm_shield_kwargs(ip=info["ip"], port=port, description=act_name)
    sub_sub_pipeline.add_act(
        act_name=act_name,
        act_component_code=MongoAddAlarmShieldComponent.code,
        kwargs=kwargs,
    )


def _append_add_then_remove_cutover(
    *,
    sub_sub_pipeline,
    sub_sub_get_kwargs,
    cluster_role,
    info,
    new_node,
    port,
    step_down_info,
    add_node_info,
    remove_node_info,
    node_info,
):
    """活机：可 Pause 切主 → add → DNS → shield → hide → remove。"""
    exec_ip = new_node["ip"]
    exec_ip_bk_cloud_id = new_node["bk_cloud_id"]

    if sub_sub_get_kwargs.db_instance.get("role_status") == "primary":
        sub_sub_pipeline.add_act(act_name=_("primary切换-人工确认"), act_component_code=PauseComponent.code, kwargs={})
        step_down_info["exec_ip"] = exec_ip
        step_down_info["exec_bk_cloud_id"] = exec_ip_bk_cloud_id
        step_down_info["ip"] = sub_sub_get_kwargs.db_instance["primary_ip"]
        step_down_info["port"] = sub_sub_get_kwargs.db_instance["primary_port"]
        kwargs = sub_sub_get_kwargs.get_step_down_kwargs(info=step_down_info)
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-主备切换-{}:{}".format(info["ip"], str(port))),
            act_component_code=ExecuteDBActuatorJobComponent.code,
            kwargs=kwargs,
        )

    add_node_info["ip"] = sub_sub_get_kwargs.db_instance["primary_ip"]
    add_node_info["port"] = sub_sub_get_kwargs.db_instance["primary_port"]
    kwargs = sub_sub_get_kwargs.get_res_replace_add_node_kwargs(info=add_node_info)
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-添加node-{}:{}".format(new_node["ip"], str(port))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    if not cluster_role:
        kwargs = sub_sub_get_kwargs.get_add_domain_to_dns_kwargs(cluster=False)
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-添加新实例的domain到dns"),
            act_component_code=ExecAddDomainToDnsOperationComponent.code,
            kwargs=kwargs,
        )
        kwargs = sub_sub_get_kwargs.get_delete_domain_kwargs()
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-删除老实例的domain指向"),
            act_component_code=ExecDeleteDomainFromDnsOperationComponent.code,
            kwargs=kwargs,
        )

    act_name = _("MongoDB-mongod下架前屏蔽告警-{}:{}".format(info["ip"], str(port)))
    kwargs = sub_sub_get_kwargs.get_add_alarm_shield_kwargs(ip=info["ip"], port=port, description=act_name)
    sub_sub_pipeline.add_act(
        act_name=act_name,
        act_component_code=MongoAddAlarmShieldComponent.code,
        kwargs=kwargs,
    )
    kwargs = sub_sub_get_kwargs.get_mongod_hidden_kwargs(info=info, hidden=True, port=port)
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-mongod下架前隐藏-{}:{}".format(info["ip"], str(port))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )
    kwargs = sub_sub_get_kwargs.get_reduce_node_kwargs(info=remove_node_info)
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-移除node-{}:{}".format(node_info["ip"], str(port))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )
