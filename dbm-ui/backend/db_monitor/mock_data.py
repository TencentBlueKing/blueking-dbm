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

from django.utils.translation import ugettext_lazy as _

GET_MESSAGE_TYPE = [
    {"type": "rtx", "label": _("企业微信"), "is_active": True, "icon": "base64xxxxxxx"},
    {"type": "weixin", "label": _("微信"), "is_active": False, "icon": "base64xxxxxxx"},
    {"type": "mail", "label": _("邮件"), "is_active": True, "icon": "base64xxxxxxx"},
    {"type": "sms", "label": _("短信"), "is_active": True, "icon": "base64xxxxxxx"},
    {"type": "voice", "label": _("语音"), "is_active": True, "icon": "base64xxxxxxx"},
    {"type": "wxwork-bot", "label": _("群机器人"), "is_active": True, "icon": "base64xxxxxxx"},
]

GET_RECEIVER_GROUP = [
    {"id": "bk_biz_maintainer", "display_name": _("运维人员"), "logo": "", "type": "group", "members": ["admin"]},
    {"id": "bk_biz_productor", "display_name": _("产品人员"), "logo": "", "type": "group", "members": []},
    {"id": "bk_biz_tester", "display_name": _("测试人员"), "logo": "", "type": "group", "members": []},
    {"id": "bk_biz_developer", "display_name": _("开发人员"), "logo": "", "type": "group", "members": []},
    {"id": "operator", "display_name": _("主负责人"), "logo": "", "type": "group", "members": []},
    {"id": "bk_bak_operator", "display_name": _("备份负责人"), "logo": "", "type": "group", "members": []},
]

NOTICE_GROUP_DETAIL = {
    "alert_notice": [
        {
            "time_range": "00:00:00--11:59:00",
            "notify_config": [
                {
                    "notice_ways": [{"name": "weixin"}],
                    "level": 3,
                },
                {
                    "notice_ways": [{"name": "mail"}],
                    "level": 2,
                },
                {
                    "notice_ways": [{"name": "rtx"}, {"name": "voice"}],
                    "level": 1,
                },
            ],
        },
        {
            "time_range": "12:00:00--23:59:00",
            "notify_config": [
                {
                    "notice_ways": [{"name": "weixin"}],
                    "level": 3,
                },
                {
                    "notice_ways": [{"name": "wxwork-bot", "receivers": ["123"]}],
                    "level": 2,
                },
                {
                    "notice_ways": [{"name": "rtx"}, {"name": "voice"}],
                    "level": 1,
                },
            ],
        },
    ]
}

LIST_NOTICE_GROUP = {
    "count": 2,
    "results": [
        {
            "id": 1,
            "name": "MySQL DBA",
            "updater": "admin",
            "update_at": "2023-08-29 15:36:53",
            "bk_biz_id": 0,
            "monitor_group_id": 0,
            "related_policy_count": 1,
            "group_type": "PLATFORM",
            "db_type": "mysql",
            "receivers": [{"type": "group", "id": "bk_biz_maintainer"}, {"type": "user", "id": "admin"}],
            "details": {
                "alert_notice": [
                    {
                        "time_range": "00:00:00--23:59:00",
                        "notify_config": [
                            {
                                "notice_ways": [{"name": "weixin"}],
                                "level": 3,
                            },
                            {
                                "notice_ways": [{"name": "mail"}],
                                "level": 2,
                            },
                            {
                                "notice_ways": [{"name": "rtx"}, {"name": "voice"}],
                                "level": 1,
                            },
                        ],
                    }
                ]
            },
            "is_built_in": True,
        },
        {
            "id": 2,
            "name": _("自定义告警组名称"),
            "updater": "admin",
            "update_at": "2023-08-29 15:36:53",
            "bk_biz_id": 0,
            "monitor_group_id": 0,
            "related_policy_count": 2,
            "group_type": "PLATFORM",
            "db_type": "mysql",
            "receivers": [{"type": "user", "id": "admin"}],
            "details": copy.deepcopy(NOTICE_GROUP_DETAIL),
            "is_built_in": False,
        },
    ],
}

CREATE_NOTICE_GROUP = {
    "name": _("新建告警组"),
    "receivers": [{"type": "group", "id": "bk_biz_maintainer"}, {"type": "user", "id": "admin"}],
    "details": copy.deepcopy(NOTICE_GROUP_DETAIL),
}

UPDATE_NOTICE_GROUP = {"id": 1, **CREATE_NOTICE_GROUP}

GET_RELATED_POLICY = [{"id": 1, "name": _("策略 A")}, {"id": 2, "name": _("策略 B")}]

CREATE_DUTY_RULE = {
    "name": _("周末轮值"),
    "duty_type": "periodic",
    "duty_biz_list": [],
    "ignore_biz_list": [],
    "members": ["admin"],
    "shift_number": 2,
    "shift_day": 1,
    "start_time": "2023-09-05",
    "end_time": "2023-10-31",
    "work_type": "daily",
    "work_days": [6, 7],
    "work_times": ["00:00--11:59", "12:00--23:59"],
}

# bk monitor api
BK_MONITOR_CREATE_NOTICE_GROUP_REQUEST = {
    "name": "durant0905",
    "desc": "",
    "need_duty": False,
    "duty_arranges": [
        {
            "duty_type": "always",
            "work_time": "always",
            "users": [{"display_name": "admin", "logo": "", "id": "admin", "type": "user"}],
        }
    ],
    "alert_notice": [
        {
            "time_range": "00:00:00--17:59:00",
            "notify_config": [
                {"level": 3, "notice_ways": [{"name": "rtx"}, {"name": "wxwork-bot", "receivers": ["123"]}]},
                {"level": 2, "notice_ways": [{"name": "rtx"}]},
                {"level": 1, "notice_ways": [{"name": "rtx"}]},
            ],
        },
        {
            "time_range": "18:00:00--23:59:00",
            "notify_config": [
                {"level": 3, "notice_ways": [{"name": "rtx"}]},
                {"level": 2, "notice_ways": [{"name": "rtx"}]},
                {"level": 1, "notice_ways": [{"name": "rtx"}]},
            ],
        },
    ],
    "action_notice": [
        {
            "time_range": "00:00:00--23:59:00",
            "notify_config": [
                {"level": 3, "notice_ways": [{"name": "rtx"}], "phase": 3},
                {"level": 2, "notice_ways": [{"name": "rtx"}], "phase": 2},
                {"level": 1, "notice_ways": [{"name": "rtx"}], "phase": 1},
            ],
        }
    ],
    "channels": ["user", "wxwork-bot"],
    "bk_biz_id": 5005578,
}

BK_MONITOR_NOTICE_GROUP_DETAIL = {
    "id": 29,
    "name": _("mysql 周末轮值 告警组"),
    "bk_biz_id": 3,
    "desc": "",
    "update_user": "admin",
    "update_time": "2023-08-28 12:02:27+0800",
    "create_user": "admin",
    "create_time": "2023-08-23 17:53:46+0800",
    "duty_arranges": [
        {
            "id": 35,
            "user_group_id": 29,
            "need_rotation": True,
            "duty_time": [{"work_type": "weekly", "work_days": [6, 7], "work_time": "00:00--23:59"}],
            "effective_time": "2023-08-28t12:02:00+08:00",
            "handoff_time": {"date": 1, "time": "00:00", "rotation_type": "daily"},
            "users": [],
            "duty_users": [
                [{"id": "durant", "display_name": "durant", "type": "user"}],
                [{"id": "edwin", "display_name": "edwin", "type": "user"}],
                [{"id": "hongsong", "display_name": "hongsong", "type": "user"}],
                [{"id": "kio", "display_name": "kio", "type": "user"}],
            ],
            "backups": [],
            "order": 1,
        },
        {
            "id": 36,
            "user_group_id": 29,
            "need_rotation": True,
            "duty_time": [{"work_type": "weekly", "work_days": [6, 7], "work_time": "00:00--23:59"}],
            "effective_time": "2023-08-28t12:02:00+08:00",
            "handoff_time": {"date": 1, "time": "00:00", "rotation_type": "daily"},
            "users": [],
            "duty_users": [
                [{"id": "hongsong", "display_name": "hongsong", "type": "user"}],
                [{"id": "kio", "display_name": "kio", "type": "user"}],
                [{"id": "durant", "display_name": "durant", "type": "user"}],
                [{"id": "edwin", "display_name": "edwin", "type": "user"}],
            ],
            "backups": [],
            "order": 2,
        },
    ],
    "alert_notice": [
        {
            "time_range": "00:00:00--23:59:00",
            "notify_config": [
                {"type": [], "notice_ways": [{"name": "weixin", "receivers": []}], "level": 3},
                {"type": [], "notice_ways": [{"name": "weixin", "receivers": []}], "level": 2},
                {"type": [], "notice_ways": [{"name": "weixin", "receivers": []}], "level": 1},
            ],
        }
    ],
    "action_notice": [
        {
            "time_range": "00:00:00--23:59:00",
            "notify_config": [
                {"type": [], "notice_ways": [{"name": "weixin", "receivers": []}], "phase": 3},
                {"type": [], "notice_ways": [{"name": "weixin", "receivers": []}], "phase": 2},
                {"type": [], "notice_ways": [{"name": "weixin", "receivers": []}], "phase": 1},
            ],
        }
    ],
    "need_duty": True,
    "path": "",
    "channels": ["user"],
    "users": [],
    "strategy_count": 1,
    "delete_allowed": False,
    "edit_allowed": True,
    "config_source": "ui",
    "duty_plans": [
        {
            "id": 365,
            "user_group_id": 29,
            "duty_arrange_id": 35,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-04 00:00:00+0800",
            "end_time": "2023-09-05 00:00:00+0800",
            "users": [{"id": "kio", "display_name": "kio", "type": "user"}],
            "order": 1,
            "is_active": False,
        },
        {
            "id": 390,
            "user_group_id": 29,
            "duty_arrange_id": 35,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-05 00:00:00+0800",
            "end_time": "2023-09-06 00:00:00+0800",
            "users": [{"id": "durant", "display_name": "durant", "type": "user"}],
            "order": 1,
            "is_active": False,
        },
        {
            "id": 391,
            "user_group_id": 29,
            "duty_arrange_id": 35,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-06 00:00:00+0800",
            "end_time": "2023-09-07 00:00:00+0800",
            "users": [{"id": "edwin", "display_name": "edwin", "type": "user"}],
            "order": 1,
            "is_active": False,
        },
        {
            "id": 392,
            "user_group_id": 29,
            "duty_arrange_id": 35,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-07 00:00:00+0800",
            "end_time": "2023-09-08 00:00:00+0800",
            "users": [{"id": "hongsong", "display_name": "hongsong", "type": "user"}],
            "order": 1,
            "is_active": False,
        },
        {
            "id": 393,
            "user_group_id": 29,
            "duty_arrange_id": 35,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-08 00:00:00+0800",
            "end_time": "2023-09-09 00:00:00+0800",
            "users": [{"id": "kio", "display_name": "kio", "type": "user"}],
            "order": 1,
            "is_active": False,
        },
        {
            "id": 369,
            "user_group_id": 29,
            "duty_arrange_id": 36,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-04 00:00:00+0800",
            "end_time": "2023-09-05 00:00:00+0800",
            "users": [{"id": "edwin", "display_name": "edwin", "type": "user"}],
            "order": 2,
            "is_active": False,
        },
        {
            "id": 394,
            "user_group_id": 29,
            "duty_arrange_id": 36,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-05 00:00:00+0800",
            "end_time": "2023-09-06 00:00:00+0800",
            "users": [{"id": "hongsong", "display_name": "hongsong", "type": "user"}],
            "order": 2,
            "is_active": False,
        },
        {
            "id": 395,
            "user_group_id": 29,
            "duty_arrange_id": 36,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-06 00:00:00+0800",
            "end_time": "2023-09-07 00:00:00+0800",
            "users": [{"id": "kio", "display_name": "kio", "type": "user"}],
            "order": 2,
            "is_active": False,
        },
        {
            "id": 396,
            "user_group_id": 29,
            "duty_arrange_id": 36,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-07 00:00:00+0800",
            "end_time": "2023-09-08 00:00:00+0800",
            "users": [{"id": "durant", "display_name": "durant", "type": "user"}],
            "order": 2,
            "is_active": False,
        },
        {
            "id": 397,
            "user_group_id": 29,
            "duty_arrange_id": 36,
            "duty_time": [{"work_days": [6, 7], "work_time": "00:00--23:59", "work_type": "weekly"}],
            "begin_time": "2023-09-08 00:00:00+0800",
            "end_time": "2023-09-09 00:00:00+0800",
            "users": [{"id": "edwin", "display_name": "edwin", "type": "user"}],
            "order": 2,
            "is_active": False,
        },
    ],
    "rule_count": 1,
}
