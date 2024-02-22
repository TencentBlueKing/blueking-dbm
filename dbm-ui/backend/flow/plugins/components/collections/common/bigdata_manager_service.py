import logging
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_proxy.models import ClusterExtension
from backend.flow.consts import ManagerOpType
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


def get_manager_ip(bk_biz_id, db_type, cluster_name, service_type):
    """
    通过4个参数唯一确定manager的ip
    @params:
     bk_biz_id: 业务ID
     db_type: 组件类型
     cluster_name: 集群名字
     service_type: manager类型
    @return: manager ip
    """

    try:
        manager = ClusterExtension.objects.get(
            bk_biz_id=bk_biz_id,
            db_type=db_type,
            cluster_name=cluster_name,
            service_type=service_type,
        )
        return manager.ip
    except ClusterExtension.DoesNotExist:
        return None


class BigdataManagerService(BaseService):
    """
    大数据管理端信息维护
    ManagerOpType: CREATE / UPDATE / DELETE
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 操作类型 insert / update
        manager_op_type = kwargs["manager_op_type"]

        # 传入调用结果
        bk_biz_id = global_data["bk_biz_id"]
        db_type = kwargs["db_type"]
        cluster_name = global_data["cluster_name"]
        service_type = kwargs["service_type"]
        bk_cloud_id = global_data["bk_cloud_id"]
        manager_ip = kwargs["manager_ip"]
        manager_port = kwargs["manager_port"]

        if manager_op_type == ManagerOpType.CREATE:
            ClusterExtension.objects.create(
                bk_biz_id=bk_biz_id,
                db_type=db_type,
                cluster_name=cluster_name,
                service_type=service_type,
                bk_cloud_id=bk_cloud_id,
                ip=manager_ip,
                port=manager_port,
                is_flush=False,
                is_deleted=False,
            )
        elif manager_op_type == ManagerOpType.UPDATE:
            try:
                manager = ClusterExtension.objects.get(
                    bk_biz_id=bk_biz_id,
                    db_type=db_type,
                    cluster_name=cluster_name,
                    service_type=service_type,
                )
                manager.bk_biz_id = bk_biz_id
                manager.db_type = db_type
                manager.cluster_name = cluster_name
                manager.service_type = service_type
                manager.bk_cloud_id = bk_cloud_id
                manager.ip = manager_ip
                manager.port = manager_port
                manager.is_flush = False
                manager.save()
            except ClusterExtension.DoesNotExist:
                ClusterExtension.objects.create(
                    bk_biz_id=bk_biz_id,
                    db_type=db_type,
                    cluster_name=cluster_name,
                    service_type=service_type,
                    bk_cloud_id=bk_cloud_id,
                    manager_ip=manager_ip,
                    manager_port=manager_port,
                    is_flush=False,
                    is_deleted=False,
                )

        elif manager_op_type == ManagerOpType.DELETE:
            try:
                manager = ClusterExtension.objects.get(
                    bk_biz_id=bk_biz_id,
                    db_type=db_type,
                    cluster_name=cluster_name,
                    service_type=service_type,
                )
                manager.is_deleted = True
                manager.save()
            except ClusterExtension.DoesNotExist:
                self.log_error(
                    "Manager not found, bk_biz_id={}, db_type={}, cluster_name={}, service_type={}".format(
                        bk_biz_id, db_type, cluster_name, service_type
                    )
                )
                # 没有找到manager的情况下无需特殊处理
        else:
            self.log_error(_("无法找到Manager处理类型,请联系系统管理员:{}").format(manager_op_type))
            return False

        self.log_info("Manager operation {} result: success".format(manager_op_type))
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class BigdataManagerComponent(Component):
    name = __name__
    code = "bigdata_manager_service"
    bound_service = BigdataManagerService
