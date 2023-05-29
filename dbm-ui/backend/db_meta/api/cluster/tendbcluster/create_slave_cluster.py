"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.db import transaction
from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import ClusterEntry


@transaction.atomic
def slave_cluster_create_pre_check(slave_domain: str):
    """
    添加从集群的元信息前置检测
    """
    pre_check_errors = []

    # 域名唯一性检查
    if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=slave_domain).exists():
        pre_check_errors.append(_("域名 {} 已存在").format(slave_domain))

    if pre_check_errors:
        raise DBMetaException(message=", ".join(pre_check_errors))
