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

from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, StructuredEnum


class PrivilegeType:
    """规则类型枚举"""

    class MySQL:
        class DML(str, StructuredEnum):
            """DML权限类型"""

            SELECT = EnumField("select", _("选择"))
            INSERT = EnumField("insert", _("插入"))
            UPDATE = EnumField("update", _("更新"))
            DELETE = EnumField("delete", _("删除"))

        class DDL(str, StructuredEnum):
            """DDL权限类型"""

            CREATE = EnumField("create", _("创建表"))
            ALTER = EnumField("alter", _("修改表"))
            DROP = EnumField("drop", _("删除表"))
            INDEX = EnumField("index", _("索引"))
            EXECUTE = EnumField("execute", _("执行"))
            CREATE_VIEW = EnumField("create view", _("创建视图"))

        class GLOBAL(str, StructuredEnum):
            """GLOBAL权限类型"""

            REPLICATION_CLIENT = EnumField("replication client", _("replication client"))
            REPLICATION_SLAVE = EnumField("replication slave", _("replication slave"))
            FILE = EnumField("file", _("file"))
            TRIGGER = EnumField("trigger", _("trigger"))
            EVENT = EnumField("event", _("event"))
            CREATE_ROUTING = EnumField("create routine", _("create routine"))
            ALTER_ROUTING = EnumField("alter routine", _("alter routine"))
            ALL_PRIVILEGES = EnumField("all privileges", _("all privileges"))

    class MongoDB:
        class USER(str, StructuredEnum):
            READ = EnumField("Read", _("Read"))
            READ_write = EnumField("readWrite", _("readWrite"))
            READ_ANY_DATABASE = EnumField("readAnyDatabase", _("readAnyDatabase"))
            READ_WRITE_ANY_DATABASE = EnumField("readWriteAnyDatabase", _("readWriteAnyDatabase"))

        class MANAGER(str, StructuredEnum):
            DBADMIN = EnumField("dbAdmin", _("dbAdmin"))
            BACKUP = EnumField("backup", _("backup"))
            RESTORE = EnumField("restore", _("restore"))
            USER_ADMIN = EnumField("userAdmin", _("userAdmin"))
            CLUSTER_ADMIN = EnumField("clusterAdmin", _("clusterAdmin"))
            CLUSTER_MANAGER = EnumField("clusterManager", _("clusterManager"))
            CLUSTER_MONITOR = EnumField("clusterMonitor", _("clusterMonitor"))
            HOST_MANAGER = EnumField("hostManager", _("hostManager"))
            USER_ADMIN_ANY_DATABASE = EnumField("userAdminAnyDatabase", _("userAdminAnyDatabase"))
            DB_ADMIN_ANY_DATABASE = EnumField("dbAdminAnyDatabase", _("dbAdminAnyDatabase"))
            DB_OWNER = EnumField("dbOwner", _("dbOwner"))
            ROOT = EnumField("root", _("root"))

    class SQLServer:
        class DML(str, StructuredEnum):
            db_datawriter = EnumField("db_datawriter", _("db_datawriter"))
            db_datareader = EnumField("db_datareader", _("db_datareader"))

        class OWNER(str, StructuredEnum):
            db_owner = EnumField("db_owner", _("db_owner"))


class AccountType(str, StructuredEnum):
    """账号类型枚举"""

    MYSQL = EnumField("mysql", _("MySQL"))
    TENDBCLUSTER = EnumField("tendbcluster", _("TendbCluster"))
    MONGODB = EnumField("mongodb", _("MongoDB"))
    SQLServer = EnumField("sqlserver", _("SQLServer"))


class AuthorizeExcelHeader(str, StructuredEnum):
    """授权excel的头部信息"""

    USER = EnumField("账号(单个)", _("账号(单个)"))
    SOURCE_IPS = EnumField("访问源(多个)", _("访问源(多个)"))
    TARGET_INSTANCES = EnumField("访问集群域名(多个)", _("访问集群域名(多个)"))
    ACCESS_DBS = EnumField("访问DB名(多个)", _("访问DB名(多个)"))
    ERROR = EnumField("错误信息/提示信息", _("错误信息/提示信息"))


# 授权数据过期时间
AUTHORIZE_DATA_EXPIRE_TIME = 60 * 60 * 6

# excel分隔符
EXCEL_DIVIDER = ","

# 账号名称最大长度
MAX_ACCOUNT_LENGTH = 31
