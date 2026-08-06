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
from typing import Dict, List, Union

from iam import Resource
from iam.eval.constants import KEYWORD_BK_IAM_PATH

from backend.components.iamv4.client import IAMV4Api
from backend.iam_app.dataclass.actions import ActionMeta
from backend.iam_app.handlers.backends.base import IAMBackend

logger = logging.getLogger("root")


class IAMV4Backend(IAMBackend):
    """基于 IAMV4Api 的 V4 鉴权后端"""

    @staticmethod
    def make_resource(action: ActionMeta, resources: List[Resource]) -> Union[Dict, None]:
        """
        构造V4的鉴权资源。V4一个动作只关联一个资源类型，多资源动作要按V4声明的类型挑选，
        """
        resource_type = action.get_related_resource_type_v4()
        if not resource_type or not resources:
            return None

        # 只取一个资源，V4限定只有action之关联一种资源
        resource = next((item for item in resources if item.type == resource_type.id), None)
        if not resource:
            logger.warning("[iam_v4] action(%s) expects resource(%s) but not given", action.id, resource_type.id)
            return None

        auth_resource = {"id": str(resource.id)}
        bk_iam_path = (resource.attribute or {}).get(KEYWORD_BK_IAM_PATH)
        if bk_iam_path:
            auth_resource["attributes"] = {KEYWORD_BK_IAM_PATH: bk_iam_path}
        return auth_resource

    def is_allowed(self, username: str, action: ActionMeta, resources: List[Resource]) -> bool:
        # TODO: 这些动作的资源存在多平行父级，暂未注册到V4(见06文档B1)，先放行，待IAM支持拓扑后移除
        if action.is_disabled_v4():
            logger.warning("[iam_v4] action(%s) is not registered in V4, allowed by default", action.id)
            return True

        params = {"subject": {"type": "user", "id": username}, "action_id": action.id}
        # 无关资源类型的动作不传resource
        auth_resource = self.make_resource(action, resources)
        if auth_resource:
            params["resource"] = auth_resource

        data = self.call_with_retry(IAMV4Api.direct_auth, params=params, default=None)
        return bool((data or {}).get("allowed"))

    def abc(self, a, b, c):
        pass
