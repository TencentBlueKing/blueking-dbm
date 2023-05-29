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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache
from backend.flow.consts import DEFAULT_REDIS_START_PORT, SyncType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisApplyContext

logger = logging.getLogger("flow")


def RedisMakeSyncAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, params: Dict) -> SubBuilder:
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
        act_name=_("Redis-101-{}-下发介质包").format(exec_ip),
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
        act_name=_("Redis-102-{}-卸载dbmon").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 建立Sync关系
    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance:
        RedisCacheMakeSyncAtomJob(sub_pipeline=sub_pipeline, act_kwargs=act_kwargs, params=params)
        #  sub_pipeline = RedisCacheMakeSyncAtomJob(sub_pipeline=sub_pipeline, act_kwargs=act_kwargs, params=params)
    elif act_kwargs.cluster["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance:
        # TODO 具体方案再定
        RedisSSDMakeSyncAtomJob(sub_pipeline=sub_pipeline, act_kwargs=act_kwargs, params=params)
    else:
        raise Exception("unsupport cluster type 4 make sync {}".format(params["cluster_type"]))

    # 拉起dbmon
    exec_ip = [params["sync_dst1"]]
    server_ports = []
    for sync_link in params["ins_link"]:
        server_ports.append(int(sync_link["sync_dst1"].split(IP_PORT_DIVIDER)[1]))
    if ins_sync_type in [SyncType.SYNC_MMS, SyncType.SYNC_SMS]:
        exec_ip.append(params["sync_dst2"])
    act_kwargs.exec_ip = exec_ip
    act_kwargs.cluster["servers"] = [
        {
            "app": app,
            "app_name": app_name,
            "bk_biz_id": str(act_kwargs.cluster["bk_biz_id"]),
            "bk_cloud_id": int(act_kwargs.cluster["bk_cloud_id"]),
            "server_ports": server_ports,
            "cluster_type": act_kwargs.cluster["cluster_type"],
            "cluster_domain": act_kwargs.cluster["immute_domain"],
        }
    ]
    act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
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
        act_name=_("Redis-103-{}-建立主从关系".format(data_to)),
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
            act_name=_("Redis-104-{}-建立主从关系".format(data_to)),
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
    act_kwargs.cluster["ms_link"] = []
    for sync_direct in params["ins_link"]:
        data_from = "origin_1"
        data_to = params["sync_dst1"]
        act_kwargs.cluster["ms_link"].append(
            {
                "master_ip": params[data_from],
                "master_port": sync_direct[data_from],
                "slave_ip": data_to,
                "slave_port": sync_direct["sync_dst1"],
            }
        )
        backup_and_restore(sub_pipeline, act_kwargs, params)
        if params["sync_type"] in [SyncType.SYNC_MMS, SyncType.SYNC_SMS]:
            data_from = "sync_dst1"
            data_to = params["sync_dst2"]
            act_kwargs.cluster["ms_link"].append(
                {
                    "master_ip": params[data_from],
                    "master_port": sync_direct[data_from],
                    "slave_ip": data_to,
                    "slave_port": sync_direct["sync_dst2"],
                }
            )
            backup_and_restore(sub_pipeline, act_kwargs, params)

    return sub_pipeline


# def make_sync_param(srcd, dst: str, params: Dict) -> Dict:
#     return {
#         "master_ip": srcd.split(IP_PORT_DIVIDER)[0],
#         "master_port": srcd.split(IP_PORT_DIVIDER)[1],
#         "slave_ip": dst.split(IP_PORT_DIVIDER)[0],
#         "slave_port": dst.split(IP_PORT_DIVIDER)[1],
#     }


def backup_and_restore(
    sub_pipeline: SubBuilder,
    act_kwargs: ActKwargs,
    params: Dict,
) -> SubBuilder:
    """### 封装 备份、远程传输文件、以及恢复实例 TODO"""
    # 发起备份
    act_kwargs.exec_ip = params["slave_ip"]
    act_kwargs.cluster["exec_ip"] = params["slave_ip"]
    act_kwargs.cluster["backup_instance"] = params["slave_port"]
    act_kwargs.cluster["ssd_log_count"] = {"log-count": 6600000, "slave-log-keep-count": 6600000}
    act_kwargs.cluster["bk_biz_id"] = act_kwargs.cluster["bk_biz_id"]
    act_kwargs.cluster["domain_name"] = act_kwargs.cluster["immute_domain"]
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_backup_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-103-{}-发起备份").format(params["slave_ip"]),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 远程传输文件

    # 恢复备份
