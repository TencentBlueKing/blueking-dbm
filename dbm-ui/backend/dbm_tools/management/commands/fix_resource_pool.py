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

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.components import CCApi
from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.utils import remove_cluster_ips
from backend.db_services.ipchooser.constants import CommonEnum
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = _("清理资源池主机")

    def add_arguments(self, parser):
        parser.add_argument("resource_mod", type=int, help=_("资源池模块ID"))

    def handle(self, *args, **options):
        resource_mod_id = options.get("resource_mod")

        resource_data = DBResourceApi.resource_list(params={"limit": 1000, "offset": 0})
        logger.info("resource: count=%s", resource_data["count"])

        host_in_use = [ri["bk_host_id"] for ri in resource_data.get("details", [])]

        resp = ResourceQueryHelper.query_cc_hosts(
            {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_inst_id": resource_mod_id, "bk_obj_id": "module"},
            [],
            0,
            1000,
            CommonEnum.DEFAULT_HOST_FIELDS.value,
            return_status=True,
            bk_cloud_id=0,
        )

        count, apply_data = resp["count"], list(filter(lambda x: x["status"] == 1, resp["info"]))

        free_hosts = list(filter(lambda x: x["bk_host_id"] not in host_in_use, apply_data))
        free_host_ids = [h["bk_host_id"] for h in free_hosts]
        free_host_ips = [h["bk_host_innerip"] for h in free_hosts]
        logger.info("clean: count=%s, details: %s", len(free_host_ips), free_host_ips)

        res = DBResourceApi.resource_delete(params={"bk_host_ids": free_host_ids}, raise_exception=False)
        logger.info("clean: res=%s", res)

        remove_cluster_ips(free_host_ips, False, True)

        CCApi.transfer_host_to_recyclemodule(
            {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": free_host_ids}, use_admin=True, raw=True
        )
