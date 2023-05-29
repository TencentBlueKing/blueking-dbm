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
from backend.db_meta.models import AppCache, DBModule
from backend.db_services.infras.host import get_city_code_name_map, get_spec_display_map


class TicketContext:
    def __init__(
        self,
        ticket=None,
    ):
        self.ticket = ticket
        self.city_map = get_city_code_name_map()
        self.spec_map = get_spec_display_map()
        self.db_config = {}

        bizs = list(AppCache.objects.all())
        self.biz_name_map = {biz.bk_biz_id: biz.bk_biz_name for biz in bizs}
        self.app_abbr_map = {biz.bk_biz_id: biz.db_app_abbr for biz in bizs}

        db_modules = list(DBModule.objects.all())
        self.db_module_map = {module.db_module_id: module.db_module_name for module in db_modules}
        self.db_module_id__biz_id_map = {module.db_module_id: module.bk_biz_id for module in db_modules}
