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
import logging.config
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import AppCache
from backend.flow.consts import SyncType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.redis_trans_files import RedisBackupFileTransComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs

logger = logging.getLogger("flow")


def RedisMakeSyncAtomJob(root_id, ticket_data, sub_kwargs: ActKwargs, params: Dict) -> SubBuilder:
    """### SubBuilder: Redis建Sync关系
    #### 支持多种同步关系建立 包含 MMS,MS,SMS
    params (Dict): {
        "sync_type": (ms,mms,sms)
        "origin_1": "x.12.1.2",   # old_master
        "origin_2": "x.12.1.2", # old_slave
        "sync_dst1":"1.1.1.x",    # new_master
        "sync_dst2":"2.2.x.1",    # new_slave
        "ins_link":[{"origin_1":"port","origin_2":"port","sync_dst1":"port","sync_dst2":"port"}],
    }
    """
    act_kwargs = deepcopy(sub_kwargs)
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    ins_sync_type = params["sync_type"]
    app = AppCache.get_app_attr(act_kwargs.cluster["bk_biz_id"], "db_app_abbr")
    app_name = AppCache.get_app_attr(act_kwargs.cluster["bk_biz_id"], "bk_biz_name")

    # 下发介质包
    exec_ip = [params["origin_1"], params["sync_dst1"]]
    if ins_sync_type in [SyncType.SYNC_MMS, SyncType.SYNC_SMS]:
        exec_ip.append(params["sync_dst2"])
    act_kwargs.exec_ip = exec_ip
    act_kwargs.file_list = GetFileList(db_type=DBType.Redis).redis_actuator()
    sub_pipeline.add_act(
        act_name=_("Redis-{}-下发介质包").format(exec_ip),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 停dbmon
    exec_ip = [params["sync_dst1"]]
    if ins_sync_type in [SyncType.SYNC_MMS, SyncType.SYNC_SMS]:
        exec_ip.append(params["sync_dst2"])
    act_kwargs.exec_ip = exec_ip
    act_kwargs.cluster["servers"] = [
        {
            "bk_biz_id": str(act_kwargs.cluster["bk_biz_id"]),
            "bk_cloud_id": int(act_kwargs.cluster["bk_cloud_id"]),
            "server_ports": [],
            "cluster_domain": act_kwargs.cluster["immute_domain"],
        }
    ]
    act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-卸载dbmon").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 建立Sync关系
    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance:
        RedisCacheMakeSyncAtomJob(sub_pipeline=sub_pipeline, act_kwargs=act_kwargs, params=params)
        #  sub_pipeline = RedisCacheMakeSyncAtomJob(sub_pipeline=sub_pipeline, act_kwargs=act_kwargs, params=params)
    elif act_kwargs.cluster["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance:
        RedisSSDMakeSyncAtomJob(sub_pipeline=sub_pipeline, act_kwargs=act_kwargs, params=params)
    else:
        raise Exception("unsupport cluster type 4 make sync {}".format(params["cluster_type"]))

    # 拉起dbmon
    exec_ip, server_ports = [params["sync_dst1"]], []
    for sync_link in params["ins_link"]:
        server_ports.append(int(sync_link["sync_dst1"]))
    act_kwargs.exec_ip = exec_ip
    act_kwargs.cluster["servers"] = [
        {
            "app": app,
            "app_name": app_name,
            "bk_biz_id": str(act_kwargs.cluster["bk_biz_id"]),
            "bk_cloud_id": int(act_kwargs.cluster["bk_cloud_id"]),
            "meta_role": InstanceRole.REDIS_SLAVE.value,  # 可能是master/slave 角色
            "server_ip": params["sync_dst1"],
            "server_ports": server_ports,
            "cluster_type": act_kwargs.cluster["cluster_type"],
            "cluster_domain": act_kwargs.cluster["immute_domain"],
        }
    ]

    if ins_sync_type in [SyncType.SYNC_MMS, SyncType.SYNC_SMS]:
        act_kwargs.cluster["servers"][0]["meta_role"] = InstanceRole.REDIS_MASTER.value
    act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-拉起dbmon").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 通常是slave 角色
    if ins_sync_type in [SyncType.SYNC_MMS, SyncType.SYNC_SMS]:
        exec_ip, server_ports = [params["sync_dst2"]], []
        act_kwargs.exec_ip = exec_ip
        for sync_link in params["ins_link"]:
            server_ports.append(int(sync_link["sync_dst2"]))
        act_kwargs.cluster["servers"][0]["meta_role"] = InstanceRole.REDIS_SLAVE.value
        act_kwargs.cluster["servers"][0]["server_ip"] = params["sync_dst2"]
        act_kwargs.cluster["servers"][0]["server_ports"] = server_ports
        sub_pipeline.add_act(
            act_name=_("Redis-{}-拉起dbmon").format(exec_ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

    return sub_pipeline.build_sub_process(sub_name=_("Redis-{}-创建同步关系原子任务").format(exec_ip))


def RedisCacheMakeSyncAtomJob(sub_pipeline: SubBuilder, act_kwargs: ActKwargs, params: Dict) -> SubBuilder:
    """
    ## 支持直接 内核层解决数据传输 方式做数据同步
    """
    # 建立主从关系
    act_kwargs.cluster["ms_link"] = []
    data_to = params["sync_dst1"]
    data_from = "origin_1"  # 重建热备
    if params["sync_type"] == SyncType.SYNC_SMS.value:
        data_from = "origin_2"  # 替换Master
    for sync_direct in params["ins_link"]:
        act_kwargs.cluster["ms_link"].append(
            {
                "master_ip": params[data_from],
                "master_port": sync_direct[data_from],
                "slave_ip": data_to,
                "slave_port": sync_direct["sync_dst1"],
            }
        )
    act_kwargs.exec_ip = data_to
    act_kwargs.get_redis_payload_func = RedisActPayload.get_redis_batch_replicate.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-建立主从关系".format(data_to)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    if params["sync_type"] in [SyncType.SYNC_MMS, SyncType.SYNC_SMS]:
        act_kwargs.cluster["ms_link"] = []
        data_to = params["sync_dst2"]
        for sync_direct in params["ins_link"]:
            act_kwargs.cluster["ms_link"].append(
                {
                    "master_ip": params["sync_dst1"],
                    "master_port": sync_direct["sync_dst1"],
                    "slave_ip": data_to,
                    "slave_port": sync_direct["sync_dst2"],
                }
            )
        act_kwargs.exec_ip = data_to
        act_kwargs.get_redis_payload_func = RedisActPayload.get_redis_batch_replicate.__name__
        sub_pipeline.add_act(
            act_name=_("Redis-{}-建立主从关系".format(data_to)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
    return sub_pipeline


def RedisSSDMakeSyncAtomJob(sub_pipeline: SubBuilder, act_kwargs: ActKwargs, params: Dict) -> SubBuilder:
    """
    ## 支持需要使用 全备数据+增量数据的方式做同步
    SubBuilder: RedisSSD建Sync关系
    dbs/bk-dbactuator-redis/blob/master/example/redis_backup.example.md
    dbs/bk-dbactuator-redis/blob/master/example/tendisssd_dr_restore.examle.md

    M->S
    M->M2->S2 (M2,S2:实际上没有主从关系,最后需要写入主从关系)
    2. Actor: Master上 发起备份 ;这里需要解析输出结果
    3. 调用GSE 远程传输文件 (from master to slave)
    4. Actor: restore dr 任务
    """
    # 创建同步关系
    data_from = "origin_1"
    data_to = "sync_dst1"
    backup_and_restore(sub_pipeline, act_kwargs, params, data_from, data_to)

    if params["sync_type"] in [SyncType.SYNC_MMS, SyncType.SYNC_SMS]:
        data_from = "origin_1"
        data_to = "sync_dst1"
        backup_and_restore(sub_pipeline, act_kwargs, params, data_from, data_to)

    return sub_pipeline


def backup_and_restore(
    sub_pipeline: SubBuilder, act_kwargs: ActKwargs, params: Dict, data_from: str, data_to: str
) -> SubBuilder:
    """### 封装 备份、远程传输文件、以及恢复实例 TODO"""
    #     params (Dict): {
    #     "sync_type": (ms,mms,sms)
    #     "origin_1": "x.12.1.2",   # old_master
    #     "origin_2": "x.12.1.2", # old_slave
    #     "sync_dst1":"1.1.1.x",    # new_master
    #     "sync_dst2":"2.2.x.1",    # new_slave
    #     "ins_link":[{"origin_1":"port","origin_2":"port","sync_dst1":"port","sync_dst2":"port"}],
    # }

    # 发起备份
    act_kwargs.exec_ip = params[data_from]
    act_kwargs.cluster["backup_host"] = params[data_from]
    act_kwargs.cluster["backup_instances"] = []
    act_kwargs.cluster["ssd_log_count"] = {"log-count": 6600000, "slave-log-keep-count": 6600000}
    act_kwargs.cluster["domain_name"] = act_kwargs.cluster["immute_domain"]
    for sync_direct in params["ins_link"]:
        act_kwargs.cluster["backup_instances"].append(int(sync_direct[data_from]))
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_backup_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-发起备份").format(params[data_from]),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
        write_payload_var="tendis_backup_info",
    )

    # 远程传输文件
    act_kwargs.cluster["soruce_ip"] = params[data_from]
    act_kwargs.cluster["target_ip"] = params[data_to]
    act_kwargs.exec_ip = params[data_to]
    sub_pipeline.add_act(
        act_name=_("Redis-{}==>>{}-发送备份文件").format(params[data_from], params[data_to]),
        act_component_code=RedisBackupFileTransComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 恢复备份
    act_kwargs.cluster["master_ip"] = params[data_from]
    act_kwargs.cluster["slave_ip"] = params[data_to]
    act_kwargs.cluster["slave_ports"] = [int(sync_direct[data_from]) for sync_direct in params["ins_link"]]
    act_kwargs.cluster["master_ports"] = [int(sync_direct[data_to]) for sync_direct in params["ins_link"]]
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_tendisssd_dr_restore_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-恢复备份").format(params[data_to]),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    return sub_pipeline
