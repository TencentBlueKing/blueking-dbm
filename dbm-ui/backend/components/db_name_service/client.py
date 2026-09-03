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

from django.utils.translation import gettext_lazy as _

from ..base import BaseApi
from ..domains import NAMESERVICE_APIGW_DOMAIN


class _NameServiceApi(BaseApi):
    MODULE = _("名字服务")
    BASE = NAMESERVICE_APIGW_DOMAIN

    def __init__(self):
        # 传入参数
        # {"region":"南京",
        # "loadbalancername":"clb_name",
        # "manager":"xxx",
        # "backupmanager":"xxx",
        # "protocol":"TCP",
        # "listenername":"clb_listener_name",
        # "ips":["1.1.1.1:52026","2.2.2.2:52026"]}
        # 返回参数
        # {"code": 0,
        # "message": "",
        # "data":{"loadbalancerid":"lb-xxx","listenerid":"lbl-xxx","loadbalancerip":"1.1.1.1"}}
        self.clb_create_lb_and_register_target = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/create_lb_and_register_target",
            description=_("创建clb并绑定后端主机"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"region":"南京","loadbalancerid":"lb-xxx","listenerid":"lbl-xxx","ips":["1.1.1.1:52026"]}
        # 返回参数
        # {"code": 0, "message": "ok", "data":0}  code为 0 为成功，其他为失败
        self.clb_deregister_part_target = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/deregister_part_target",
            description=_("clb解绑部分后端主机"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"region":"南京","loadbalancerid":"lb-xxx","listenerid":"lbl-xxx","ips":["1.1.1.1:52026"]}
        # 返回参数
        # {"code": 0, "message": "ok", "data":0}  code为 0 为成功，其他为失败
        self.clb_register_part_target = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/register_part_target",
            description=_("clb新增绑定部分后端主机"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"region":"南京","loadbalancerid":"lb-xxx","listenerid":"lbl-xxx"}
        # 返回参数
        # {"code": 0, "message": "ok", "data":{"ips":["1.1.1.1:52026","2.2.2.2:52026"]}}
        self.clb_get_target_private_ips = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/get_target_private_ips",
            description=_("获取已绑定 clb 的后端 RS 列表（data.ips 为 ip:port 字符串列表）"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"region":"南京","ips":["1.1.1.1"]}
        # 返回参数
        # {"code": 0,
        # "message": "ok",
        # "data":{"clbinfos":[{"clbid":"lb-xxx","registerclb": true,"ip":"1.1.1.1","region":"南京"}]}}
        self.clb_check_clb_register_target_by_ip = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/check_clb_register_target_by_ip",
            description=_("通过IP查询该IP是否已经被clb绑定了"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"region":"南京","loadbalancerid":"lb-xxx","listenerid":"lbl-xxx"}
        # 返回参数
        # {"code": 0, "message": "ok", "data":0}  code为 0 为成功，其他为失败
        self.clb_deregister_target_and_del_lb = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/deregister_target_and_del_lb",
            description=_("解绑后端主机并删除clb"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"region":"南京","loadbalancerid":"lb-xxx","listenerid":"lbl-xxx","scheduler":"WRR"}
        # 可选值：WRR（按权重轮询）、LEAST_CONN（按最小连接数）、IP_HASH（按 IP 地址哈希）
        # 返回参数
        # {"code": 0, "message": "ok", "data":0}  code为 0 为成功，其他为失败
        self.clb_listener_change_scheduler = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/listener_change_scheduler",
            description=_("修改监听器转发方式"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"region":"南京","loadbalancerid":"lb-xxx","listenerid":"lbl-xxx","sessionexpiretime":300}
        # sessionexpiretime 会话保持时间，单位秒
        # 返回参数
        # {"code": 0, "message": "ok", "data":0}  code为 0 为成功，其他为失败
        self.clb_listener_change_session_expire_time = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/listener_change_session_expire_time",
            description=_("修改监听器会话保持时间"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"region":"南京","loadbalancerid":"lb-xxx","listenerid":"lbl-xxx","ips":["1.1.1.1:52026"],"weight":10}
        # weight 权重，范围 0-100
        # 返回参数
        # {"code": 0, "message": "ok", "data":0}  code为 0 为成功，其他为失败
        self.clb_change_target_weight = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/change_target_weight",
            description=_("修改后端绑定主机的转发权重"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"region":"ap-guangzhou","loadbalancerid":"lb-xxxxxxxx"}
        # 返回参数
        # {"code": 0,
        # "message": "ok",
        # "data":{"totalcount":10,"abnormalcount":2,"abnormalips":["xxxx:8080","xxxx:8080"]}}
        self.clb_describe_target_health = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/describe_target_health",
            description=_("查询clb后端主机健康状态"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"name":"polaris.xx.xx.xx.db",
        # "owners":"xxx1,xxx2",
        # "department":"xxx",
        # "business":"xxx",
        # "comment":"测试",
        # "ips":["1.1.1.1:52026","2.2.2.2:52026"]}
        # 返回参数
        # {"code": 0, "message": "ok",
        # "data":{"servicename":"polaris.xxx","servicetoken":"xxx", "alias":"xxx", "aliastoken":"xxx"}}
        self.polaris_create_service_alias_and_bind_targets = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/create_service_alias_and_bind_targets",
            description=_("创建北极星服务和别名并绑定后端主机"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"servicename":"polaris.xx.xx.xx.db","servicetoken":"xxx","ips":["1.1.1.1:52026"]}
        # 返回参数
        # {"code": 0, "message": "ok", "data":0}  code为 0 为成功，其他为失败
        self.polaris_unbind_part_targets = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/unbind_part_targets",
            description=_("北极星解绑部分后端主机"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"servicename":"polaris.xx.xx.xx.db","servicetoken":"xxx","ips":["1.1.1.1:52026"]}
        # 返回参数
        # {"code": 0, "message": "ok", "data":0}  code为 0 为成功，其他为失败
        self.polaris_bind_part_targets = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/bind_part_targets",
            description=_("北极星新增绑定部分后端主机"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"servicename":"polaris.xx.xx.xx.db"}
        # 返回参数
        # {"code": 0, "message": "ok", "data":{"ips":["1.1.1.1:52026","2.2.2.2:52026"]}}
        self.polaris_describe_targets = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/describe_targets",
            description=_("获取北极星已绑定的后端主机信息"),
            default_timeout=600,
            max_retry_times=1,
        )
        # 传入参数
        # {"servicename":"polaris.xx.xx.xx.db","servicetoken":"xxx","alias":"xxx", "aliastoken":"xxx"}
        # 返回参数
        # {"code": 0, "message": "ok", "data":0}  code为 0 为成功，其他为失败
        self.polaris_unbind_targets_and_delete_alias_service = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/unbind_targets_and_delete_alias_service",
            description=_("解绑后端主机并删除别名和北极星服务"),
            default_timeout=600,
            max_retry_times=1,
        )


NameServiceApi = _NameServiceApi()
