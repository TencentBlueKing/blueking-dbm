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

from django.conf import settings

from backend import env

ESB_PREFIX = "/api/c/compapi/v2/"

ESB_DOMAIN_TPL = "{}{}{{}}/".format(env.BK_COMPONENT_API_URL, ESB_PREFIX)

# 优先取环境变量的配置，若未配置对应的环境变量，则取paas默认的esb地址
CC_APIGW_DOMAIN = env.CC_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("cc")
GSE_APIGW_DOMAIN = env.GSE_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("gse")
JOB_APIGW_DOMAIN = env.JOB_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("jobv3")
SOPS_APIGW_DOMAIN = env.SOPS_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("sops")
ESB_APIGW_DOMAIN = env.ESB_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("esb")
USER_MANAGE_APIGW_DOMAIN = env.USER_MANAGE_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("usermanage")
CMSI_APIGW_DOMAIN = env.CMSI_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("cmsi")
ITSM_APIGW_DOMAIN = env.ITSM_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("itsm")
BKLOG_APIGW_DOMAIN = env.BKLOG_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("bk_log")
DBCONFIG_APIGW_DOMAIN = env.DBCONFIG_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("dbconfig")
DNS_APIGW_DOMAIN = env.DNS_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("dbdns")
MYSQL_PRIV_MANAGER_APIGW_DOMAIN = env.MYSQL_PRIV_MANAGER_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("mysql_priv_manager")
PARTITION_APIGW_DOMAIN = env.PARTITION_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("partition")
DRS_APIGW_DOMAIN = env.DRS_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("db_remove_service")
# 监控区分上云版和社区版环境，待统一
BKMONITORV3_APIGW_DOMAIN = env.BKMONITORV3_APIGW_DOMAIN or ESB_DOMAIN_TPL.format(
    "monitor_v3" if env.RUN_VER == "open" else "bkmonitorv3"
)
MYSQL_SIMULATION_DOMAIN = env.MYSQL_SIMULATION_DOMAIN or ESB_DOMAIN_TPL.format("db_simulation")
NAMESERVICE_APIGW_DOMAIN = env.NAMESERVICE_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("nameservice")
HADB_APIGW_DOMAIN = env.HADB_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("hadb")
DBRESOURCE_APIGW_DOMAIN = env.DBRESOURCE_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("dbresource")
BACKUP_APIGW_DOMAIN = env.BACKUP_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("backup")
CELERY_SERVICE_APIGW_DOMAIN = env.CELERY_SERVICE_APIGW_DOMAIN or ESB_DOMAIN_TPL.format("celery_service")
