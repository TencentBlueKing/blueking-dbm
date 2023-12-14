import logging.config

from backend.components import DRSApi
from backend.db_meta.models import Cluster
from backend.flow.utils.mysql.common.compare_time import compare_time

logger = logging.getLogger("root")


def get_local_backup(instances: list, cluster: Cluster):
    """
    @param instances:实例列表 ip:port
    @param cluster: 集群
    @return: dict
    """
    backups = []
    for addr in instances:
        res = DRSApi.rpc(
            {
                "addresses": addr,
                "cmds": [
                    "select * from infodba_schema.local_backup_report where "
                    "server_id=@@server_id AND backup_end_time>DATE_SUB(CURDATE(),INTERVAL 1 WEEK) "
                    "and is_full_backup=1 order by backup_end_time desc limit 1"
                ],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            logging.error("{} get backup info error {}".format(addr, res[0]["error_msg"]))
            continue
        if (
            isinstance(res[0]["cmd_results"][0]["table_data"], list)
            and len(res[0]["cmd_results"][0]["table_data"]) > 0
        ):
            backup_tmp = res[0]["cmd_results"][0]["table_data"][0]
            backup_tmp["addr"] = addr
            backups.append(backup_tmp)

    # 多份备份比较 backup map 列表....
    backup_time = "2000-01-01 00:00:00"
    if len(backups) > 0:
        max_backup = backups[0]
        for backup in backups:
            if compare_time(backup["backup_end_time"], backup_time):
                backup_time = backup["backup_end_time"]
                max_backup = backup
        return max_backup
    else:
        return None
