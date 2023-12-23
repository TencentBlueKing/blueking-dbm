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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("flow")


class TransferHostService(BaseService):
    """将主机转移对应的模块下"""

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        bk_biz_id = kwargs["bk_biz_id"]
        bk_module_ids = kwargs["bk_module_ids"]
        bk_host_ids = kwargs["bk_host_ids"]
        update_host_properties = kwargs.get("update_host_properties", None)
        try:
            cc_manage = CcManage(bk_biz_id=bk_biz_id)
            cc_manage.transfer_host_module(
                bk_host_ids=bk_host_ids, target_module_ids=bk_module_ids, update_host_properties=update_host_properties
            )
            return True
        except Exception as err:  # pylint: disable=broad-except
            self.log_error(_("主机{}转移目标模块{}失败, {}").format(bk_host_ids, bk_module_ids, err))
            return False


class TransferHostServiceComponent(Component):
    name = __name__
    code = "transfer_host_service"
    bound_service = TransferHostService
