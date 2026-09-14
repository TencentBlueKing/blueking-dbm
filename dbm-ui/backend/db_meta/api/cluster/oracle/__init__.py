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

from .change_password import ip_change_password
from .delete_cluster import oracle_delete_cluster
from .detail import scan_cluster, single_scan_cluster
from .primary_standby_create import create_oracle_instances, create_oracle_set, pkg_create_oracle
from .replace_primary_standby import new_machine, replace_instance, replace_primary_and_standby
from .replace_single_instance import replace_single_instance
from .replace_standby import replace_standby
from .swap_primary_standby import swap_primary_standby
