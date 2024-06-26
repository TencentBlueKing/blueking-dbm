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
from typing import Union

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.flow.consts import ConfigTypeEnum, NameSpaceEnum
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator
from backend.flow.utils.doris.consts import DEFAULT_BE_WEB_PORT, DEFAULT_FE_WEB_PORT, DorisConfigEnum

logger = logging.getLogger("flow")


class DorisCCTopoOperator(CCTopoOperator):
    db_type = DBType.Doris.value

    def generate_custom_labels(self, ins: Union[StorageInstance, ProxyInstance]) -> dict:
        # 定义注册Doris服务监控实例需要的labels标签结构
        metrics_port = "0"
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.bk_biz_id),
                "level_name": LevelName.APP,
                "level_value": str(self.bk_biz_id),
                "conf_file": self.clusters[0].major_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": NameSpaceEnum.Doris,
                "format": FormatType.MAP_LEVEL,
                "method": ReqType.GENERATE_AND_PUBLISH,
            }
        )
        if ins.instance_role in [InstanceRole.DORIS_OBSERVER, InstanceRole.DORIS_FOLLOWER]:
            metrics_port = str(data["content"][DorisConfigEnum.Frontend].get("http_port", DEFAULT_FE_WEB_PORT))
        elif ins.instance_role in [InstanceRole.DORIS_BACKEND_HOT, InstanceRole.DORIS_BACKEND_COLD]:
            metrics_port = str(DEFAULT_BE_WEB_PORT)

        logger.info("metrics_port is %d", metrics_port)
        return {
            "metrics_port": metrics_port,
        }
