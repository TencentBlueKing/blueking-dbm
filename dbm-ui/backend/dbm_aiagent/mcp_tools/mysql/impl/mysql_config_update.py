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
import json
import logging
from typing import Dict

from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import LevelName, OpType
from backend.db_meta.models import Cluster

logger = logging.getLogger("root")

# conf_type 与 conf_file 的映射关系（单一 conf_file 的类型可自动填充）
CONF_TYPE_DEFAULT_CONF_FILE_MAP = {
    "mysql_monitor": "items-config.yaml",
    "checksum": "checksum.yaml",
}

# backup 类型允许的 conf_file 列表
BACKUP_ALLOWED_CONF_FILES = ["binlog_rotate.yaml", "dbbackup.ini", "dbbackup.options"]


def update_mysql_config(
    bk_biz_id: int,
    cluster_domain: str,
    conf_type: str,
    conf_file: str,
    conf_name: str,
    conf_value: str,
) -> Dict[str, str]:
    """
    修改 MySQL 集群级别的配置（backup / mysql_monitor / checksum）
    """
    # 获取集群对象
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    namespace = cluster_obj.cluster_type
    if not cluster_obj:
        raise ValueError(_("集群不存在: {}").format(cluster_domain))

    # 校验 conf_type 并确定 conf_file
    if conf_type == "backup":
        if conf_file not in BACKUP_ALLOWED_CONF_FILES:
            raise ValueError(_("backup 类型的 conf_file 必须是以下之一: {}").format(", ".join(BACKUP_ALLOWED_CONF_FILES)))
    elif conf_type in CONF_TYPE_DEFAULT_CONF_FILE_MAP:
        # mysql_monitor / checksum 的 conf_file 固定
        conf_file = CONF_TYPE_DEFAULT_CONF_FILE_MAP[conf_type]
        if conf_file == "mysql_monitor":
            # conf_value 必须是 JSON 字符串
            try:
                valid_json = dict(json.loads(conf_value))
                conf_value = json.dumps(valid_json)
                if valid_json.get("enable", None) is None:
                    raise ValueError(_("mysql_monitor conf_value 配置必须包含 enable 字段"))
            except json.JSONDecodeError:
                raise ValueError(_("mysql_monitor conf_value 必须是 JSON 字符串"))

    else:
        raise ValueError(_("不支持的 conf_type: {}").format(conf_type))

    conf_items = [
        {"conf_name": conf_name, "conf_value": conf_value, "op_type": OpType.UPDATE, "description": "by ai agent"}
    ]

    logger.info(
        _("MCP 修改 MySQL 配置: bk_biz_id={}, cluster_domain={}, conf_type={}, conf_file={}, conf_items={}").format(
            bk_biz_id, cluster_domain, conf_type, conf_file, conf_items
        )
    )
    # get module_id by cluster_domain
    module_id = cluster_obj.db_module_id
    DBConfigApi.save_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "conf_file_info": {
                "conf_file": conf_file,
                "conf_type": conf_type,
                "namespace": namespace,
            },
            "conf_items": conf_items,
            "level_name": LevelName.CLUSTER,
            "level_value": cluster_domain,
            "level_info": {
                "module": str(module_id),
            },
            "confirm": 0,
        }
    )

    return {
        "message": _("配置修改成功: cluster_domain={}, conf_type={}, conf_file={}, conf_name={}, conf_value={}").format(
            cluster_domain, conf_type, conf_file, conf_name, conf_value
        )
    }
