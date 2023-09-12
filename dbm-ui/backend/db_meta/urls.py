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
        # 提供给 DBPRIV 使用, 老版本 api, 等待废弃
        path(
            "priv_manager/cluster_instances",
            views.priv_manager.cluster_instances,
            name="priv_manager-cluster_instances",
        ),
        path(
            "priv_manager/instance_detail",
            views.priv_manager.instance_detail,
            name="priv_manager-instance_detail",
        ),
        path(
            "priv_manager/biz_clusters",
            views.priv_manager.biz_clusters,
            name="priv_manager-biz_clusters",
        ),
        # priv manager tendbcluster
        path(
            "priv_manager/tendbcluster/cluster_instances",
            views.priv_manager.tendbcluster_cluster_instances,
            name="priv-manager-tendbcluster-cluster_instances",
        ),
        path(
            "priv_manager/tendbcluster/instance_detail",
            views.priv_manager.tendbcluster_instance_detail,
            name="priv_manager-tendbcluster-instance_detail",
        ),
        path(
            "priv_manager/tendbcluster/biz_clusters",
            views.priv_manager.tendbcluster_biz_clusters,
            name="priv_manager-tendbcluster-biz_clusters",
        ),
        # priv manager tendbha
        path(
            "priv_manager/tendbha/cluster_instances",
            views.priv_manager.tendbha_cluster_instances,
            name="priv-manager-tendbha-cluster_instances",
        ),
        path(
            "priv_manager/tendbha/instance_detail",
            views.priv_manager.tendbha_instance_detail,
            name="priv_manager-tendbha-instance_detail",
        ),
        path(
            "priv_manager/tendbha/biz_clusters",
            views.priv_manager.tendbha_biz_clusters,
            name="priv_manager-tendbha-biz_clusters",
        ),
        # priv manager tendbsingle
        path(
            "priv_manager/tendbsingle/cluster_instances",
            views.priv_manager.tendbsingle_cluster_instances,
            name="priv-manager-tendbsingle-cluster_instances",
        ),
        path(
            "priv_manager/tendbsingle/instance_detail",
            views.priv_manager.tendbsingle_instance_detail,
            name="priv_manager-tendbsingle-instance_detail",
        ),
        path(
            "priv_manager/tendbsingle/biz_clusters",
            views.priv_manager.tendbsingle_biz_clusters,
            name="priv_manager-tendbsingle-biz_clusters",
        ),
        path(
            "fake/tendbha/create_cluster", views.fake.fake_create_tendbha_cluster, name="fake-tendbha-create_cluster"
        ),
        path(
            "fake/tendbsingle/create_cluster",
            views.fake.fake_create_tendbsingle,
            name="fake-tendbsingle-create_cluster",
        ),
        path(
            "fake/tendbha/reset_cluster",
            views.fake.fake_reset_tendbha_cluster,
            name="fake-tendbha-reset_cluster",
        ),
        path(
            "fake/tendbcluster/reset_cluster",
            views.fake.fake_reset_tendbcluster_cluster,
            name="fake-tendbcluster-reset_cluster",
        ),
    ]
