"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import ConfigTypeEnum, SqlserverVersion


def get_module_infos(bk_biz_id: int, db_module_id: int, cluster_type: ClusterType) -> dict:
    """
    根据业务id和模块id，通过bk—config获取模块信息
    @param bk_biz_id: 业务id
    @param db_module_id: db模块id
    @param cluster_type: 集群类型
    """
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.MODULE,
            "level_value": str(db_module_id),
            "conf_file": "deploy_info",
            "conf_type": "deploy",
            "namespace": cluster_type,
            "format": FormatType.MAP,
        }
    )["content"]
    return data


def get_sqlserver_config(
    bk_biz_id: int, immutable_domain: str, db_version: SqlserverVersion, db_module_id: int, cluster_type: ClusterType
) -> dict:
    """
    生成并获取sqlserver实例配置,集群级别配置
    sqlserver_single和sqlserver_ha集群统一用这里拿去配置
    @param bk_biz_id: 业务id
    @param immutable_domain: 集群主域名
    @param db_version: 数据库版本
    @param db_module_id: db模块id
    @param cluster_type: 集群类型
    """
    data = DBConfigApi.get_or_generate_instance_config(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.CLUSTER,
            "level_value": immutable_domain,
            "level_info": {"module": str(db_module_id)},
            "conf_file": db_version,
            "conf_type": ConfigTypeEnum.DBConf,
            "namespace": cluster_type,
            "format": FormatType.MAP_LEVEL,
            "method": ReqType.GENERATE_AND_PUBLISH,
        }
    )
    return data["content"]
