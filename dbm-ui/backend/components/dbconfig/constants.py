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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _

DEPLOY_FILE_NAME = "deploy_info"


class LevelName(str, StructuredEnum):
    """层级名称枚举"""

    PLAT = EnumField("plat", _("平台层级"))
    APP = EnumField("app", _("业务层级"))
    MODULE = EnumField("module", _("模块层级"))
    CLUSTER = EnumField("cluster", _("集群层级"))
    INSTANCE = EnumField("instance", _("实例层级"))


class ConfType(str, StructuredEnum):
    """配置类型枚举"""

    DEPLOY = EnumField("deploy", _("部署配置"))
    DBCONF = EnumField("dbconf", _("数据库配置"))
    BACKUP = EnumField("backup", _("备份配置"))
    PROXY = EnumField("proxyconf", _("Proxy配置"))


class OpType(str, StructuredEnum):
    """操作类型枚举"""

    ADD = EnumField("add", _("新增"))
    UPDATE = EnumField("update", _("更新"))
    REMOVE = EnumField("remove", _("删除"))


class ReqType(str, StructuredEnum):
    """请求类型枚举"""

    SAVE_ONLY = EnumField("SaveOnly", _("仅保存"))
    GENERATE_AND_SAVE = EnumField("GenerateAndSave", _("生成并保存"))
    SAVE_AND_PUBLISH = EnumField("SaveAndPublish", _("保存并发布"))
    GENERATE_AND_PUBLISH = EnumField("GenerateAndPublish", _("生成并发布"))


class FormatType(str, StructuredEnum):
    """格式枚举"""

    LIST = EnumField("list", _("列表"))
    MAP = EnumField("map", _("字典"))
    MAP_LEVEL = EnumField("map.", _("分级字典"))


class MysqlDefaultDeployConfig:
    """MySQL默认部署配置"""

    DB_VERSION = "MySQL-5.7"
    CHARSET = "utf8mb4"
