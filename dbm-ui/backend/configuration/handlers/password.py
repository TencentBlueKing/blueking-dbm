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
import base64
from collections import defaultdict
from typing import Any, Dict, List, Union

from django.utils.translation import ugettext as _
from django_celery_beat.schedulers import ModelEntry

from backend.components import MySQLPrivManagerApi
from backend.configuration.constants import DBM_MYSQL_ADMIN_USER, DBM_PASSWORD_SECURITY_NAME, DBType
from backend.configuration.exceptions import PasswordPolicyBaseException
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, TenDBClusterSpiderRole
from backend.db_periodic_task.models import DBPeriodicTask
from backend.flow.consts import MySQLPasswordRole


class DBPasswordHandler(object):
    """密码策略相关处理"""

    @classmethod
    def verify_password_strength(cls, password: str, echo: bool = False):
        """
        校验密码强度
        @param password: 密码(这里是不加盐的)
        @param echo: 是否回显解密密码
        """
        plain_password = AsymmetricHandler.decrypt(
            name=AsymmetricCipherConfigType.PASSWORD.value, content=password, salted=False
        )
        # 密码需要用base64加密后传输
        b64_plain_password = base64.b64encode(plain_password.encode("utf-8")).decode("utf-8")
        check_result = MySQLPrivManagerApi.check_password(
            {"password": b64_plain_password, "security_rule_name": DBM_PASSWORD_SECURITY_NAME}
        )
        if echo:
            check_result.update(password=plain_password)

        return check_result

    @classmethod
    def query_mysql_admin_password(
        cls, limit: int, offset: int, instances: List[str] = None, start_time: str = None, end_time: str = None
    ):
        """
        获取mysql的admin密码
        @param limit: 分页限制
        @param offset: 分页起始
        @param instances: 实例列表
        @param start_time: 过滤开始时间
        @param end_time: 过滤结束时间
        """
        instances = instances or []
        # 获取过滤条件
        instance_list = []
        try:
            for address in instances:
                bk_cloud_id, ip, port = address.split(":")
                instance_list.append({"bk_cloud_id": int(bk_cloud_id), "ip": ip, "port": int(port)})
        except (IndexError, ValueError):
            raise PasswordPolicyBaseException(_("请保证查询的实例输入格式合法"))

        filters = {"limit": limit, "offset": offset, "component": DBType.MySQL.value, "username": DBM_MYSQL_ADMIN_USER}
        if instance_list:
            filters.update(instances=instance_list)
        # TODO: 过滤起止时间

        mysql_admin_password_data = MySQLPrivManagerApi.get_mysql_admin_password(params=filters)
        mysql_admin_password_data["results"] = mysql_admin_password_data.pop("items")
        for data in mysql_admin_password_data["results"]:
            data["password"] = base64.b64decode(data["password"]).decode("utf-8")

        return mysql_admin_password_data

    @classmethod
    def modify_mysql_admin_password(cls, operator: str, password: str, lock_until: str, instance_list: List[Dict]):
        """
        修改mysql的admin密码
        @param operator: 操作人
        @param password: 修改密码
        @param lock_until: 到期时间
        @param instance_list: 修改的实例列表
        """

        # 根据cluster_type, bk_cloud_id, role将实例分类后聚合
        aggregate_instance: Dict[str, Dict[str, Dict[str, List]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        cluster_infos: List[Dict[str, Any]] = []
        for instance in instance_list:
            role = cls._get_mysql_password_role(instance["cluster_type"], instance["role"])
            aggregate_instance[instance["bk_cloud_id"]][instance["cluster_type"]][role].append(
                {"ip": instance["ip"], "port": int(instance["port"])}
            )
        for bk_cloud_id, clusters in aggregate_instance.items():
            for cluster_type, role_instances in clusters.items():
                instances_info = [{"role": role, "addresses": insts} for role, insts in role_instances.items()]
                cluster_infos.append(
                    {"bk_cloud_id": bk_cloud_id, "cluster_type": cluster_type, "instances": instances_info}
                )

        # 填充参数，修改mysql admin的密码
        modify_password_params = {
            "username": DBM_MYSQL_ADMIN_USER,
            "component": DBType.MySQL.value,
            "password": base64.b64encode(password.encode("utf-8")).decode("utf-8"),
            "lock_until": lock_until,
            "operator": operator,
            "clusters": cluster_infos,
            "security_rule_name": DBM_PASSWORD_SECURITY_NAME,
            "async": False,
        }
        return MySQLPrivManagerApi.modify_mysql_admin_password(params=modify_password_params)

    @classmethod
    def _get_mysql_password_role(cls, cluster_type, role):
        """获取实例对应的密码角色"""
        # 映射tendbcluster的角色
        if cluster_type == ClusterType.TenDBCluster:
            if role == "spider_ctl":
                return MySQLPasswordRole.TDBCTL_USER.value
            if role in TenDBClusterSpiderRole.get_values():
                return MySQLPasswordRole.SPIDER.value
            if role in [InstanceRole.REMOTE_MASTER.value, InstanceRole.REMOTE_SLAVE.value]:
                return MySQLPasswordRole.SPIDER.value

        # 映射mysql的角色
        if role in [InstanceInnerRole.MASTER.value, InstanceInnerRole.SLAVE.value]:
            return MySQLPasswordRole.STORAGE.value

        raise PasswordPolicyBaseException(_("{}-{}不存在相应的password角色").format(cluster_type, role))

    @classmethod
    def modify_periodic_task_run_every(cls, run_every, func_name):
        """修改定时任务的运行周期"""
        model_schedule, model_field = ModelEntry.to_model_schedule(run_every)
        db_task = DBPeriodicTask.objects.get(name__contains=func_name)
        celery_task = db_task.task
        setattr(celery_task, model_field, model_schedule)
        celery_task.save(update_fields=[model_field])
