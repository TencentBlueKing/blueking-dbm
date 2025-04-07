"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Any

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterType
from backend.flow.consts import ConfigTypeEnum


def get_spider_version_and_charset(bk_biz_id, db_module_id) -> Any:
    """
    根据业务id和模块id，通过bk—config获取版本号和字符集信息
    """
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.MODULE,
            "level_value": str(db_module_id),
            "conf_file": "deploy_info",
            "conf_type": "deploy",
            "namespace": ClusterType.TenDBCluster,
            "format": FormatType.MAP,
        }
    )["content"]
    return data["charset"], data["spider_version"]


def calc_spider_max_count(bk_biz_id, db_module_id, db_version) -> int:
    """
    根据业务id和模块id，通过bk—config获取默认spider的配置
    得出spider_auto_increment_step配置
    为了保证后续可以做集群的整体迁移/整体升级，集群spider_master/spider_mnt的数量不能超过spider_auto_increment_step的一半
    @param bk_biz_id: 业务id
    @param db_module_id: db模块ID
    @param db_version: spider版本
    """
    spider_auto_increment_step = int(
        DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.MODULE,
                "level_value": str(db_module_id),
                "conf_file": db_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": ClusterType.TenDBCluster,
                "format": FormatType.MAP,
            }
        )["content"]["mysqld"]["spider_auto_increment_step"]
    )
    return int(spider_auto_increment_step / 2)
