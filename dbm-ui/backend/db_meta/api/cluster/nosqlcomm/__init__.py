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
from .cc_ops import cc_add_instance, cc_add_instances, cc_del_module, cc_del_service_instances, cc_transfer_idle
from .create_cluster import (
    create_twemproxy_cluster,
    pkg_create_twemproxy_cluster,
    update_cluster_type,
    update_storage_cluster_type,
)
from .create_instances import create_mongo_instances, create_proxies, create_tendis_instances
from .decommission import decommission_cluster, decommission_instances, decommission_proxies, decommission_tendis
from .detail_cluster import scan_cluster
from .other import get_cluster_detail, get_clusters_details
from .precheck import (
    before_create_domain_precheck,
    before_create_proxy_precheck,
    before_create_storage_precheck,
    create_domain_precheck,
    create_precheck,
    create_proxies_precheck,
    create_storage_precheck,
)
from .scale_proxy import add_proxies, delete_proxies
from .scale_tendis import make_sync, make_sync_mms, make_sync_msms, precheck, redo_slaves, switch_tendis
