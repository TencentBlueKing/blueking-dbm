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

CREATE_SINGLE_TICKET_DATA = {
    "ticket_type": "MYSQL_SINGLE_APPLY",
    "remark": "",
    "details": {
        "city_code": "string",
        "spec": "string",
        "db_module_id": 0,
        "cluster_count": 3,
        "inst_num": 2,
        "domains": [{"key": "cluster_1"}, {"key": "cluster_2"}, {"key": "cluster_3"}],
        "ip_source": "manual_input",
        "nodes": {"backend": [{"ip": "127.0.0.1", "bk_cloud_id": 0}, {"ip": "127.0.0.1", "bk_cloud_id": 0}]},
        "mysql_port": 10000,
        "disaster_tolerance_level": "cross_city",
        "proxy_port": 20000,
    },
    "bk_biz_id": 2005000002,
}

CREATE_TENDBHA_TICKET_DATA = {
    "ticket_type": "MYSQL_HA_APPLY",
    "remark": "",
    "details": {
        "city_code": "string",
        "spec": "string",
        "db_module_id": 0,
        "cluster_count": 1,
        "domains": [
            {
                "key": "aaa",
            }
        ],
        "ip_source": "manual_input",
        "nodes": {
            "backend": [{"ip": "127.0.0.1", "bk_cloud_id": 0}, {"ip": "127.0.0.1", "bk_cloud_id": 0}],
            "proxy": [{"ip": "127.0.0.3", "bk_cloud_id": 0}, {"ip": "127.0.0.4", "bk_cloud_id": 0}],
        },
        "mysql_port": 10000,
        "disaster_tolerance_level": "cross_city",
        "proxy_port": 20000,
    },
    "bk_biz_id": 2005000002,
}

CREATE_ES_TICKET_DATA = {
    "bk_biz_id": 2005000002,
    "db_app_abbr": "blueking",
    "remark": _("测试创建es集群"),
    "ticket_type": "ES_APPLY",
    # 业务专属协议
    "details": {
        "cluster_name": "viper-cluster",
        "city_code": _("深圳"),
        "db_version": "3.2.3",
        "http_port": 9200,
        "nodes": {
            "hot": [
                {"ip": "127.0.0.1", "bk_cloud_id": 0, "instance_num": 1},
            ],
            "cold": [
                {"ip": "127.0.0.2", "bk_cloud_id": 0, "instance_num": 1},
            ],
            "client": [
                {"ip": "127.0.0.7", "bk_cloud_id": 0},
            ],
            "master": [
                {"ip": "127.0.0.7", "bk_cloud_id": 0},
            ],
        },
    },
}

CREATE_KAFKA_TICKET_DATA = {
    "bk_biz_id": 2005000002,
    "remark": _("测试创建kafka集群"),
    "ticket_type": "KAFKA_APPLY",
    # 业务专属协议
    "details": {
        "cluster_name": "viper-cluster",
        "city_code": _("深圳"),
        "db_version": "3.2.3",
        "username": "username",
        "password": "password",
        "port": 9092,
        "partition_num": 2,
        "retention_hours": 2,
        "replication_num": 2,
        "nodes": {
            "zookeeper": [
                {"ip": "127.0.0.1", "bk_cloud_id": 0},
                {"ip": "127.0.0.2", "bk_cloud_id": 0},
                {"ip": "127.0.0.3", "bk_cloud_id": 0},
            ],
            "broker": [
                {"ip": "127.0.0.3", "bk_cloud_id": 0},
                {"ip": "127.0.0.4", "bk_cloud_id": 0},
            ],
        },
    },
}

CREATE_HDFS_TICKET_DATA = {
    "bk_biz_id": 2005000002,
    "remark": _("测试创建hdfs集群"),
    "ticket_type": "HDFS_APPLY",
    # 业务专属协议
    "details": {
        "cluster_name": "viper-cluster",
        "city_code": _("深圳"),
        "db_app_abbr": "blueking",
        "version_id": 133,
        # 用户指定访问HDFS的WEB端口，默认50070，禁用2181，8480，8485
        "http_port": 50070,
        # 用户指定访问HDFS的RPC端口，默认9000，禁用2181，8480，8485，不能与http_port相同
        "rpc_port": 9000,
        # 用户HTTP访问Namenode密码，默认用户名root
        "haproxy_passwd": "haproxy_passwd",
        "nodes": {
            "zookeeper": [
                {"ip": "127.0.0.1", "bk_cloud_id": 0},
                {"ip": "127.0.0.2", "bk_cloud_id": 0},
                {"ip": "127.0.0.3", "bk_cloud_id": 0},
            ],
            "namenode": [
                {"ip": "127.0.0.4", "bk_cloud_id": 0},
                {"ip": "127.0.0.5", "bk_cloud_id": 0},
            ],
            "datanode": [
                {"ip": "127.0.0.6", "bk_cloud_id": 0},
                {"ip": "127.0.0.7", "bk_cloud_id": 0},
            ],
        },
    },
}

CREATE_REDIS_TICKET_DATA = {
    "uid": "2022051612120001",
    "created_by": "admin",
    "bk_biz_id": "152",
    "ticket_type": "REDIS_CLUSTER_APPLY",  # 单据类型
    "proxy_port": 50000,  # 集群端口
    "domain_name": "xxx",  # 域名
    "cluster_name": "test",  # 集群ID
    "cluster_alias": _("测试集群"),  # 集群别名
    "cluster_type": "TwemproxyRedisInstance",  # 集群架构
    "city": _("深圳"),
    "shard_num": 6,  # 分片数
    # ---- 集群容量
    "spec": "S5.4XLARGE32",  # 机器规格
    "group_num": 2,  # 机器组数 -> 手输机器数为组数的倍数
    "maxmemory": "2G",  # 实例最大内存
    # ---- 集群容量
    "db_version": "Redis-2.8",
    "databases": 2,  # 库数量，集群申请给默认值2就好
    "proxy_pwd": "twemproxypwd",  # proxy密码
    "redis_pwd": "redispwd",  # redis密码
    "nodes": {
        "proxy": [
            {"ip": "127.0.0.1", "bk_cloud_id": 0},
            {"ip": "127.0.0.2", "bk_cloud_id": 0},
        ],
        "master": [
            {"ip": "127.0.0.4", "bk_cloud_id": 0},
            {"ip": "127.0.0.5", "bk_cloud_id": 0},
        ],
        "slave": [
            {"ip": "127.0.0.6", "bk_cloud_id": 0},
            {"ip": "127.0.0.7", "bk_cloud_id": 0},
        ],
    },
}
