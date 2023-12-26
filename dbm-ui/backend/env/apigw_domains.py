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
from backend.utils.env import get_type_env

CC_APIGW_DOMAIN = get_type_env(key="CC_APIGW_DOMAIN", _type=str)
GSE_APIGW_DOMAIN = get_type_env(key="GSE_APIGW_DOMAIN", _type=str)
GCS_APIGW_DOMAIN = get_type_env(key="GCS_APIGW_DOMAIN", _type=str)
SCR_APIGW_DOMAIN = get_type_env(key="SCR_APIGW_DOMAIN", _type=str)
JOB_APIGW_DOMAIN = get_type_env(key="JOB_APIGW_DOMAIN", _type=str)
SOPS_APIGW_DOMAIN = get_type_env(key="SOPS_APIGW_DOMAIN", _type=str)
ESB_APIGW_DOMAIN = get_type_env(key="ESB_APIGW_DOMAIN", _type=str)
USER_MANAGE_APIGW_DOMAIN = get_type_env(key="USER_MANAGE_APIGW_DOMAIN", _type=str)
CMSI_APIGW_DOMAIN = get_type_env(key="CMSI_APIGW_DOMAIN", _type=str)
ITSM_APIGW_DOMAIN = get_type_env(key="ITSM_APIGW_DOMAIN", _type=str)
BKLOG_APIGW_DOMAIN = get_type_env(key="BKLOG_APIGW_DOMAIN", _type=str)
BKMONITORV3_APIGW_DOMAIN = get_type_env(key="BKMONITORV3_APIGW_DOMAIN", _type=str)

DRS_APIGW_DOMAIN = get_type_env(key="DRS_APIGW_DOMAIN", _type=str)
NAMESERVICE_APIGW_DOMAIN = get_type_env(key="NAMESERVICE_APIGW_DOMAIN", _type=str)

DBCONFIG_APIGW_DOMAIN = get_type_env(key="DBCONFIG_APIGW_DOMAIN", _type=str, default="http://bk-dbm-dbconfig")
DNS_APIGW_DOMAIN = get_type_env(key="DNS_APIGW_DOMAIN", _type=str, default="http://bk-dbm-db-dns-api")
MYSQL_PRIV_MANAGER_APIGW_DOMAIN = get_type_env(
    key="MYSQL_PRIV_MANAGER_APIGW_DOMAIN", _type=str, default="http://bk-dbm-dbpriv"
)
PARTITION_APIGW_DOMAIN = get_type_env(key="PARTITION_APIGW_DOMAIN", _type=str, default="http://bk-dbm-dbpartition")
MYSQL_SIMULATION_DOMAIN = get_type_env(key="MYSQL_SIMULATION_DOMAIN", _type=str, default="http://bk-dbm-dbsimulation")
HADB_APIGW_DOMAIN = get_type_env(key="HADB_APIGW_DOMAIN", _type=str, default="http://bk-dbm-hadb-api")
DBRESOURCE_APIGW_DOMAIN = get_type_env(key="DBRESOURCE_APIGW_DOMAIN", _type=str, default="http://bk-dbm-db-resource")
BACKUP_APIGW_DOMAIN = get_type_env(key="BACKUP_APIGW_DOMAIN", _type=str, default="http://bk-dbm-backup-server")
SLOW_QUERY_PARSER_DOMAIN = get_type_env(
    key="SLOW_QUERY_PARSER_DOMAIN", _type=str, default="http://bk-dbm-slow-query-parser-service"
)
DBHA_APIGW_DOMAIN_LIST = get_type_env(key="DBHA_APIGW_DOMAIN_LIST", _type=list, default=[])
# todo 备份服务器已经设置好mysql密码。后续需要获取mysql随机账号
BACKUP_DOWNLOAD_USER = get_type_env(key="BACKUP_DOWNLOAD_USER", _type=str, default="mysql")
BACKUP_DOWNLOAD_USER_PWD = get_type_env(key="BACKUP_DOWNLOAD_USER", _type=str, default="")

CELERY_SERVICE_APIGW_DOMAIN = get_type_env(key="CELERY_SERVICE_APIGW_DOMAIN", _type=str)
