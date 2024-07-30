"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class ClonePrivRulesToOtherService(BaseService):
    """
    克隆权限规则到其他业务
    """

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        target_biz_id = kwargs.get("target_biz_id")
        source_biz = kwargs.get("source_biz")

        param = {"source_biz": source_biz, "target_biz": target_biz_id, "cluster_type": "tendbha"}

        try:
            DBPrivManagerApi.clone_account_rule(param)
            self.log_info(_("从{}复制权限规则到业务{}成功").format(source_biz, target_biz_id))
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("复制权限规则异常，相关信息: {}").format(e))
            return False

        return True


class ClonePrivRulesToOtherComponent(Component):
    name = __name__
    code = "clone_priv_rules_to_other"
    bound_service = ClonePrivRulesToOtherService
