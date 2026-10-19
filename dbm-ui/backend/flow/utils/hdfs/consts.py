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
# HDFS 默认服务端口号
DATANODE_DEFAULT_PORT = 50010
NAME_NODE_DEFAULT_PORT = 53310
DATANODE_DEFAULT_RPC_PORT = 50020
# DATANODE_DEFAULT_SERVICE_RPC_PORT = 50010
DATANODE_DEFAULT_HTTP_PORT = 50075
JOURNAL_NODE_DEFAULT_PORT = 8485
ZOOKEEPER_DEFAULT_PORT = 2181

# HDFS集群主节点(active namenode)缓存key前缀
# 完整key格式: {CACHE_CLUSTER_MASTER}_{bk_biz_id}_{cluster_type}
# 由 db_periodic_task.local_tasks.hdfs.sync_cluster_master 定时任务写入
# 由 db_services.bigdata.hdfs.query.HDFSListRetrieveResource.get_clusters_master 读取
CACHE_CLUSTER_MASTER = "hdfs_cluster_master"
