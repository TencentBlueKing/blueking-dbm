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

from django.utils.translation import ugettext as _

from backend.db_meta import api
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import MongoDBInstanceType, MongoDBManagerUser
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import install_plugin
from backend.flow.plugins.components.collections.mongodb.add_domain_to_dns import ExecAddDomainToDnsOperationComponent
from backend.flow.plugins.components.collections.mongodb.add_password_to_db import (
    ExecAddPasswordToDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.delete_password_from_db import (
    ExecDeletePasswordFromDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.instance_deinstall_ticket import (
    ExecInstanceDeInstallTicketOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.mongodb_cmr_4_meta import CMRMongoDBMetaComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.plugins.components.collections.name_service.name_service import ExecNameServiceOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def mongos_autofix(root_id: str, ticket_data: Optional[Dict], sub_sub_kwargs: ActKwargs, info: dict) -> SubBuilder:
    """
    mongos自愈流程
    """

    # 获取变量
    sub_sub_get_kwargs = deepcopy(sub_sub_kwargs)

    # 创建子流程
    sub_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取参数
    sub_sub_get_kwargs.mongos_info = {}
    sub_sub_get_kwargs.payload["config_nodes"] = []
    sub_sub_get_kwargs.payload["shards_nodes"] = []
    sub_sub_get_kwargs.payload["app"] = sub_sub_get_kwargs.payload["bk_app_abbr"]
    sub_sub_get_kwargs.mongos_info["port"] = sub_sub_get_kwargs.db_instance["port"]
    cluster_id = sub_sub_get_kwargs.db_instance["cluster_id"]
    sub_sub_get_kwargs.mongos_info["conf_set_id"] = sub_sub_get_kwargs.get_config_set_name_replace(
        cluster_id=cluster_id
    )
    sub_sub_get_kwargs.cluster_type = ClusterType.MongoShardedCluster.value
    # 获取db版本
    db_version = sub_sub_get_kwargs.payload["db_version"]
    # db大版本
    sub_sub_get_kwargs.db_main_version = str(db_version.split("-")[1].split(".")[0])
    # db发行版本
    sub_sub_get_kwargs.db_release_version = db_version
    # db发行
    sub_sub_get_kwargs.db_release = db_version.split("-")[0]
    # db版本
    sub_sub_get_kwargs.payload["db_version"] = db_version.split("-")[1]

    sub_sub_get_kwargs.payload["key_file"] = sub_sub_get_kwargs.get_conf(
        cluster_name=sub_sub_get_kwargs.db_instance["cluster_name"]
    )["key_file"]
    node = info["target"]
    node["cluster_id"] = cluster_id
    sub_sub_get_kwargs.payload["mongos"] = {}
    sub_sub_get_kwargs.payload["mongos"]["nodes"] = [
        {
            "ip": node["ip"],
            "domain": sub_sub_get_kwargs.db_instance["domain"],
            "bk_cloud_id": info["bk_cloud_id"],
            "port": sub_sub_get_kwargs.db_instance["port"],
        }
    ]
    sub_sub_get_kwargs.payload["mongos"]["port"] = sub_sub_get_kwargs.db_instance["port"]
    sub_sub_get_kwargs.payload["mongos"]["domain"] = sub_sub_get_kwargs.db_instance["domain"]
    sub_sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoShardedCluster.value
    sub_sub_get_kwargs.payload["mongos_nodes"] = [
        {
            "ip": info["ip"],
            "domain": sub_sub_get_kwargs.db_instance["domain"],
            "port": sub_sub_get_kwargs.db_instance["port"],
            "bk_cloud_id": info["bk_cloud_id"],
        }
    ]
    sub_sub_get_kwargs.payload["nodes"] = [
        {
            "ip": info["ip"],
            "domain": sub_sub_get_kwargs.db_instance["domain"],
            "port": sub_sub_get_kwargs.db_instance["port"],
            "bk_cloud_id": info["bk_cloud_id"],
            "role": MongoDBInstanceType.MongoS.value,
        }
    ]
    sub_sub_get_kwargs.payload["bk_cloud_id"] = info["bk_cloud_id"]
    sub_sub_get_kwargs.payload["set_id"] = sub_sub_get_kwargs.db_instance["cluster_name"]

    # 判断是否有clb
    clb = False
    if (
        ClusterEntryType.CLB.value
        in api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id=cluster_id)[0]["clusterentry_set"]
    ):
        clb = True
    # dbha已做clb解绑，dns删除
    # # 删除clb中绑定的老ip
    # if clb:
    #     kwargs = {
    #         "name_service_operation_type": "clb_deregister_part_target",
    #         "creator": sub_sub_get_kwargs.payload["creator"],
    #         "cluster_id": cluster_id,
    #         "ips": ["{}:{}".format(info["ip"], str(sub_sub_get_kwargs.db_instance["port"]))],
    #     }
    #     sub_sub_pipeline.add_act(
    #         act_name=_("MongoDB-clb解绑故障ip"),
    #         act_component_code=ExecNameServiceOperationComponent.code,
    #         kwargs=kwargs,
    #     )
    #
    # # 删除老的dns
    # kwargs = sub_sub_get_kwargs.get_delete_domain_kwargs()
    # sub_sub_pipeline.add_act(
    #     act_name=_("MongoDB-删除老实例的domain指向"),
    #     act_component_code=ExecDeleteDomainFromDnsOperationComponent.code,
    #     kwargs=kwargs,
    # )

    # 获取信息
    sub_sub_get_kwargs.get_host_cluster_autofix(info=info)

    # 安装蓝鲸插件
    install_plugin(pipeline=sub_sub_pipeline, get_kwargs=sub_sub_get_kwargs, new_cluster=False)

    # 介质下发
    kwargs = sub_sub_get_kwargs.get_send_media_kwargs(media_type="all")
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 创建原子任务执行目录
    kwargs = sub_sub_get_kwargs.get_create_dir_kwargs()
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-创建原子任务执行目录"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 机器初始化
    kwargs = sub_sub_get_kwargs.get_os_init_kwargs()
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-机器初始化"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # mognos安装
    kwargs = sub_sub_get_kwargs.get_install_mongos_kwargs(node=node, replace=True)
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-mongos安装-{}:{}".format(node["ip"], str(sub_sub_get_kwargs.db_instance["port"]))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    # mongos修改db_meta数据
    cluster_mongos = {}
    cluster_mongos["mongos"] = [info]
    cluster_mongos["db_type"] = "mongos"
    cluster_mongos["created_by"] = sub_sub_get_kwargs.payload.get("created_by")
    cluster_mongos["bk_biz_id"] = sub_sub_get_kwargs.payload.get("bk_biz_id")
    kwargs = sub_sub_get_kwargs.get_change_meta_replace_kwargs(info=cluster_mongos, instance={})
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-mongos修改meta"), act_component_code=CMRMongoDBMetaComponent.code, kwargs=kwargs
    )

    # clb绑定新ip
    if clb:
        kwargs = {
            "name_service_operation_type": "clb_register_part_target",
            "creator": sub_sub_get_kwargs.payload["created_by"],
            "cluster_id": cluster_id,
            "ips": ["{}:{}".format(node["ip"], str(sub_sub_get_kwargs.db_instance["port"]))],
        }
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-clb绑定新ip"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=kwargs,
        )

    # 添加新的dns
    kwargs = sub_sub_get_kwargs.get_add_domain_to_dns_kwargs(cluster=True)
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-添加新实例的domain到dns"),
        act_component_code=ExecAddDomainToDnsOperationComponent.code,
        kwargs=kwargs,
    )
    # 密码服务修改密码
    # 添加新实例密码
    kwargs = sub_sub_get_kwargs.get_add_password_to_db_kwargs(
        usernames=[
            MongoDBManagerUser.DbaUser.value,
            MongoDBManagerUser.AppDbaUser.value,
            MongoDBManagerUser.MonitorUser.value,
            MongoDBManagerUser.AppMonitorUser.value,
        ],
        info=sub_sub_get_kwargs.payload["mongos"],
    )
    # 用户获取密码
    kwargs = sub_sub_get_kwargs.get_password_from_db(info=kwargs)
    # 是否是部署单据
    kwargs["create"] = False
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-保存新实例的dba用户及额外管理用户密码"),
        act_component_code=ExecAddPasswordToDBOperationComponent.code,
        kwargs=kwargs,
    )
    # 删除老实例密码
    kwargs = sub_sub_get_kwargs.get_delete_pwd_kwargs()
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-删除老实例的dba用户及额外管理用户密码"),
        act_component_code=ExecDeletePasswordFromDBOperationComponent.code,
        kwargs=kwargs,
    )

    # 老实例提下架单
    kwargs = {
        "infos": sub_sub_get_kwargs.payload["nodes"],
        "creator": sub_sub_get_kwargs.payload["created_by"],
        "bk_biz_id": sub_sub_get_kwargs.payload["bk_biz_id"],
    }
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-实例下架提单"),
        act_component_code=ExecInstanceDeInstallTicketOperationComponent.code,
        kwargs=kwargs,
    )

    return sub_sub_pipeline.build_sub_process(
        sub_name=_("MongoDB--mongos自愈--{}:{}".format(info["ip"], str(sub_sub_get_kwargs.db_instance["port"])))
    )
