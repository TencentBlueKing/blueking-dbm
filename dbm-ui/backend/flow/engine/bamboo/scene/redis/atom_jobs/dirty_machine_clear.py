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
from typing import Dict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums.machine_type import MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_services.redis.util import is_predixy_proxy_type
from backend.flow.consts import (
    DEFAULT_MONITOR_TIME,
    DEFAULT_REDIS_SYSTEM_CMDS,
    DBActuatorTypeEnum,
    RedisActuatorActionEnum,
)
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


def DirtyRedisMachineClear(root_id, ticket_data, sub_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    清理redis机器的原子任务
    Args:
        param (Dict): {
            "ip":"a.a.a.a",
            "force":True,
            "only_clear_dbmeta":True,
        }
    """
    bk_biz_id = ticket_data["bk_biz_id"]
    bk_cloud_id = ticket_data["bk_cloud_id"]
    ip = param["ip"]
    force = param.get("force", False)
    only_clear_dbmeta = param.get("only_clear_dbmeta", False)
    ports = [row.port for row in StorageInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)]
    storage_inst = StorageInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id).first()
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    act_kwargs = deepcopy(sub_kwargs)
    act_kwargs.cluster = {}
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_dbmon()

    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )

    if only_clear_dbmeta is False:
        act_kwargs.exec_ip = ip
        sub_pipeline.add_act(
            act_name=_("{}-下发介质包").format(ip),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(act_kwargs),
        )

        #  监听请求。集群是先关闭再下架，所以理论上这里是没请求才对
        act_kwargs.exec_ip = ip
        act_kwargs.cluster = {}
        act_kwargs.cluster["exec_ip"] = ip
        act_kwargs.cluster["ports"] = ports
        act_kwargs.cluster["monitor_time_ms"] = DEFAULT_MONITOR_TIME
        act_kwargs.cluster["ignore_req"] = force
        act_kwargs.cluster["ignore_keys"] = DEFAULT_REDIS_SYSTEM_CMDS
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_capturer_4_scene.__name__
        sub_pipeline.add_act(
            act_name=_("请求检查-{}").format(ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 停监控
        act_kwargs.cluster["servers"] = [
            {
                "bk_biz_id": str(bk_biz_id),
                "bk_cloud_id": bk_cloud_id,
            }
        ]
        act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
        sub_pipeline.add_act(
            act_name=_("卸载监控-{}").format(ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 干掉非活跃链接
        act_kwargs.exec_ip = ip
        act_kwargs.cluster["exec_ip"] = ip
        act_kwargs.cluster["instances"] = [{"ip": ip, "port": p} for p in ports]
        act_kwargs.cluster["idle_time"] = 600
        act_kwargs.cluster["ignore_kill"] = force
        act_kwargs.cluster["cluster_type"] = storage_inst.cluster_type
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_killconn_4_scene.__name__
        sub_pipeline.add_act(
            act_name=_("干掉非活跃链接-{}").format(ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 下架实例
        act_kwargs.exec_ip = ip
        act_kwargs.cluster["exec_ip"] = ip
        act_kwargs.cluster["force_shutdown"] = force
        act_kwargs.cluster["shutdown_ports"] = ports
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_shutdown_4_scene.__name__
        sub_pipeline.add_act(
            act_name=_("下架实例-{}").format(ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

    # 清理元数据 @这里如果是master, 需要等slave 清理后才能执行
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.instances_uninstall.__name__
    act_kwargs.cluster["ports"] = ports
    act_kwargs.cluster["ip"] = ip
    act_kwargs.cluster["bk_cloud_id"] = bk_cloud_id
    act_kwargs.cluster["created_by"] = ticket_data["created_by"]
    sub_pipeline.add_act(
        act_name=_("清理元数据-{}").format(ip),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(act_kwargs),
    )

    return sub_pipeline.build_sub_process(sub_name=_("Redis-{}-下架原子任务").format(ip))


def DirtyProxyMachineClear(root_id, ticket_data, sub_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    清理proxy机器的原子任务
    Args:
        param (Dict): {
            "ip":"a.a.a.a",
            "force":True,
            "only_clear_dbmeta":True,
        }
    """
    ip = param["ip"]
    # bk_biz_id = ticket_data["bk_biz_id"]
    bk_cloud_id = ticket_data["bk_cloud_id"]
    # force = param.get("force", False)
    only_clear_dbmeta = param.get("only_clear_dbmeta", False)
    # ports = [row.port for row in ProxyInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)]
    proxy_inst = ProxyInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id).first()
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    act_kwargs = deepcopy(sub_kwargs)
    act_kwargs.cluster = {"cluster_type": proxy_inst.cluster_type}
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_dbmon()

    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )
    if is_predixy_proxy_type(proxy_inst.cluster_type):
        act_kwargs.cluster["machine_type"] = MachineType.PREDIXY.value
    else:
        act_kwargs.cluster["machine_type"] = MachineType.TWEMPROXY.value

    if only_clear_dbmeta is False:
        # 下发介质包
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs.file_list = trans_files.redis_cluster_apply_proxy(proxy_inst.cluster_type)
        act_kwargs.exec_ip = ip
        sub_pipeline.add_act(
            act_name=_("Proxy-{}-下发介质包").format(ip),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 停监控
        act_kwargs.cluster["servers"] = [
            {
                "bk_biz_id": str(proxy_inst.bk_biz_id),
                "bk_cloud_id": proxy_inst.machine.bk_cloud_id,
            }
        ]
        act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
        sub_pipeline.add_act(
            act_name=_("卸载监控-{}").format(ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 暂停进程
        act_kwargs.exec_ip = ip
        act_kwargs.cluster = {
            "operate": DBActuatorTypeEnum.Proxy.value + "_" + RedisActuatorActionEnum.Shutdown.value,
            "port": proxy_inst.port,
            "ip": ip,
            "cluster_type": proxy_inst.cluster_type,
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.proxy_operate_payload.__name__
        sub_pipeline.add_act(
            act_name=_("Proxy-{}-卸载实例").format(ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
    # 删除元数据
    act_kwargs.cluster = {
        "bk_cloud_id": bk_cloud_id,
        "proxy_ips": [ip],
        "meta_func_name": RedisDBMeta.clear_dirty_proxy_dbmetas.__name__,
    }
    sub_pipeline.add_act(
        act_name=_("Proxy-{}-删除元数据").format(ip),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(act_kwargs),
    )

    return sub_pipeline.build_sub_process(sub_name=_("Proxy-{}-卸载原子任务").format(ip))
