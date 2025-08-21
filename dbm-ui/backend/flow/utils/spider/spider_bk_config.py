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
from backend.flow.engine.bamboo.scene.spider.common.exceptions import NormalSpiderFlowException


def get_spider_version_and_charset(bk_biz_id, db_module_id) -> Any:
    """
    根据业务id和模块id，通过bk—config获取版本号和字符集信息
    """
    if int(db_module_id) <= 0:
        # 模块ID小于等于属于非法
        raise NormalSpiderFlowException(message=f"db_module_id = {db_module_id} is illegal")

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


def calc_spider_max_count(bk_biz_id, db_module_id, db_version, immute_domain: str, is_init: bool = False) -> int:
    """
    如果集群配置没有开启spider_auto_increment_mode_switch
    则这里直接返回平台硬限制，返回128
    如果开启，则按照下面判断：
    根据业务id和模块id，通过bk—config获取默认spider的配置
    得出spider_auto_increment_step配置
    为了保证后续可以做集群的整体迁移/整体升级，集群spider_master/spider_mnt的数量不能超过spider_auto_increment_step的一半
    @param bk_biz_id: 业务id
    @param db_module_id: db模块ID
    @param db_version: spider版本
    @param immute_domain: 域名信息
    @param is_init: 是否是第一次查询申请，域名配置没有生成好，针对集群部署的场景
    """
    if is_init:
        config = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.MODULE,
                "level_value": str(db_module_id),
                "conf_file": db_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": ClusterType.TenDBCluster,
                "format": FormatType.MAP_LEVEL,
            }
        )["content"]["mysqld"]

    else:
        config = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.CLUSTER,
                "level_value": immute_domain,
                "level_info": {"module": str(db_module_id)},
                "conf_file": db_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": ClusterType.TenDBCluster,
                "format": FormatType.MAP_LEVEL,
            }
        )["content"]["mysqld"]

    if int(config["spider_auto_increment_mode_switch"]):
        # spider_auto_increment_step 值作为集群理论上限
        return int(config["spider_auto_increment_step"])

    # 没有开启全局自增，返回硬上限
    return 1024
