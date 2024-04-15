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

MOCK_SAVE_DUTY_RULE_RETURN = {
    "id": 17,
    "bk_biz_id": 2,
    "name": "handoff duty",
    "labels": ["mysql", "redis", "business"],
    "effective_time": "2023-07-25 11:00:00",
    "end_time": "",
    "category": "handoff",
    "enabled": True,
    "hash": "fb44e5e5b4b8eec86d65d6f6e34fd8e6",
    "duty_arranges": [
        {
            "id": 4375,
            "user_group_id": None,
            "duty_rule_id": 17,
            "need_rotation": False,
            "duty_time": [
                {
                    "is_custom": False,
                    "work_type": "daily",
                    "work_days": [],
                    "work_time_type": "time_range",
                    "work_time": ["00:00--23:59"],
                    "period_settings": {"duration": 2, "window_unit": "day"},
                }
            ],
            "effective_time": None,
            "handoff_time": {},
            "users": [],
            "duty_users": [
                [
                    {"id": "admin", "display_name": "管理员", "type": "user"},
                    {"id": "admin1", "display_name": "admin1", "type": "user"},
                    {"id": "admin2", "display_name": "admin2", "type": "user"},
                    {"id": "admin3", "display_name": "admin3", "type": "user"},
                    {"id": "admin4", "display_name": "admin4", "type": "user"},
                    {"id": "admin5", "display_name": "admin5", "type": "user"},
                ]
            ],
            "backups": [],
            "order": 1,
            "hash": "022e266708d9091a1f61d2c640d79cbd",
            "group_type": "auto",
            "group_number": 2,
        }
    ],
    "create_time": "2024-04-07 17:17:04+0800",
    "create_user": "admin",
    "update_time": "2024-04-07 17:17:04+0800",
    "update_user": "admin",
    "code_hash": "",
    "app": "",
    "path": "",
    "snippet": "",
    "user_groups": [],
    "user_groups_count": 0,
    "delete_allowed": True,
    "edit_allowed": True,
}

MOCK_SAVE_USER_GROUP_RETURN = {"id": 0}

TEST_BK_BIZ_ID = 1
TEST_DB_TYPE = "mysql"


class BKMonitorV3MockApi:
    save_duty_rule_return = copy.deepcopy(MOCK_SAVE_DUTY_RULE_RETURN)
    save_user_group_return = copy.deepcopy(MOCK_SAVE_USER_GROUP_RETURN)
    delete_user_groups_return = None
    search_user_groups_return = None
    delete_duty_rules_return = None

    def __init__(
        self,
        save_duty_rule_return=None,
        save_user_group_return=None,
    ):
        self.save_duty_rule_return = save_duty_rule_return or self.save_duty_rule_return
        self.save_user_group_return = save_user_group_return or self.save_user_group_return

    @classmethod
    def save_duty_rule(cls, *args, **kwargs):
        return cls.save_duty_rule_return

    @classmethod
    def delete_duty_rules(cls, *args, **kwargs):
        return cls.delete_duty_rules_return

    @classmethod
    def save_user_group(cls, *args, **kwargs):
        return cls.save_user_group_return

    @classmethod
    def search_user_groups(cls, *args, **kwargs):
        return cls.search_user_groups_return

    @classmethod
    def delete_user_groups(cls, *args, **kwargs):
        return cls.delete_user_groups_return
