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

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.exec_clear_machine import ClearMachineScriptComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class ClearRedisMachineFlow(object):
    """
    构建清理rediscache/tendissd/tendisplus/twemproxy/predixy机器的流程
    兼容跨云区域的执行
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def run_flow(self):
        """
        定义清理机器的执行流程
        执行逻辑：
        1: 清理和机器相关的dbm元数据
        2: 清理机器
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)

        main_pipeline.add_act(
            act_name=_("清理元数据-{}".format(self.data["clear_hosts"])),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=RedisDBMeta.clear_machines.__name__)),
        )

        main_pipeline.add_act(
            act_name=_("清理机器-{}".format(self.data["clear_hosts"])),
            act_component_code=ClearMachineScriptComponent.code,
            kwargs={"exec_ips": self.data["clear_hosts"]},
        )

        main_pipeline.run_pipeline()
