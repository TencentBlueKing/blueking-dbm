import json
import logging

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.flow.consts import TendbSingleRestoreType
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator

logger = logging.getLogger("root")


class TendbSingleMigrateFlowValidator(MysqlBaseValidator):
    def __call__(self):
        logging.info("tendbCluster rollback flow validator xxxxxxxxxx")
        logging.info(self.data)
        logging.info("tendbCluster rollback flow validator zzzzzzzzzz")
        print(json.dumps(self.data))
        error_msgs = []
        # 以下迁移类型先判断实例是否联通
        if self.data["orphan_restore_type"] in [
            TendbSingleRestoreType.RESTORE_FROM_FLOW_BACKUP.value,
            TendbSingleRestoreType.REPLICATE_WITH_STRUCT.value,
            TendbSingleRestoreType.REPLICATE_WITH_DATA.value,
        ]:
            for index, info in enumerate(self.data["infos"]):
                for cluster_id in info["cluster_ids"]:
                    cluster_model = Cluster.objects.get(id=cluster_id)
                    master_model = cluster_model.storageinstance_set.get(
                        instance_inner_role=InstanceInnerRole.ORPHAN.value
                    )
                    res = DRSApi.rpc(
                        {
                            "addresses": [master_model.ip_port],
                            "cmds": ["show global variables like 'log_bin'"],
                            "force": False,
                            "bk_cloud_id": cluster_model.bk_cloud_id,
                        }
                    )
                    if (
                        res[0]["error_msg"]
                        or res[0]["cmd_results"] is None
                        or len(res[0]["cmd_results"][0]["table_data"]) == 0
                    ):
                        error_msgs.append(
                            msg_format(
                                index, _("集群: {} 无法通过DRS连接,如果是集群故障请通过故障替换提单".format(cluster_model.immute_domain))
                            )
                        )
                    else:
                        if self.data["orphan_restore_type"] in [
                            TendbSingleRestoreType.REPLICATE_WITH_STRUCT.value,
                            TendbSingleRestoreType.REPLICATE_WITH_DATA.value,
                        ]:
                            if res[0]["cmd_results"][0]["table_data"][0]["Value"] == "OFF":
                                error_msgs.append(
                                    msg_format(
                                        index, _("集群: {} 选择了实时同步类型,请保证开启Binlog".format(cluster_model.immute_domain))
                                    )
                                )
            if len(error_msgs) > 0:
                return error_msgs
        return None


def msg_format(index: int = 0, msg="") -> str:
    return _("第{}行:{}").format(index, msg)
