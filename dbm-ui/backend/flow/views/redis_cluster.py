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


class RedisClusterDtsSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/redis_cluster_dts
    params:
         {
        "uid":"2022051612120001",
        "created_by":"xxxx",
        "bk_biz_id":2005000194,
        "ticket_type":"REDIS_NEW_DTS_JOB",
        "dts_bill_type":"cluster_nodes_num_update/cluster_type_update/cluster_data_copy",
        # dts_copy_type值为:
        # - one_app_diff_cluster
        # - diff_app_diff_cluster
        # - copy_from_rollback_temp
        # - copy_to_other_system
        # - user_built_to_dbm
        "dts_copy_type":"one_app_diff_cluster",
        "online_switch":{
            "type":"auto/user_confirm"
        }
        "datacheck":true/false,
        "datarepair":true/false,
        "datarepair_mode":"auto/user_confirm",
        "rules":[
            {
                #dts_copy_type=user_built_to_dbm,src_cluster值就是源redis addr信息,如 1.1.1.1:6379; 其他情况下填源redis的domain;
                "src_cluster":"cache.luketest101.dba.db:50000",
                #dts_copy_type=user_built_to_dbm,src_cluster_type值必须为 RedisInstance or RedisCluster;其他时候值为空;
                "src_cluster_type":"",
                #dts_copy_type=user_built_to_dbm,src_cluster_password必须填值;否则为空;
                "src_cluster_password":"",
                #dts_copy_type=copy_from_rollback_temp时,src_rolback_bill_id才有值,其余为空
                "src_rolback_bill_id":0,
                #dts_copy_type=copy_from_rollback_temp时,src_rollback_instances才有值,其余为空
                "src_rollback_instances":"",
                #目的集群业务id,默认和bk_biz_id保持一致,只有当dts_copy_type=diff_app_diff_cluster时,才不同;
                "dst_bk_biz_id": 0,
                #dts_copy_type=sync_to_other_system,dst_cluster值就是目的redis addr信息,
                #如2.2.2.2:6379; 其他情况下填目的redis的domain;
                "dst_cluster":"tendisplus.luketest201.dba.db:50000",
                #dts_copy_type=sync_to_other_system必须填值;否则为空;
                "dst_cluster_password":"",
                "key_white_regex":"*", #包含key
                "key_black_regex":"", #排除key
            }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_dts()
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
