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
import logging
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import AppCache
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


def RedisDbmonAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    ### SubBuilder: Redis安装 dbmon 原子人物

    Args:
        param (Dict): {
            "ip":"1.1.1.x",
            "ports":[],
            "meta_role":"redis_slave",
            "cluster_type":"",
            "immute_domain":"",
        }
    """
    app = AppCache.get_app_attr(ticket_data["bk_biz_id"], "db_app_abbr")
    app_name = AppCache.get_app_attr(ticket_data["bk_biz_id"], "bk_biz_name")

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    exec_ip = param["ip"]

    # 下发介质包
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_dbmon()
    act_kwargs.exec_ip = exec_ip
    sub_pipeline.add_act(
        act_name=_("Redis-201-{}-下发介质包").format(exec_ip),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 部署bkdbmon
    act_kwargs.cluster["servers"] = [
        {
            "app": app,
            "app_name": app_name,
            "bk_biz_id": str(ticket_data["bk_biz_id"]),
            "bk_cloud_id": int(ticket_data["bk_cloud_id"]),
            "server_ports": param["ports"],
            "meta_role": param["meta_role"],
            "cluster_type": param["cluster_type"],
            "cluster_domain": param["immute_domain"],
        }
    ]
    act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-202-{}-安装监控").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 启动bkdbmon
    return sub_pipeline.build_sub_process(sub_name=_("Redis-{}-安装原子任务").format(exec_ip))
