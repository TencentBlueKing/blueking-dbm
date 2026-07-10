# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Oracle 通用元数据写入入口 (与其它 DB 命名对齐: sqlserver_db_meta / mysql_db_meta)。

与 dba 编写的 OracleMigrateMeta (migrate_meta.py) 职责区分:
    - OracleMigrateMeta: 集群迁移相关的元数据写入;
    - OracleDBMeta:      日常运维单据(如 add_slave)相关的元数据写入。
"""

import logging

from django.utils.translation import gettext as _

from backend.db_meta.api.cluster.oracle.replace_primary_standby import new_machine, replace_instance
from backend.db_meta.api.cluster.oracle.replace_single_instance import replace_single_instance

logger = logging.getLogger("flow")


class OracleDBMeta(object):
    """oracle 日常运维单据 -- 元数据写入 flow 节点函数"""

    def __init__(self, info: dict):
        self.info = info

    def action(self) -> bool:
        function_name = self.info["meta_func_name"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(_("找不到单据类型，请联系系统管理员"))
        return False

    def new_machine(self):
        """Oracle 创建新机器

        info 期望字段:
            bk_cloud_id: 云区域 ID
            bk_biz_id: 业务 ID
            new_ip: 新机器 IP
            resource_spec: 新机器规格
            creator: 创建人
            cluster_type: 集群类型
        """
        try:
            new_machine(
                bk_cloud_id=self.info["bk_cloud_id"],
                bk_biz_id=self.info["bk_biz_id"],
                ip=self.info["new_ip"],
                resource_spec=self.info["resource_spec"],
                creator=self.info["created_by"],
                cluster_type=self.info["cluster_type"],
            )
        except Exception as e:
            logger.error("oracle add machine meta fail, error:{}".format(str(e)))
            return False
        logger.info("oracle add machine meta successfully")
        return True

    def replace_instance(self):
        """Oracle 主备集群单节点替换 -- 写元数据

        用于 OraclePrimaryStandby 集群下, 用新的 IP/Port 替换旧的
        PRIMARY 或 STANDBY 节点(角色由旧实例自动识别)。

        info 期望字段:
            cluster_id: 集群 ID
            bk_biz_id: 业务 ID
            new_instance_ip: 新实例 IP
            new_instance_port: 新实例端口
            old_instance_ip: 旧实例 IP
            old_instance_port: 旧实例端口
        """
        try:
            replace_instance(
                cluster_id=self.info["cluster_id"],
                new_instance_ip=self.info["new_instance_ip"],
                new_instance_port=self.info["new_instance_port"],
                old_instance_ip=self.info["old_instance_ip"],
                old_instance_port=self.info["old_instance_port"],
                bk_biz_id=self.info["bk_biz_id"],
            )
        except Exception as e:
            logger.error("oracle replace instance meta fail, error:{}".format(str(e)))
            return False
        logger.info("oracle replace instance meta successfully")
        return True

    def replace_single_instance(self):
        """Oracle 单实例集群机器替换 -- 写元数据

        用于 OracleSingleNone 集群, 将唯一 PRIMARY 实例迁移到新机器/端口。

        info 期望字段:
            cluster_id: 集群 ID
            bk_biz_id: 业务 ID
            new_ip: 新机器 IP
            new_port: 新实例端口
        """
        try:
            replace_single_instance(
                cluster_id=self.info["cluster_id"],
                new_ip=self.info["new_ip"],
                new_port=self.info["new_port"],
                bk_biz_id=self.info["bk_biz_id"],
            )
        except Exception as e:
            logger.error("oracle replace single instance meta fail, error:{}".format(str(e)))
            return False
        logger.info("oracle replace single instance meta successfully")
        return True
