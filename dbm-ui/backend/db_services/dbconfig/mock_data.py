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
from django.utils.translation import ugettext_lazy as _

"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

LIST_PUBLIC_CONFIG_REQUEST_BODY = {"meta_cluster_type": "tendbha"}

LIST_PUBLIC_CONFIG_RESPONSE_DATA = [
    {"name": _("5.5配置项"), "version": "mysql-5.5", "updated_at": "2022-05-16 10:20:00", "updated_by": "admin"},
    {"name": _("5.6配置项"), "version": "MySQL-5.6", "updated_at": "2022-05-16 10:20:00", "updated_by": "admin"},
]

CREATE_PUBLIC_CONFIG_REQUEST_BODY = {
    "meta_cluster_type": "tendbha",
    "conf_type": "dbconf",
    "version": "MySQL-5.6",
    "name": _("MySQL5.6配置"),
    "conf_items": [
        {
            "conf_name": "mysqld.expire_logs_days",
            "description": _("日志过期天数"),
            "flag_locked": 0,
            "need_restart": 1,
            "op_type": "update",
            "value_allowed": "[0,999999)",
            "value_default": "60",
            "value_type": "STRING",
            "value_type_sub": "",
        },
        {
            "conf_name": "mysqld.bind-address",
            "description": _("绑定地址"),
            "flag_locked": 1,
            "need_restart": 1,
            "op_type": "update",
            "value_allowed": "",
            "value_default": "0.0.0.0",
            "value_type": "STRING",
            "value_type_sub": "",
        },
        {
            "conf_name": "mysqld.binlog_format",
            "description": _("binlog格式"),
            "flag_locked": 0,
            "need_restart": 0,
            "op_type": "update",
            "value_allowed": "ROW|MIXED|STATEMENT",
            "value_default": "ROW",
            "value_type": "STRING",
            "value_type_sub": "ENUM",
        },
    ],
    "description": _("我是描述"),
    "confirm": 0,
}

GET_PUBLIC_CONFIG_DETAIL_REQUEST_BODY = {
    "meta_cluster_type": "tendbha",
    "conf_type": "dbconf",
    "version": "MySQL-5.6",
    "name": _("MySQL5.6配置"),
}

LIST_BIZ_CONFIG_REQUEST_BODY = {"meta_cluster_type": "tendbha", "conf_type": "dbconf", "bk_biz_id": 2}

UPSERT_LEVEL_CONFIG_REQUEST_BODY = {
    "bk_biz_id": 2,
    "level_name": "cluster",
    "level_value": 1,
    "level_info": {"module": "3"},
    "conf_items": [
        {
            "conf_name": "auto_increment_offset",
            "flag_locked": 1,
            "op_type": "update",
            "conf_value": "4000",
        },
        {
            "conf_name": "autocommit",
            "flag_locked": 0,
            "op_type": "remove",
            "conf_value": "ON",
        },
    ],
    "confirm": 0,
    "description": _("我是描述"),
    "meta_cluster_type": "tendbha",
    "conf_type": "dbconf",
    "version": "MySQL-5.6",
}

SAVE_MODULE_DEPLOY_INFO_REQUEST_BODY = {
    "bk_biz_id": 2,
    "level_name": "module",
    "level_value": 1,
    "conf_items": [
        {
            "conf_name": "charset",
            "op_type": "add",
            "conf_value": "utf8mb4",
        },
        {
            "conf_name": "db_version",
            "op_type": "add",
            "conf_value": "MySQL-5.7",
        },
    ],
    "meta_cluster_type": "tendbha",
    "conf_type": "deploy",
    "version": "deploy_info",
}

GET_LEVEL_CONFIG_DETAIL_REQUEST_BODY = {
    "bk_biz_id": 2,
    "level_name": "cluster",
    "level_value": 1,
    "level_info": {"module": 3},
    "meta_cluster_type": "tendbha",
    "conf_type": "dbconf",
    "version": "MySQL-5.6",
}
