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

META_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {"bk_biz_id": 3, "ip": "127.0.0.1", "port": 3600, "machine_type": "remote", "status": True, "msg": ""}
    ],
    "name": "实例集群归属",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "ip", "display_name": "IP", "format": "text"},
        {"name": "port", "display_name": "端口", "format": "text"},
        {"name": "machine_type", "display_name": "实例类型", "format": "text"},
        {"name": "status", "display_name": "元数据状态", "format": "status"},
        {"name": "msg", "display_name": "详情", "format": "text"},
    ],
}

CHECKSUM_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [{"bk_biz_id": 3, "cluster": "example.cluster", "status": True, "fail_slaves": 0, "msg": ""}],
    "name": "数据校验",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群", "format": "text"},
        {"name": "status", "display_name": "校验结果", "format": "status"},
        {"name": "fail_slaves", "display_name": "失败的从库实例数量", "format": "text"},
        {"name": "msg", "display_name": "失败信息", "format": "text"},
    ],
}

CHECKSUM_INSTANCE_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [{"bk_biz_id": 3, "cluster": "example.cluster", "status": True, "fail_slaves": 0, "msg": ""}],
    "name": "失败的从库实例详情",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群", "format": "text"},
        {"name": "status", "display_name": "校验结果", "format": "status"},
        {"name": "fail_slaves", "display_name": "失败的从库实例数量", "format": "text"},
        {"name": "msg", "display_name": "失败信息", "format": "text"},
    ],
}

# mysql 备份报告
MYSQL_BACKUP_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [{"bk_biz_id": 3, "cluster": "aa.bb.cc", "cluster_type": "tendbha", "status": True, "msg": ""}],
    "name": "mysql备份检查",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群域名", "format": "text"},
        {"name": "cluster_type", "display_name": "集群类型", "format": "text"},
        {"name": "status", "display_name": "元数据状态", "format": "status"},
        {"name": "msg", "display_name": "详情", "format": "text"},
    ],
}

# redis 全备份和binlog备份报告
REDIS_BACKUP_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "bk_biz_id": 3,
            "cluster": "aa.bb.cc",
            "cluster_type": "TendisSSD",
            "instance": "aa:bb",
            "status": True,
            "msg": "",
        }
    ],
    "name": "redis备份检查",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群域名", "format": "text"},
        {"name": "cluster_type", "display_name": "集群类型", "format": "text"},
        {"name": "status", "display_name": "校验结果", "format": "status"},
        {"name": "instance", "display_name": "实例节点", "format": "text"},
        {"name": "msg", "display_name": "详情", "format": "text"},
    ],
}

# dbmon心跳超时报告
DBMON_HEARTBEAT_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "bk_biz_id": 3,
            "cluster": "aa.bb.cc",
            "app": "dba",
            "dba": "admin",
            "time": "",
            "cluster_type": "TWEMPROXY",
            "instance": "aa:bb",
        }
    ],
    "name": "dbmon心跳报告",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群域名", "format": "text"},
        {"name": "app", "display_name": "业务名", "format": "text"},
        {"name": "dba", "display_name": "业务所属dba", "format": "text"},
        {"name": "cluster_type", "display_name": "类型", "format": "text"},
        {"name": "instance", "display_name": "实例节点", "format": "text"},
        {"name": "create_at", "display_name": "心跳超时时间", "format": "text"},
    ],
}

# 元数据检查那里还需要在增加redis特有的检查
REDIS_META_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {"bk_biz_id": 3, "cluster": "xx.xx.xx.xx", "cluster_type": "TwemproxyRedisInstance", "status": True, "msg": ""}
    ],
    "name": "redis 元数据检查",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群名", "format": "text"},
        {"name": "cluster_type", "display_name": "集群类型", "format": "text"},
        {"name": "status", "display_name": "元数据状态", "format": "status"},
        {"name": "msg", "display_name": "详情", "format": "text"},
    ],
}

REPORT_OVERVIEW_DATA = {
    "redis": [
        "dbmon_heartbeat_check",
        "full_backup_check",
        "binlog_backup_check",
        "alone_instance_check",
        "status_abnormal_check",
    ],
    "mysql": ["full_backup_check", "binlog_backup_check", "meta_check", "checksum"],
}

REPORT_COUNT_DATA = {
    "redis": {
        "dbmon_heartbeat_check": {"manage_count": 10896, "assist_count": 0},
    },
    "mysql": {
        "full_backup_check": {"manage_count": 0, "assist_count": 26},
    },
}


# SQLSERVER 备份报告
SQLSERVER_BACKUP_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [{"bk_biz_id": 3, "cluster": "aa.bb.cc", "cluster_type": "sqlserver_ha", "msg": ""}],
    "name": "sqlserver备份检查",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群域名", "format": "text"},
        {"name": "cluster_type", "display_name": "集群类型", "format": "text"},
        {"name": "msg", "display_name": "详情", "format": "text"},
    ],
}

# SQLSERVER 备份报告
SQLSERVER_SYNC_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "bk_biz_id": 3,
            "cluster": "aa.bb.cc",
            "cluster_type": "sqlserver_ha",
            "instance_host": "1.1.1.1",
            "instance_port": 48322,
            "msg": "",
        }
    ],
    "name": "sqlserver同步检查",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群域名", "format": "text"},
        {"name": "cluster_type", "display_name": "集群类型", "format": "text"},
        {"name": "instance_host", "display_name": "实例IP", "format": "text"},
        {"name": "instance_port", "display_name": "实例端口", "format": "text"},
        {"name": "msg", "display_name": "详情", "format": "text"},
    ],
}

# SQLSERVER app_setting报告
SQLSERVER_APP_SETTING_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "bk_biz_id": 3,
            "cluster": "aa.bb.cc",
            "cluster_type": "sqlserver_ha",
            "instance_host": "1.1.1.1",
            "instance_port": 48322,
            "msg": "",
            "is_fix": True,
        }
    ],
    "name": "sqlserver app_setting数据检查",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群域名", "format": "text"},
        {"name": "cluster_type", "display_name": "集群类型", "format": "text"},
        {"name": "instance_host", "display_name": "实例IP", "format": "text"},
        {"name": "instance_port", "display_name": "实例端口", "format": "text"},
        {"name": "msg", "display_name": "详情", "format": "text"},
        {"name": "is_fix", "display_name": "是否自动修复", "format": "text"},
    ],
}

# mongodb 全备份和binlog备份报告
MONGODB_BACKUP_CHECK_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "bk_biz_id": 3,
            "cluster": "aa.bb.cc",
            "cluster_type": "MongoShardedCluster",
            "instance": "aa:bb",
            "status": True,
            "msg": "",
        }
    ],
    "name": "mongodb备份检查",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster", "display_name": "集群域名", "format": "text"},
        {"name": "cluster_type", "display_name": "集群类型", "format": "text"},
        {"name": "status", "display_name": "校验结果", "format": "status"},
        {"name": "instance", "display_name": "实例节点", "format": "text"},
        {"name": "msg", "display_name": "详情", "format": "text"},
    ],
}
# 备份恢复演练 mock data
REPORT_BACKUP_RECOVER_DATA = {
    "count": 2,
    "next": None,
    "previous": None,
    "results": [
        {
            "bk_biz_id": 1,
            "cluster_domain": "mysql-prod-01.db.example.com",
            "backup_begin_time": "2024-04-01T02:00:00Z",
            "recover_duration": 45,
            "status": True,
            "task_id": "task_20240401001",
            "charset": "utf8mb4",
            "mysql_version": "8.0.32",
            "backup_type": "full",
            "backup_tool": "xtrabackup",
            "create_at": "2024-04-01T01:00:00Z",
        },
        {
            "bk_biz_id": 2,
            "cluster_domain": "mysql-test-02.db.example.com",
            "backup_begin_time": "2024-04-02T03:30:00Z",
            "recover_duration": 60,
            "status": False,
            "task_id": "task_20240402002",
            "charset": "utf8",
            "mysql_version": "5.7.41",
            "backup_type": "incremental",
            "backup_tool": "mysqldump",
            "create_at": "2024-04-02T03:00:00Z",
        },
    ],
    "name": "备份恢复演练",
    "title": [
        {"name": "bk_biz_id", "display_name": "业务", "format": "text"},
        {"name": "cluster_domain", "display_name": "集群名称", "format": "text"},
        {"name": "mysql_version", "display_name": "MySQL版本", "format": "text"},
        {"name": "charset", "display_name": "备份字符集", "format": "text"},
        {"name": "backup_type", "display_name": "备份类型", "format": "text"},
        {"name": "backup_tool", "display_name": "备份工具", "format": "text"},
        {"name": "backup_begin_time", "display_name": "备份开始时间", "format": "text"},
        {"name": "recover_duration", "display_name": "恢复花费时间(分钟)", "format": "text"},
        {"name": "status", "display_name": "任务状态", "format": "status"},
        {"name": "task_id", "display_name": "任务ID", "format": "link"},
        {"name": "create_at", "display_name": "创建时间", "format": "text"},
    ],
}
