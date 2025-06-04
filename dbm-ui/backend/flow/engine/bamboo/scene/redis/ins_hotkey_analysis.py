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
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta.models import RedisHotKeyInfo
from backend.db_proxy.models import DBCloudProxy
from backend.flow.consts import AUTH_ADDRESS_DIVIDER, StateType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class HotkeyAnalysisFlow(object):
    """
    proxy + redis 分析热key flow
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_nginx_ip(bk_cloud_id: int) -> str:
        nginx_ip = DBCloudProxy.objects.filter(bk_cloud_id=bk_cloud_id).last().internal_address
        return nginx_ip

    @staticmethod
    def __get_token(bk_cloud_id: int) -> str:
        return AsymmetricHandler.encrypt(
            name=AsymmetricCipherConfigType.PROXYPASS.value, content=f"{bk_cloud_id}_dbactuator_token"
        )

    def ins_hotkey_analysis_flow(self):
        # 数据预处理
        ip_job_map = defaultdict(list)
        ip_cluster_map = {}
        for info in self.data["infos"]:
            for ins in info["ins"]:
                ip, port = str.split(ins, AUTH_ADDRESS_DIVIDER)
                ip_job_map[ip].append(
                    {
                        "port": int(port),
                        "record_id": info["record_id"],
                    }
                )
                ip_cluster_map[ip] = info["cluster_id"]
        ip_job_map = dict(ip_job_map)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        bk_cloud_id = self.data["bk_cloud_id"]
        db_cloud_token = self.__get_token(bk_cloud_id)
        nginx_ip = self.__get_nginx_ip(bk_cloud_id)

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.exec_ip = list(ip_job_map.keys())
        redis_pipeline.add_act(
            act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 按ip下发任务
        acts_list = []
        for ip, params in ip_job_map.items():
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {
                "ip": ip,
                "analysis_time": int(self.data["analysis_time"]),
                "ticket_id": self.data["uid"],
                "bk_biz_id": self.data["bk_biz_id"],
                "ins_list": ip_job_map[ip],
                "cluster_id": int(ip_cluster_map[ip]),
                "api_server": nginx_ip,
                "bk_cloud_id": bk_cloud_id,
                "db_cloud_token": db_cloud_token,
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.hotkey_analysis_payload.__name__
            acts_list.append(
                {
                    "act_name": _("实例分析热key: {}").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )

        # 更新热key记录表的root_id及状态
        RedisHotKeyInfo.objects.filter(ticket_id=self.data["uid"]).update(
            root_id=self.root_id, status=StateType.RUNNING
        )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)
        redis_pipeline.run_pipeline()
