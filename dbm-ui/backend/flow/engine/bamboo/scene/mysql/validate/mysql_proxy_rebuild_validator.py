"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.mysql.validate.exception import (
    ProxyRebuildCountFailedException,
    ProxyRebuildDuplicateIPException,
)
from backend.flow.engine.validate.exceptions import DuplicateClusterIDException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class MySQLProxyRebuildFlowValidator(MysqlBaseValidator):
    """
    MySQLProxyRebuildFlow类对应的validate类
    判断传入flow的data参数合法性
    每行入参校验：
    检验1：传入集群合法性
    校验2：传入ip的合法性（ip字符串合法 + ip属于该集群的proxy机器）
    聚合校验：
    检验1：同一个flow，不能出现同样的cluster要处理
    检验2：同一个flow，同一个集群，传入机器不能有相同
    检验3：同一个flow，同一个集群，如果传入proxy数量，不能大于等于集群所有proxy数量
    """

    def pre_check_rebuild_proxy_count(self):
        """
        聚合校验3：同一个flow，同一个集群，传入proxy数量不能大于等于集群所有proxy机器数量
        （避免一次性把集群内所有proxy全部重建，无法保留可用的用户白名单克隆源，且会导致集群访问中断）
        前置依赖：聚合校验1已保证infos中不会出现重复cluster_id，故只需在每个info内判断即可
        """
        err_msg = ""
        for info in self.data["infos"]:
            cluster = Cluster.objects.get(id=int(info["cluster_id"]))
            # 集群内 proxy 的机器总数（按机器ip去重，而不是按实例）
            total_proxy_machine_count = len({p.machine.ip for p in cluster.proxyinstance_set.all()})
            rebuild_ip_count = len({host["ip"] for host in info["rebuild_proxy_hosts"]})
            if rebuild_ip_count >= total_proxy_machine_count:
                err_msg += _(
                    "集群[{}]本次重建proxy机器数[{}]不能大于等于集群所有proxy机器数[{}]，请检查 \n".format(
                        cluster.immute_domain, rebuild_ip_count, total_proxy_machine_count
                    )
                )
        return err_msg

    def __run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info：  self.data["infos"]每个元素体
        @param index： 每个元素体的编号
        """
        row_key = info.get("row_key", "")
        errors = []

        # 校验1：传入集群合法性
        log_format_tag = self.create_log_tag(field="cluster_id", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist([info["cluster_id"]], **log_format_tag)
        if error_msg:
            errors.append(error_msg)
            # 集群不存在，后续基于该集群的ip归属校验也无法执行，直接返回
            return errors

        # 校验2.1：传入ip字符串合法性
        ip_list = [host["ip"] for host in info["rebuild_proxy_hosts"]]
        log_format_tag = self.create_log_tag(field="rebuild_proxy_hosts", index=index, row_key=row_key)
        error_msg = self.pre_check_ip(ip_list, **log_format_tag)
        if error_msg:
            errors.append(error_msg)
            return errors

        # 校验2.2：传入ip是否属于该集群的proxy机器
        log_format_tag = self.create_log_tag(field="rebuild_proxy_hosts", index=index, row_key=row_key)
        error_msg = self.pre_check_mysql_proxy_in_cluster(ip_list, [info["cluster_id"]], **log_format_tag)
        if error_msg:
            errors.append(error_msg)

        return errors

    def __call__(self):
        # 阶段1 检测每行数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.__run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 聚合校验
        # 聚合校验1：同一个flow，不能出现同样的cluster要处理
        err = self.pre_check_duplicate_cluster_ids("cluster_id")
        if err:
            raise DuplicateClusterIDException(err)

        # 聚合校验2：同一个flow，同一个集群，传入机器不能有相同
        err = self.pre_check_duplicate_ip(check_ip_field_name="rebuild_proxy_hosts")
        if err:
            raise ProxyRebuildDuplicateIPException(err)

        # 聚合校验3：同一个flow，同一个集群，传入proxy数量不能大于等于集群所有proxy数量
        err = self.pre_check_rebuild_proxy_count()
        if err:
            raise ProxyRebuildCountFailedException(err)

        return None
