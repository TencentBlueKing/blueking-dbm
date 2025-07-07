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
import copy
import logging
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.mysql.autofix.mysql_autofix_todo_register import (
    MySQLAutofixTodoRegisterComponent,
)

logger = logging.getLogger("flow")


class MySQLDBHAAutofixTodoRegisterFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def autofix_register(self):
        """
        self.data = {
            "infos": [{
                    bk_cloud_id = models.IntegerField(default=0)
                    bk_biz_id = models.IntegerField(default=0)
                    check_id = models.IntegerField
                    immute_domain = models.CharField(max_length=255, default="")
                    machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), default="")
                    ip = models.GenericIPAddressField(default="")
                    port = models.IntegerField(default=0)
                    event_create_time = models.DateTimeField()
            }, ...]
        }
        """
        autofix_pipe = Builder(root_id=self.root_id, data=self.data)
        autofix_pipe.add_act(
            act_name=_("写自愈信息"),
            act_component_code=MySQLAutofixTodoRegisterComponent.code,
            kwargs={**copy.deepcopy(self.data)},
        )
        logger.info(_("构建MySQL自愈信息写入流程成功"))
        autofix_pipe.run_pipeline()
