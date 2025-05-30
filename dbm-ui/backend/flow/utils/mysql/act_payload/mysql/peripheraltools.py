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
from typing import List

from backend.db_meta.enums import AccessLayer, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, Machine, ProxyInstance
from backend.db_package.models import Package
from backend.db_proxy.reverse_api.common.impl import list_nginx_addrs
from backend.flow.consts import DBActuatorActionEnum, DBActuatorTypeEnum, MediumEnum, MysqlVersionToDBBackupForMap
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    DeployPeripheralToolsDepart,
    remove_departs,
)
from backend.flow.utils.mysql.act_payload.base.payload_base import PayloadBase
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.mysql_account_mixed import MySQLAccountMixed
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.proxy_account_mixed import ProxyAccountMixed


class PeripheralToolsPayload(PayloadBase, MySQLAccountMixed, ProxyAccountMixed):
    def __filter_departs(
        self, ip: str, departs: List[DeployPeripheralToolsDepart]
    ) -> List[DeployPeripheralToolsDepart]:
        m = Machine.objects.get(bk_cloud_id=self.bk_cloud_id, ip=ip)
        res = copy.deepcopy(departs)

        # 接入层进一步修饰 departs
        if m.access_layer == AccessLayer.PROXY:
            # 所有接入层都不用校验
            res = remove_departs(
                res, DeployPeripheralToolsDepart.MySQLTableChecksum, DeployPeripheralToolsDepart.MySQLRotateBinlog
            )

            # tendbha proxy 不用备份, rotate
            if m.machine_type == MachineType.PROXY:
                res = remove_departs(res, DeployPeripheralToolsDepart.MySQLDBBackup)
            else:  # spider
                ins = ProxyInstance.objects.filter(machine=m).first()
                # spider slave, spider mnt 不用备份
                if not ins.tendbclusterspiderext.spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                    res = remove_departs(res, DeployPeripheralToolsDepart.MySQLDBBackup)

        self.logger.info("{} departs: {}".format(ip, res))
        return res

    def gen_config(self, **kwargs):
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.GenPeripheralToolsConfig.value,
            "payload": {
                "extend": {
                    "ip": kwargs["ip"],
                    "bk_cloud_id": self.bk_cloud_id,
                    "ports": self.cluster["ports"],
                    "departs": self.__filter_departs(kwargs["ip"], self.cluster["departs"]),
                    "nginx_addrs": list_nginx_addrs(bk_cloud_id=self.bk_cloud_id),
                },
            },
        }

    def reload_config(self, **kwargs):
        p = self.gen_config(**kwargs)
        p["action"] = DBActuatorActionEnum.ReloadPeripheralToolsConfig.value
        return p

    def deploy_binary(self, **kwargs):
        departs = self.cluster["departs"]
        ip = kwargs["ip"]
        # departs = self.__filter_departs(ip, departs)

        m = Machine.objects.get(ip=ip, bk_cloud_id=self.bk_cloud_id)
        depart_pkgs = {}

        if DeployPeripheralToolsDepart.MySQLDBBackup in departs:
            departs = remove_departs(departs, DeployPeripheralToolsDepart.MySQLDBBackup)
            if m.machine_type == MachineType.PROXY:
                pass
            else:
                if m.machine_type == MachineType.SPIDER:
                    dbbackup_pkg_type = MediumEnum.DbBackup
                else:
                    db_version = Cluster.objects.filter(storageinstance__machine__ip=ip).first().major_version
                    dbbackup_pkg_type = MysqlVersionToDBBackupForMap[db_version]

                dbbackup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=dbbackup_pkg_type)
                depart_pkgs[DeployPeripheralToolsDepart.MySQLDBBackup] = {
                    "pkg": dbbackup_pkg.name,
                    "pkg_md5": dbbackup_pkg.md5,
                }

        for depart in departs:
            pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=depart)
            depart_pkgs[depart] = {
                "pkg": pkg.name,
                "pkg_md5": pkg.md5,
            }

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.DeployPeripheralToolsBinary.value,
            "payload": {
                "extend": {
                    "ip": ip,
                    "bk_cloud_id": self.bk_cloud_id,
                    "nginx_addrs": list_nginx_addrs(bk_cloud_id=self.bk_cloud_id),
                    "departs": depart_pkgs,
                },
            },
        }

    def standardize_instance(self, **kwargs):
        ip = kwargs["ip"]
        m = Machine.objects.get(ip=ip, bk_cloud_id=self.bk_cloud_id)

        if m.machine_type == MachineType.PROXY:
            return {
                "db_type": DBActuatorTypeEnum.Proxy.value,
                "action": DBActuatorActionEnum.StandardizeTenDBHAProxy.value,
                "payload": {
                    "general": {"runtime_account": self.proxy_admin_account()},
                    "extend": {
                        "dbha_account": self.mysql_dbha_account(self.bk_cloud_id)["user"],
                        "port_list": self.cluster["ports"],
                        "ip": ip,
                    },
                },
            }
        else:
            if m.machine_type == MachineType.SPIDER:
                major_version = Cluster.objects.filter(proxyinstance__machine__ip=ip).first().major_version
            else:
                major_version = Cluster.objects.filter(storageinstance__machine__ip=ip).first().major_version

            pkg = Package.get_latest_package(version=major_version, pkg_type=MediumEnum.MySQL)

            return {
                "db_type": DBActuatorTypeEnum.MySQL.value,
                "action": DBActuatorActionEnum.StandardizeMySQLInstance.value,
                "payload": {
                    "general": {
                        "runtime_account": {
                            **self.mysql_static_account(),
                            **self.mysql_admin_account(self.ticket_data),
                        },
                    },
                    "extend": {
                        "pkg": pkg.name,
                        "pkg_md5": pkg.md5,
                        "ip": ip,
                        "ports": self.cluster["ports"],
                        "mysql_version": major_version,
                        "super_account": self.mysql_drs_account(self.bk_cloud_id),
                        "dbha_account": self.mysql_dbha_account(self.bk_cloud_id),
                        "webconsolers_account": self.mysql_webconsole_account(self.bk_cloud_id),
                        "partition_yw_account": self.mysql_partition_yw_account(),
                    },
                },
            }

    def init_common_config(self, **kwargs):
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.InitCommonConfig.value,
            "payload": {
                "extend": {
                    "nginx_addrs": list_nginx_addrs(bk_cloud_id=self.bk_cloud_id),
                    "bk_cloud_id": self.bk_cloud_id,
                }
            },
        }
