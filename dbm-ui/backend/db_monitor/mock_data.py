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

CREATE_NOTICE_GROUP = [
    {
        "name": _("新建告警组1"),
        "bk_biz_id": 0,
        "receivers": [{"type": "group", "id": "bk_biz_maintainer"}, {"type": "user", "id": "admin"}],
        "details": copy.deepcopy(NOTICE_GROUP_DETAIL),
    },
    {
        "name": _("新建告警组2"),
        "bk_biz_id": 0,
        "receivers": [{"type": "group", "id": "bk_biz_maintainer"}, {"type": "user", "id": "admin"}],
        "details": copy.deepcopy(NOTICE_GROUP_DETAIL),
    },
]

UPDATE_NOTICE_GROUP = {"id": 1, **CREATE_NOTICE_GROUP[0], **{"name": _("更新告警组")}}

GET_RELATED_POLICY = [{"id": 1, "name": _("策略 A")}, {"id": 2, "name": _("策略 B")}]

CREATE_HANDOFF_DUTY_RULE = {
    "name": _("周末轮值"),
    "priority": 1,
    "db_type": "mysql",
    "category": "handoff",
    "effective_time": "2023-09-05 00:00:00",
    "duty_arranges": [
        {
            "duty_number": 2,
            "duty_day": 1,
            "members": ["admin"],
            "work_type": "weekly",
            "work_days": [6, 7],
            "work_times": ["00:00--11:59", "12:00--23:59"],
        }
    ],
}

CREATE_CUSTOM_DUTY_RULE = {
    "name": _("固定排班"),
    "priority": 2,
    "db_type": "redis",
    "category": "regular",
    "effective_time": "2023-10-01 00:00:00",
    "end_time": "2023-10-03 00:00:00",
    "duty_arranges": [
        {"date": "2023-10-01", "work_times": ["00:00--11:59", "12:00--23:59"], "members": ["admin"]},
        {"date": "2023-10-02", "work_times": ["08:00--18:00"], "members": ["admin"]},
        {"date": "2023-10-03", "work_times": ["00:00--11:59", "12:00--23:59"], "members": ["admin"]},
    ],
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

CALLBACK_REQUEST = {
    "appointees": "admin,leader",
    "callback_message": {
        "type": "anomaly_notice",
        "scenario": "os",
        "bk_biz_id": 3,
        "bk_biz_name": "dba",
        "event": {
            "id": "171170504652154",
            "event_id": "171170504652154",
            "is_shielded": False,
            "begin_time": "2024-03-29 09:33:00",
            "create_time": "2024-03-29 09:37:26",
            "end_time": None,
            "level": 1,
            "level_name": "致命",
            "agg_dimensions": [
                "instance_role",
                "device_name",
                "app",
                "bk_target_ip",
                "cluster_domain",
                "bk_target_cloud_id",
                "appid",
            ],
            "dimensions": {
                "cluster_domain": "example.domain.db",
                "bk_target_ip": "127.0.0.1",
                "appid": "3",
                "instance_role": "backend_slave",
                "app": "dba",
                "device_name": "/dev/vda1",
                "bk_target_cloud_id": "0",
                "bk_topo_node": ["biz|3", "set|5", "module|1195"],
                "bk_host_id": 1,
            },
            "dimension_translation": {
                "cluster_domain": {
                    "value": "example.domain.db",
                    "display_name": "dbm_meta cluster domain",
                    "display_value": "example.domain.db",
                },
                "bk_target_ip": {"value": "127.0.0.1", "display_name": "目标ip", "display_value": "127.0.0.1"},
                "appid": {"value": "3", "display_name": "dbm_meta app id", "display_value": "3"},
                "instance_role": {
                    "value": "backend_slave",
                    "display_name": "dbm_meta instance role",
                    "display_value": "backend_slave",
                },
                "app": {"value": "dba", "display_name": "dbm_meta app", "display_value": "dba"},
                "device_name": {"value": "/dev/vda1", "display_name": "设备名", "display_value": "/dev/vda1"},
                "bk_target_cloud_id": {"value": "0", "display_name": "云区域id", "display_value": "0"},
                "bk_topo_node": {
                    "value": ["biz|3", "set|5", "module|1195"],
                    "display_name": "拓扑节点",
                    "display_value": [
                        {"bk_obj_name": "业务", "bk_inst_name": "dba"},
                        {"bk_obj_name": "集群", "bk_inst_name": "db.mysql.mysql"},
                        {"bk_obj_name": "模块", "bk_inst_name": "example.domain.db"},
                    ],
                },
                "bk_host_id": {"value": 387, "display_name": "主机", "display_value": "127.0.0.1"},
            },
        },
        "strategy": {
            "id": 46650,
            "name": "mysql 主机磁盘空间使用率cc",
            "scenario": "os",
            "item_list": [
                {
                    "metric_field": "in_use",
                    "metric_field_name": "avg(磁盘空间使用率)",
                    "data_source_label": "bk_monitor",
                    "data_source_name": "监控平台",
                    "data_type_label": "time_series",
                    "data_type_name": "时序",
                    "metric_id": "bk_monitor.dbm_system.disk.in_use",
                }
            ],
        },
        "latest_anomaly_record": {
            "anomaly_id": "cc3d7ce5fb78f1f0b928b65f5e536bfa",
            "source_time": "2024-03-29 09:36:00",
            "create_time": "2024-03-29 09:37:25",
            "origin_alarm": {
                "trigger_time": 1711705045,
                "data": {
                    "time": 1711704960,
                    "value": 9.759688,
                    "values": {"in_use": 0, "_result_": 9.759688, "time": 1711704960},
                    "dimensions": {
                        "cluster_domain": "example.domain.db",
                        "bk_target_ip": "127.0.0.1",
                        "appid": "3",
                        "instance_role": "backend_slave",
                        "app": "dba",
                        "device_name": "/dev/vda1",
                        "bk_target_cloud_id": "0",
                        "bk_topo_node": ["biz|3", "set|5", "module|1195"],
                        "bk_host_id": 387,
                    },
                    "record_id": "ce266d85bd01a4a50ba33d0acde845a0.1711704960",
                    "dimension_fields": [
                        "cluster_domain",
                        "bk_target_ip",
                        "appid",
                        "instance_role",
                        "app",
                        "device_name",
                        "bk_target_cloud_id",
                    ],
                    "access_time": 1711705045.0090528,
                    "detect_time": 1711705045.618694,
                },
                "trigger": {
                    "level": "1",
                    "anomaly_ids": [
                        "ce266d85bd01a4a50ba33d0acde845a0.1711704720.46650.46650.1",
                        "ce266d85bd01a4a50ba33d0acde845a0.1711704780.46650.46650.1",
                        "ce266d85bd01a4a50ba33d0acde845a0.1711704840.46650.46650.1",
                        "ce266d85bd01a4a50ba33d0acde845a0.1711704900.46650.46650.1",
                        "ce266d85bd01a4a50ba33d0acde845a0.1711704960.46650.46650.1",
                    ],
                },
                "anomaly": {
                    "1": {
                        "anomaly_message": "avg(磁盘空间使用率) >= 2.0%, 当前值9.759688%",
                        "anomaly_id": "ce266d85bd01a4a50ba33d0acde845a0.1711704960.46650.46650.1",
                        "anomaly_time": "2024-03-29 09:37:25",
                    },
                    "2": {
                        "anomaly_message": "avg(磁盘空间使用率) >= 1.0%, 当前值9.759688%",
                        "anomaly_id": "ce266d85bd01a4a50ba33d0acde845a0.1711704960.46650.46650.2",
                        "anomaly_time": "2024-03-29 09:37:25",
                    },
                },
                "dimension_translation": {
                    "cluster_domain": {
                        "value": "example.domain.db",
                        "display_name": "dbm_meta cluster domain",
                        "display_value": "example.domain.db",
                    },
                    "bk_target_ip": {"value": "127.0.0.1", "display_name": "目标ip", "display_value": "127.0.0.1"},
                    "appid": {"value": "3", "display_name": "dbm_meta app id", "display_value": "3"},
                    "instance_role": {
                        "value": "backend_slave",
                        "display_name": "dbm_meta instance role",
                        "display_value": "backend_slave",
                    },
                    "app": {"value": "dba", "display_name": "dbm_meta app", "display_value": "dba"},
                    "device_name": {"value": "/dev/vda1", "display_name": "设备名", "display_value": "/dev/vda1"},
                    "bk_target_cloud_id": {"value": "0", "display_name": "云区域id", "display_value": "0"},
                    "bk_topo_node": {
                        "value": ["biz|3", "set|5", "module|1195"],
                        "display_name": "拓扑节点",
                        "display_value": [
                            {"bk_obj_name": "业务", "bk_inst_name": "dba"},
                            {"bk_obj_name": "集群", "bk_inst_name": "db.mysql.mysql"},
                            {"bk_obj_name": "模块", "bk_inst_name": "example.domain.db"},
                        ],
                    },
                    "bk_host_id": {"value": 387, "display_name": "主机", "display_value": "127.0.0.1"},
                },
                "strategy_snapshot_key": "bk_monitorv3.ce.cache.strategy.snapshot.46650.1711704968",
            },
        },
        "current_value": 9.759688,
        "description": "已持续7m, avg(磁盘空间使用率) >= 2.0%, 当前值9.759688%",
        "related_info": "",
        "labels": ["dbm_mysql", "mysql", "dbm", "need_autofix", "REDIS_CLUSTER_AUTOFIX"],
    },
}

CREATE_POLICY_DETAILS = {
    "items": [
        {
            "id": 2532,
            "name": "xuzixuan",
            "target": [
                [
                    {
                        "field": "host_topo_node",
                        "value": [{"bk_obj_id": "set", "bk_inst_id": 2000008245}],
                        "method": "eq",
                    }
                ]
            ],
            "functions": [],
            "algorithms": [
                {
                    "id": 2940,
                    "type": "Threshold",
                    "level": 2,
                    "config": [[{"method": "gte", "threshold": 80}]],
                    "unit_prefix": "%",
                },
                {
                    "id": 2941,
                    "type": "Threshold",
                    "level": 1,
                    "config": [[{"method": "gte", "threshold": 90}]],
                    "unit_prefix": "%",
                },
            ],
            "expression": "a",
            "origin_sql": "",
            "query_configs": [
                {
                    "id": 2887,
                    "unit": "percent",
                    "alias": "a",
                    "functions": [],
                    "metric_id": "bk_monitor.system.disk.in_use",
                    "agg_method": "MAX",
                    "agg_interval": 60,
                    "metric_field": "in_use",
                    "agg_condition": [],
                    "agg_dimension": ["bk_target_ip", "bk_target_cloud_id", "mount_point"],
                    "data_type_label": "time_series",
                    "result_table_id": "system.disk",
                    "data_source_label": "bk_monitor",
                }
            ],
            "no_data_config": {
                "level": 2,
                "continuous": 10,
                "is_enabled": False,
                "agg_dimension": ["bk_target_ip", "bk_target_cloud_id"],
            },
        },
    ],
    "notice": {
        "id": 2532,
        "config": {
            "template": [
                {
                    "signal": "abnormal",
                    "title_tmpl": "{{business.bk_biz_name}} - {{alarm.name}}{{alarm.display_type}}",
                    "message_tmpl": "{{content.level}}\n{{content.begin_time}}\n{{content.time}}\n{{content.duration}}"
                    "\n{{content.target_type}}\n{{content.data_source}}\n{{content.content}}"
                    "\n{{content.current_value}}\n{{content.biz}}\n{{content.target}}"
                    "\n{{content.dimension}}\n{{content.detail}}\n{{content.assign_detail}}"
                    "\n{{content.related_info}}",
                },
                {
                    "signal": "recovered",
                    "title_tmpl": "{{business.bk_biz_name}} - {{alarm.name}}{{alarm.display_type}}",
                    "message_tmpl": "{{content.level}}\n{{content.begin_time}}\n{{content.time}}\n{{content.duration}}"
                    "\n{{content.target_type}}\n{{content.data_source}}\n{{content.content}}"
                    "\n{{content.current_value}}\n{{content.biz}}\n{{content.target}}"
                    "\n{{content.dimension}}\n{{content.detail}}\n{{content.assign_detail}}"
                    "\n{{content.related_info}}",
                },
                {
                    "signal": "closed",
                    "title_tmpl": "{{business.bk_biz_name}} - {{alarm.name}}{{alarm.display_type}}",
                    "message_tmpl": "{{content.level}}\n{{content.begin_time}}\n{{content.time}}\n{{content.duration}}"
                    "\n{{content.target_type}}\n{{content.data_source}}\n{{content.content}}"
                    "\n{{content.current_value}}\n{{content.biz}}\n{{content.target}}"
                    "\n{{content.dimension}}\n{{content.detail}}\n{{content.assign_detail}}"
                    "\n{{content.related_info}}",
                },
            ],
            "need_poll": True,
            "notify_interval": 7200,
            "interval_notify_mode": "standard",
        },
        "signal": ["no_data", "abnormal"],
        "options": {
            "end_time": "23:59:59",
            "start_time": "00:00:00",
            "assign_mode": ["by_rule", "only_notice"],
            "upgrade_config": {"is_enabled": False, "user_groups": [], "upgrade_interval": 86400},
            "converge_config": {
                "count": 1,
                "condition": [
                    {"value": ["self"], "dimension": "strategy_id"},
                    {"value": ["self"], "dimension": "dimensions"},
                    {"value": ["self"], "dimension": "alert_level"},
                    {"value": ["self"], "dimension": "signal"},
                    {"value": ["self"], "dimension": "bk_biz_id"},
                    {"value": ["self"], "dimension": "notice_receiver"},
                    {"value": ["self"], "dimension": "notice_way"},
                ],
                "timedelta": 60,
                "is_enabled": True,
                "converge_func": "collect",
                "need_biz_converge": True,
                "sub_converge_config": {
                    "count": 2,
                    "condition": [
                        {"value": ["self"], "dimension": "bk_biz_id"},
                        {"value": ["self"], "dimension": "notice_receiver"},
                        {"value": ["self"], "dimension": "notice_way"},
                        {"value": ["self"], "dimension": "alert_level"},
                        {"value": ["self"], "dimension": "signal"},
                    ],
                    "timedelta": 60,
                    "converge_func": "collect_alarm",
                },
            },
            "chart_image_enabled": True,
            "exclude_notice_ways": {"ack": [], "closed": [], "recovered": []},
            "noise_reduce_config": {
                "unit": "percent",
                "count": 10,
                "timedelta": 5,
                "dimensions": [],
                "is_enabled": False,
            },
        },
        "config_id": 3548,
        "relate_type": "NOTICE",
        "user_groups": [20],
    },
}

CREATE_POLICY = [
    {"name": "influxDB-n6hfH", "target_priority": 0, "details": CREATE_POLICY_DETAILS},
    {"name": "MySql123", "target_priority": 1, "details": CREATE_POLICY_DETAILS},
]

# 范围屏蔽（主机）
CREATE_ALARM_SHIELD_FOR_IP_SCOPE = {
    "category": "scope",
    "begin_time": "2024-11-21 00:00:00",
    "end_time": "2024-11-21 23:59:59",
    "cycle_config": {"begin_time": "", "end_time": "", "day_list": [], "week_list": [], "type": 1},
    "shield_notice": False,
    "notice_config": {},
    "description": "xxxx",
    "dimension_config": {"scope_type": "ip", "target": [{"bk_host_id": 1, "ip": "127.0.0.1", "bk_cloud_id": 0}]},
    "bk_biz_id": 3,
}

# 维度屏蔽
CREATE_ALARM_SHIELD_FOR_DIMENSION = {
    "category": "dimension",
    "begin_time": "2024-11-21 00:00:00",
    "end_time": "2024-11-21 23:59:59",
    "cycle_config": {"begin_time": "", "end_time": "", "day_list": [], "week_list": [], "type": 1},
    "shield_notice": False,
    "notice_config": {},
    "description": "test",
    "dimension_config": {
        "dimension_conditions": [
            {"condition": "and", "key": "appid", "method": "eq", "value": ["100706"], "name": "appid"}
        ],
        "strategy_id": "",
    },
    "bk_biz_id": 3,
}

# 策略屏蔽
CREATE_ALARM_SHIELD_FOR_STRATEGY = {
    "category": "strategy",
    "begin_time": "2024-11-21 00:00:00",
    "end_time": "2024-11-21 23:59:59",
    "cycle_config": {"begin_time": "", "end_time": "", "day_list": [], "week_list": [], "type": 1},
    "shield_notice": False,
    "notice_config": {},
    "description": "xxxx",
    "dimension_config": {
        "id": [98043],
        "level": [2],
        "dimension_conditions": [
            {"condition": "and", "key": "appid", "method": "eq", "value": ["11111111"], "name": "dbm_meta app id"}
        ],
    },
    "level": [2],
    "bk_biz_id": 3,
}


# 更新策略屏蔽
UPDATE_ALARM_SHIELD = {"begin_time": "2024-11-21 00:00:00", "end_time": "2024-12-21 23:59:59", "description": "update"}

LIST_ALARM_SHIELD = {"bk_biz_id": 3}

LIST_ALARM_SHIELD_RESPONSE = [
    {
        "id": 769279,
        "bk_biz_id": 5005578,
        "category": "strategy",
        "status": 1,
        "begin_time": "2024-11-21 00:00:00",
        "end_time": "2024-11-21 23:59:59",
        "failure_time": "2024-11-21 23:59:59",
        "is_enabled": True,
        "scope_type": "",
        "dimension_config": {
            "strategy_id": [98043],
            "level": [2],
            "dimension_conditions": [
                {"key": "appid", "value": ["11111111"], "method": "eq", "condition": "and", "name": "dbm_meta app id"}
            ],
        },
        "content": "",
        "cycle_config": {"type": 1, "week_list": [], "day_list": [], "begin_time": "", "end_time": ""},
        "shield_notice": False,
        "notice_config": "{}",
        "description": "xxxx",
        "source": "",
        "update_user": "admin",
    },
    {
        "id": 769271,
        "bk_biz_id": 5005578,
        "category": "dimension",
        "status": 1,
        "begin_time": "2024-11-21 00:00:00",
        "end_time": "2024-11-21 23:59:59",
        "failure_time": "2024-11-21 23:59:59",
        "is_enabled": True,
        "scope_type": "",
        "dimension_config": {
            "dimension_conditions": [
                {"key": "appid", "value": ["100706"], "method": "eq", "condition": "and", "name": "appid"}
            ],
            "_strategy_id": 0,
        },
        "content": "",
        "cycle_config": {"type": 1, "week_list": [], "day_list": [], "begin_time": "", "end_time": ""},
        "shield_notice": False,
        "notice_config": "{}",
        "description": "test",
        "source": "",
        "update_user": "admin",
    },
    {
        "id": 769270,
        "bk_biz_id": 5005578,
        "category": "scope",
        "status": 1,
        "begin_time": "2024-11-21 00:00:00",
        "end_time": "2024-11-21 23:59:59",
        "failure_time": "2024-11-21 23:59:59",
        "is_enabled": True,
        "scope_type": "ip",
        "dimension_config": {
            "bk_target_ip": [{"bk_host_id": 1, "bk_target_ip": "127.0.0.1", "bk_target_cloud_id": 0}]
        },
        "content": "",
        "cycle_config": {"type": 1, "week_list": [], "day_list": [], "begin_time": "", "end_time": ""},
        "shield_notice": False,
        "notice_config": "{}",
        "description": "xxxx",
        "source": "",
        "update_user": "admin",
    },
]
