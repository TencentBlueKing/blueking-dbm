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
import logging
import uuid

from rest_framework.response import Response

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.redis import RedisController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class InstallRedisCacheClusterSceneApiView(FlowTestView):
    """
     api: /apis/v1/flow/scene/install_redis_cache_cluster_apply
    params:
     {
         "uid": "2022051612120001",
         "created_by": "admin",
         "bk_biz_id": "152",
         "ticket_type": "REDIS_CLUSTER_APPLY",  # 单据类型
         "proxy_port": 50000,  # 集群端口
         "domain_name": "xxx",  # 域名
         "cluster_name": "test",  # 集群ID
         "cluster_alias": "测试集群",  # 集群别名
         "cluster_type": "TwemproxyRedisInstance",  # 集群架构,
         "city": "深圳",
         "shard_num": 6,  # 分片数
         # ---- 集群容量
         "spec": "S5.4XLARGE32",  # 机器规格
         "group_num": 2,  # 机器组数 -> 手输机器数为组数的倍数
         "maxmemory": 2147483648,  # 实例最大内存
         # ---- 集群容量
         "db_version": "Redis-6",
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
         }
     }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        if request.data["cluster_type"] == ClusterType.TendisPredixyRedisCluster:
            RedisController(root_id=root_id, ticket_data=request.data).tendisplus_apply_scene()
        elif request.data["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_apply_scene()
        elif request.data["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance.value:
            RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_apply_scene()
        return Response({"root_id": root_id})


class InstallTendisplusClusterSceneApiView(FlowTestView):
    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).tendisplus_apply_scene()
        return Response({"root_id": root_id})


class RedisClusterBackupSceneApiView(FlowTestView):
    """
         api: /apis/v1/flow/scene/redis_cluster_backup
        params:
         {
        "uid":"2022051612120001",
        "created_by":"xxxx",
        "bk_biz_id":2005000194,
        "ticket_type":"REDIS_BACKUP",
        "backup_server":{
        },
        "rules":[
            {
                "cluster_id":1,
                "domain":"cache.test1.redistest.db",
                "target":"master/slave",
                "backup_type":"normal_backup/forever_backup"
            }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_backup()
        return Response({"root_id": root_id})


class RedisClusterOpenCloseSceneApiView(FlowTestView):
    """
     api: /apis/v1/flow/scene/redis_open_close
    params:
     {
        "uid":"2022051612120001",
        "created_by":"xxxx",
        "bk_biz_id": 2005000194,
        "ticket_type": "REDIS_OPEN/REDIS_CLOSE",
        "cluster_id": 123
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_open_close_scene()
        return Response({"root_id": root_id})


class RedisClusterShutdownSceneApiView(FlowTestView):
    """
     api: /apis/v1/flow/scene/redis_shutdown
    params:
     {
        "uid":"2022051612120001",
        "created_by":"xxxx",
        "bk_biz_id": 2005000194,
        "ticket_type": "REDIS_CLUSTER_SHUTDOWN",
        "cluster_id": 123
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_shutdown()
        return Response({"root_id": root_id})


class SingleRedisShutdownSceneApiView(FlowTestView):
    """
     api: /apis/v1/flow/scene/single_redis_shutdown
    params:
     {
        "uid":"2022051612120001",
        "created_by":"xxxx",
        "bk_biz_id":2005000002,
        "ticket_type":"SINGLE_REDIS_SHUTDOWN",
        "instance_list": [152,153,154]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).single_redis_shutdown()
        return Response({"root_id": root_id})


class SingleProxyShutdownSceneApiView(FlowTestView):
    """
     api: /apis/v1/flow/scene/single_proxy_shutdown
    params:
     {
        "uid":"2022051612120001",
        "created_by":"xxxx",
        "bk_biz_id":2005000002,
        "ticket_type":"SINGLE_PROXY_SHUTDOWN",
         "force":true
        "instance_list": [152,153,154]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).single_proxy_shutdown()
        return Response({"root_id": root_id})


class RedisFlushDataSceneApiView(FlowTestView):
    """
     api: /apis/v1/flow/scene/redis_flush_data
    params:
     {
    "uid":"2022051612120001",
    "created_by":"xxxx",
    "bk_biz_id":2005000194,
    "ticket_type":"REDIS_PURGE",
    "rules":[
            {
                "cluster_id": 1,
                "cluster_type": "TwemproxyRedisInstance",
                "domain": "cache.test1.redistest.db",
                "target": "master",
                "mode": "force", //safe（检查）/force（强制）
                "backup": true,
            }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_flush_data()
        return Response({"root_id": root_id})


class RedisProxyScaleSceneApiView(FlowTestView):
    """
     api: /apis/v1/flow/scene/redis_proxy_scale
    params:
     {
        "uid":"2022051612120001",
        "bk_biz_id": 3,
        "created_by":"xxxx",
        "ticket_type":"PROXY_SCALE_UP/PROXY_SCALE_DOWN",
        "infos": [
          {
            "cluster_id": 1,
            "target_proxy_count": 1,
            // 缩容
            "online_switch_type":"user_confirm/no_confirm",
            // 扩容
            "proxy_scale_up_hosts": [
                {"ip": "3.3.3.1", "bk_cloud_id": 0, "bk_host_id": 2},
                {"ip": "3.3.3.2", "bk_cloud_id": 0, "bk_host_id": 2},
            ]
          }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_proxy_scale()
        return Response({"root_id": root_id})


class RedisBackendScaleSceneApiView(FlowTestView):
    """
     api: /apis/v1/flow/scene/redis_backend_scale
    params{
                "bk_biz_id": "",
                "ticket_type":"",
                "infos":[
                    "bk_cloud_id":",
                    "online_switch_type":"",
                    "cluster_id": "",           # 必须
                    "db_version": "Redis-7",    # 可选
                    "group_num": 4,
                    "shard_num": 40,         # 需要保证分片数能整除机器组数。并且与老集群架构的分片数是一样的
                    "backend_group":[
                        {
                            "master":"1.1.1.1",
                            "slave":"2.2.2.1"
                        },
                        {
                            "master":"1.1.1.2",
                            "slave":"2.2.2.2"
                        },
                        {
                            "master":"1.1.1.3",
                            "slave":"2.2.2.3"
                        },
                        {
                            "master":"1.1.1.4",
                            "slave":"2.2.2.4"
                        }],
                    "deploy_plan_id":3,
                    "resource_spec":{}
                }]
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_backend_scale()
        return Response({"root_id": root_id})


class RedisClusterDataCopySceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/redis_cluster_data_copy
    params:
    {
        "uid":1111,
        "bk_biz_id":2005000194,
        "ticket_type":"REDIS_CLUSTER_DATA_COPY",
        # dts 复制类型: 业务内
        "dts_copy_type":"one_app_diff_cluster",
        # write_mode值为:
        # - delete_and_write_to_redis 先删除同名redis key, 在执行写入 (如: del $key + hset $key)
        # - keep_and_append_to_redis 保留同名redis key,追加写入
        # - flushall_and_write_to_redis 先清空目标集群所有数据,在写入
        "write_mode": "delete_and_write_to_redis",
        # 同步断开设置
        "sync_disconnect_setting":{
            # type 值为:
            # - auto_disconnect_after_replication: 数据复制完成后自动断开同步关系
            # - keep_sync_with_reminder: 数据复制完成后保持同步关系，定时发送断开同步提醒
            "type": "auto_disconnect_after_replication"
            "reminder_frequency": "once_daily/once_weekly"
        },
        "data_check_repair_setting":{
            # type值为:
            # - data_check_and_repair: 数据校验并修复
            # - data_check_only: 仅进行数据校验，不进行修复
            # - no_check_no_repair: 不校验不修复
            "type": "data_check_and_repair",
            # execution_frequency 执行频次
            "execution_frequency": "once_after_replication/once_every_three_days/once_weekly"
        }
        "infos":[
            {
                "src_cluster":"1111",
                "dst_cluster":"2222",
                "key_white_regex":"*", #包含key
                "key_black_regex":"", #排除key
            }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_data_copy()
        return Response({"root_id": root_id})


class RedisClusterDataCheckRepairApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/redis_cluster_data_check_repair
    params:
    {
        "bk_biz_id": 3,
        "ticket_type":"REDIS_DATACOPY_CHECK_REPAIR",
        # execute_mode 执行模式
        # - auto_execution 自动执行
        # - scheduled_execution 定时执行
        "execute_mode":"auto_execution",
        "specified_execution_time":"2023-06-20 00:00:00", # 定时执行,指定执行时间
        "global_timeout": "never/3h/6h/24h/48h/168h", # 全局超时时间,
        "data_repair_enabled":true/false, # 是否修复数据
        "repair_mode":"auto_repair/manual_confirm",
        "infos":[
            {
                "bill_id":11111, #关联的(数据复制)单据ID
                "src_cluster":"cache.src.testapp.db:50000", #源集群,来自于数据复制记录
                "src_instances":["all"], # 源实例列表
                "dst_cluster": "cache.dst.testapp.db:50001",#目的集群,来自于数据复制记录
                "key_white_regex":"*", #包含key
                "key_black_regex":"", #排除key
            }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_data_check_repair()
        return Response({"root_id": root_id})


class RedisAddDtsServerSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/redis_add_dts_server
    params:
    {
        "uid":"2022051612120001",
        "created_by":"xxxx",
        "bk_biz_id":3,
        "ticket_type":"REDIS_ADD_DTS_SERVER",
        "infos":[
            {"ip": "3.3.3.1", "bk_cloud_id": 0, "bk_host_id": 2,"bk_city_id":1,"bk_city_name":"上海"},
            {"ip": "3.3.3.2", "bk_cloud_id": 0, "bk_host_id": 2,"bk_city_id":2,"bk_city_name":"南京"}
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_add_dts_server()
        return Response({"root_id": root_id})


class RedisRemoveDtsServerSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/redis_remove_dts_server
    params:
    {
        "uid":"2022051612120001",
        "created_by":"xxxx",
        "bk_biz_id":3,
        "ticket_type":"REDIS_REMOVE_DTS_SERVER",
        "infos":[
            {"ip": "3.3.3.1", "bk_cloud_id": 0},
            {"ip": "3.3.3.2", "bk_cloud_id": 0}
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_remove_dts_server()
        return Response({"root_id": root_id})


class RedisDataStructureSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/redis_data_structure
        params:
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"admin",
        "ticket_type":"REDIS_DATA_STRUCTURE",
        "infos": [
          {
            "cluster_id": 1,
             "master_instance":[
                "127.0.0.1:30000", "127.0.0.1:30002"
            ],
            "recovery_time_point": "2022-12-12 11:11:11",
            "redis_data_structure_hosts": [
                {"ip": "3.3.3.1", "bk_cloud_id": 0, "bk_host_id": 2},
                {"ip": "3.3.3.2", "bk_cloud_id": 0, "bk_host_id": 2},
            ]
          }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_data_structure()
        return Response({"root_id": root_id})


class RedisDataStructureTaskDeleteSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/redis_data_structure
        params:
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"admin",
        "ticket_type":"REDIS_DATA_STRUCTURE",
        "infos": [
          {
            "cluster_id": 1,
             "master_instance":[
                "127.0.0.1:30000", "127.0.0.1:30002"
            ],
            "recovery_time_point": "2022-12-12 11:11:11",
            "redis_data_structure_hosts": [
                {"ip": "3.3.3.1", "bk_cloud_id": 0, "bk_host_id": 2},
                {"ip": "3.3.3.2", "bk_cloud_id": 0, "bk_host_id": 2},
            ]
          }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_data_structure_task_delete()
        return Response({"root_id": root_id})


class RedisClusterAddSlaveApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/redis_cluster_add_slave
    params:
    {
        "bk_biz_id": 3,
        "ticket_type":"REDIS_CLUSTER_ADD_SLAVE",
        "created_by":"admin",
        "uid":"1111",
        "infos": [
          {
            "cluster_id": 1,
            "pairs": [
                {
                  "redis_master": {"ip": "2.2.3.4", "bk_cloud_id": 0, "bk_host_id": 123},
                  "redis_slave": [{"ip": "2.2.3.4", "bk_cloud_id": 0, "bk_host_id": 123}]
                },
            ]
          }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_add_slave()
        return Response({"root_id": root_id})
