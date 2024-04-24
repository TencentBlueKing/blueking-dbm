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

"""
定义一些mysql场景通过bk-config服务获取一些信息的公共方法，方便管理，减少代码重复率
"""


def get_mysql_version_and_charset(bk_biz_id, db_module_id, cluster_type) -> Any:
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
            "namespace": cluster_type,
            "format": FormatType.MAP,
        }
    )["content"]

    return data["charset"], data["db_version"]


def get_backup_ini_config(bk_biz_id: int, db_module_id: int, cluster_type: str):
    """
    根据集群维度，获取备份options配置
    @param bk_biz_id: 业务id
    @param db_module_id: db模块id
    @param cluster_type: 集群类型
    """
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.MODULE,
            "level_value": str(db_module_id),
            "conf_file": "dbbackup.ini",
            "conf_type": "backup",
            "namespace": cluster_type,
            "format": FormatType.MAP_LEVEL,
        }
    )
    return data["content"]


def get_backup_options_config(bk_biz_id: int, db_module_id: int, cluster_type: str, cluster_domain: str):
    """
    根据集群维度，获取备份options配置
    @param bk_biz_id: 业务id
    @param db_module_id: db模块id
    @param cluster_type: 集群类型
    @param cluster_domain: 集群域名
    """
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.CLUSTER,
            "level_value": cluster_domain,
            "level_info": {"module": str(db_module_id)},
            "conf_file": "dbbackup.options",
            "conf_type": "backup",
            "namespace": cluster_type,
            "format": FormatType.MAP_LEVEL,
        }
    )
    return data["content"]
