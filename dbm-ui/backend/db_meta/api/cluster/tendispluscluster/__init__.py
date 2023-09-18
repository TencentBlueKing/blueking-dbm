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
from backend.db_meta.api.cluster.nosqlcomm.cc_ops import cc_add_service_instance, cc_add_service_instances
from backend.db_meta.api.cluster.nosqlcomm.decommission import (
    decommission_cluster,
    decommission_proxies,
    decommission_tendis,
)
from backend.db_meta.api.cluster.nosqlcomm.scale_proxy import add_proxies, delete_proxies
from backend.db_meta.api.cluster.nosqlcomm.scale_tendis import make_sync_mms, redo_slaves, switch_tendis

from .create import create
from .detail import scan_cluster
