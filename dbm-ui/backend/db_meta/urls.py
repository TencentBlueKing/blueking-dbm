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
from django.urls import path

from backend import env
from backend.db_meta import views

urlpatterns = []

# 此路由提供的接口仅限内部服务(dbha/dbpriv/...)使用
if env.SERVICE_ONLY:
    urlpatterns = [
        # 提供给 DBHA 专用接口
        path("dbha/cities", views.dbha.cities, name="dbha-cities"),
        path("dbha/instances", views.dbha.instances, name="dbha-instances"),
        path("dbha/update_status", views.dbha.update_status, name="dbha-update_status"),
        path("dbha/swap_role", views.dbha.swap_role, name="dbha-swap_role"),  # tendbha, tendbcluster-remote
        path("dbha/swap_ctl_role", views.dbha.swap_ctl_role, name="dbha-swap_ctl_role"),  # tendbcluster-spider
        path("dbha/tendis_cluster_swap", views.dbha.tendis_cluster_swap, name="dbha-tendis_cluster_swap"),
        path("dbha/entry_detail", views.dbha.entry_detail, name="dbha-entry_detail"),
        # 提供给 接入服务查询集群详情使用
        path(
            "meta/tendis_cluster_detail/<int:cluster_id>",
            views.meta.tendis_cluster_detail,
            name="tendis-cluster-detail",
        ),
        # 创建Nosql集群， 后边迁移数据用
        path(
            "meta/nosql/create_cluster",
            views.nosql.create_nosql_cluster,
            name="create-nosql-cluster",
        ),
        path(
            "priv_manager/mysql/tendbsingle/cluster_instances",
            views.priv_manager.mysql.tendbsingle_cluster_instances,
            name="priv_manager-mysql-tendbsingle-cluster_instances",
        ),
        path(
            "priv_manager/mysql/tendbha/cluster_instances",
            views.priv_manager.mysql.tendbha_cluster_instances,
            name="priv_manager-mysql-tendbha-cluster_instances",
        ),
        path(
            "priv_manager/mysql/tendbcluster/cluster_instances",
            views.priv_manager.mysql.tendbcluster_cluster_instances,
            name="priv_manager-mysql-tendbcluster-cluster_instances",
        ),
        path(
            "priv_manager/biz_clusters",
            views.priv_manager.biz_clusters,
            name="priv_manager-biz_clusters",
        ),
        # priv manager sqlserver_single
        path(
            "priv_manager/sqlserver_single/cluster_instances",
            views.priv_manager.sqlserver_single_cluster_instances,
            name="priv-manager-sqlserver-single-cluster_instances",
        ),
        # priv manager sqlserver_ha
        path(
            "priv_manager/sqlserver_ha/cluster_instances",
            views.priv_manager.sqlserver_ha_cluster_instances,
            name="priv-manager-sqlserver_ha-cluster_instances",
        ),
    ]
