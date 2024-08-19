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

from django.utils.translation import gettext as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

MAX_ACTION_NAME_LEN = 32


class CommonActionLabel(str, StructuredEnum):
    BIZ_READ_ONLY = EnumField("biz_read_only", _("业务只读"))
    BIZ_MAINTAIN = EnumField("biz_maintain", _("业务运维"))
    EXTERNAL_DEVELOPER = EnumField("external_developer", _("外部开发商专用"))

    MYSQL_IMPORT_SQLFILE = EnumField("mysql_import_sqlfile", _("MySQL SQL变更"))
    MYSQL_AUTHORIZE_RULES = EnumField("mysql_authorize_rules", _("MySQL DB授权"))

    TENDBCLUSTER_IMPORT_SQLFILE = EnumField("tendbcluster_import_sqlfile", _("TendbCluster SQL变更"))
    TENDBCLUSTER_AUTHORIZE_RULES = EnumField("tendbcluster_authorize_rules", _("TendbCluster DB授权"))

    KAFKA_ACCESS = EnumField("kafka_access", _("Kafka获取访问方式"))
    ES_ACCESS = EnumField("es_access", _("ES获取访问方式"))
    HDFS_ACCESS = EnumField("hdfs_access", _("HDFS获取访问方式"))
