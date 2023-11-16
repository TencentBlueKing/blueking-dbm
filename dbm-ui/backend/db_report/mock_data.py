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
