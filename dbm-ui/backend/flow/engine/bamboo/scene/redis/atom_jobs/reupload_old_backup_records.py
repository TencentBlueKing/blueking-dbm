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
from copy import deepcopy
from dataclasses import asdict
from typing import Dict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.flow.consts import WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_old_backup_records import (
    GetOldBackupRecordsAndSaveComponent,
)
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs

logger = logging.getLogger("flow")


def RedisReuploadOldBackupRecordsAtomJob(root_id, ticket_data, sub_kwargs: ActKwargs, params: Dict) -> SubBuilder:
    """### 将备份记录重新上报到bklog
    params (Dict): {
        "bk_biz_id": "3",
        "bk_cloud_id": 0,
        "server_ip": "a.a.a.a",
        "server_ports":[30000,30001,30002],
        "cluster_domain":"cache.test.test.db",
        "cluster_type":"TwemproxyRedisInstance",
        "meta_role":"redis_slave",
        "server_shards":{
            "a.a.a.a:30000":"0-14999",
            "a.a.a.a:30001":"15000-29999",
            "a.a.a.a:30002":"30000-44999"
        },
        "ndays": 7
    }
    """
    # 查询历史备份记录
    bk_biz_id = params["bk_biz_id"]
    bk_cloud_id = params.get("bk_cloud_id", DEFAULT_BK_CLOUD_ID)
    server_ip = params["server_ip"]
    ndays = params.get("ndays", 7)

    local_file = "/data/dbbak/last_n_days_gcs_backup_record.txt"
    act_kwargs = deepcopy(sub_kwargs)
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )
    # 下发介质包
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.exec_ip = server_ip
    act_kwargs.file_list = trans_files.redis_actuator_backend()
    sub_pipeline.add_act(
        act_name=_("{}下发介质包").format(server_ip), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
    )

    # 获取备份记录并保存到本地文件
    act_kwargs.exec_ip = server_ip
    act_kwargs.write_op = WriteContextOpType.APPEND.value
    act_kwargs.cluster = {
        "ndays": ndays,
        "bk_cloud_id": bk_cloud_id,
        "server_ip": server_ip,
        "save_file": local_file,
    }
    sub_pipeline.add_act(
        act_name=_("{}-gcs备份记录获取并保存到本地文件").format(server_ip, local_file),
        act_component_code=GetOldBackupRecordsAndSaveComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 上报备份记录到bklog
    act_kwargs.exec_ip = server_ip
    act_kwargs.cluster = {
        "bk_biz_id": str(bk_biz_id),
        "bk_cloud_id": bk_cloud_id,
        "server_ip": server_ip,
        "server_ports": params["server_ports"],
        "cluster_domain": params["cluster_domain"],
        "cluster_type": params["cluster_type"],
        "meta_role": params["meta_role"],
        "server_shards": params.get("server_shards", {}),
        "records_file": local_file,
        "force": True,
    }
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_reupload_old_backup_records_payload.__name__
    sub_pipeline.add_act(
        act_name=_("{}-备份记录上报到bklog").format(server_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )
    return sub_pipeline.build_sub_process(sub_name=_("{}-重新上报备份记录").format(server_ip))
