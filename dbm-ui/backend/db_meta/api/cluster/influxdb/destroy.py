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
from typing import List, Optional

from django.db import transaction
from django.utils.translation import ugettext as _

from backend import env
from backend.components import CCApi
from backend.configuration.constants import DBType
from backend.db_meta.api.common import del_service_instance
from backend.db_meta.api.db_module import delete_instance_modules
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import GroupInstance, StorageInstance

logger = logging.getLogger("root")


@transaction.atomic
def destroy(addresses: Optional[List]):
    """
    清理DBMeta
    """

    storages = StorageInstance.find_storage_instance_by_addresses(addresses)
    for storage in storages:
        GroupInstance.objects.get(instance_id=storage.id).delete()
        # 删除storage instance
        del_instance_id = storage.id
        storage.delete(keep_parents=True)
        if not storage.machine.storageinstance_set.exists():
            # 将主机转移到待回收模块下
            logger.info(_("将主机{}转移到待回收").format(storage.machine.ip))
            CCApi.transfer_host_to_recyclemodule(
                {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [storage.machine.bk_host_id]}
            )
            storage.machine.delete(keep_parents=True)
        else:
            del_service_instance(bk_instance_id=storage.bk_instance_id)
        # 删除模块
        delete_instance_modules(
            db_type=DBType.InfluxDB.value,
            del_instance_id=del_instance_id,
            bk_biz_id=storage.bk_biz_id,
            cluster_type=ClusterType.Influxdb.value,
        )
