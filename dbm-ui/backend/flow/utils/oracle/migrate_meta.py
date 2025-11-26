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

from django.utils.translation import gettext as _

from backend.components import DnsApi
from backend.configuration.constants import DBType
from backend.configuration.handlers.dba import DBAdministratorHandler
from backend.db_meta.api.cluster.oracle.primary_standby_create import pkg_create_oracle
from backend.db_meta.models import Cluster
from backend.flow.utils.oracle.oracle_password import OraclePassword

logger = logging.getLogger("flow")


class OracleMigrateMeta(object):
    """oracle迁移元数据flow节点函数"""

    def __init__(self, info: dict):
        self.info = info

    def action(self) -> bool:
        function_name = self.info["meta_func_name"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(_("找不到单据类型，请联系系统管理员"))
        return False

    def check_dest_cluster(self):
        """检查目标环境是否已经存在该cluster"""

        if Cluster.objects.filter(name=self.info["cluster_name"], bk_biz_id=self.info["bk_biz_id"]).count() > 0:
            logger.error(
                "error: cluster:{} has of bk_biz_id:{} been existed".format(
                    self.info["cluster_name"], str(self.info["bk_biz_id"])
                )
            )
            raise ValueError(
                "error: cluster:{} has of bk_biz_id:{} been existed".format(
                    self.info["cluster_name"], str(self.info["bk_biz_id"])
                )
            )

    def check_machine_spec(self):
        """检查机器规格"""

        if not self.info["spec"]["spec_id"]:
            logger.error("error: machine spec of destination is not exist about {}".format(DBType.Oracle.value))
            raise ValueError("error: machine spec of destination is not exist about {}".format(DBType.Oracle.value))

    def upsert_dba(self):
        """更新dba"""

        DBAdministratorHandler.upsert_biz_admins(self.info["bk_biz_id"], self.info["db_admins"])

    def save_password(self):
        """保存密码到密码服务 perfstat execute_user"""

        for username in self.info["usernames"]:
            for password_info in self.info["password_infos"]:
                result = OraclePassword().save_password_to_db(
                    instances=password_info["nodes"],
                    username=username,
                    password=password_info["password"][username],
                    operator=self.info["operator"],
                )
                if result:
                    logger.error(
                        "nodes:{} save user:{} password fail, error: {}".format(
                            password_info["nodes"], username, result
                        )
                    )
                    return False

    def migrate_cluster(self):
        """迁移集群"""

        # 写入meta
        try:
            pkg_create_oracle(
                bk_biz_id=self.info["bk_biz_id"],
                name=self.info["name"],
                immute_domain=self.info["immute_domain"],
                db_module_id=self.info["db_module_id"],
                alias=self.info["alias"],
                major_version=self.info["major_version"],
                storages=self.info["storages"],
                creator=self.info["creator"],
                bk_cloud_id=self.info["bk_cloud_id"],
                region=self.info["region"],
                spec_id=self.info["spec_id"],
                spec_config=self.info["spec_config"],
                cluster_type=self.info["cluster_type"],
                disaster_tolerance_level=self.info["disaster_tolerance_level"],
            )
        except Exception as e:
            logger.error("add relationship to meta fail, error:{}".format(str(e)))
            return False
        logger.info("add mongodb relationship to meta successfully")
        return True

    def change_domain_app(self):
        """修改dns的app字段"""

        for domain in self.info["change_domain_app"]:
            domain_name = domain if domain.endswith(".") else "{}.".format(domain)
            try:
                DnsApi.update_domain_belong_app(
                    {
                        "app": self.info["app"],
                        "new_app": self.info["new_app"],
                        "domain_name": domain_name,
                        "bk_cloud_id": self.info["bk_cloud_id"],
                    }
                )
            except Exception as e:
                logger.error(
                    "change domain:{} dns app fail, from old app:{} to new app:{}, error:{}".format(
                        domain_name, self.info["app"], self.info["new_app"], str(e)
                    )
                )
                raise ValueError(
                    "change domain:{} dns app fail, from old app:{} to new app:{}, error:{}".format(
                        domain_name, self.info["app"], self.info["new_app"], str(e)
                    )
                )
