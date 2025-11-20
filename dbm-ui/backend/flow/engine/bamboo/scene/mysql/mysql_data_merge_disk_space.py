import logging
from collections import defaultdict

from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.sync_cluster_stat import query_capacity_for_clusters
from backend.flow.engine.bamboo.scene.mysql.common.statsdb_client import DB_QUERY_TEMPLATE, StatsDBClient

logger = logging.getLogger("root")
DISK_PERCENT_SAFETY_THRESHOLD = 80  # 磁盘安全使用率
DISK_PERCENT_FULL = 100  # 磁盘满载使用率


class MigrateTask(object):
    """
    数据迁移任务
    """

    def __init__(
        self,
        source: int,
        target: int,
        db_list: list,
        clone_db_list: list,
        ignore_db_list: list,
        data_schema_grant: str,
    ):
        self.source = Cluster.objects.get(id=source).immute_domain
        self.target = Cluster.objects.get(id=target).immute_domain
        self.target_cluster_type = Cluster.objects.get(id=target).cluster_type
        self.db_list = db_list
        self.clone_db_list = clone_db_list
        self.ignore_db_list = ignore_db_list
        self.data_schema_grant = data_schema_grant  # 可选"data,schema"或者"schema"
        self.db_size = {}  # GB
        self.same_target_sum_size = 0  # 和当前迁移任务目标主机相同、data盘符相同的迁移任务db大小总和，GB
        self.same_target_index = []  # 和当前迁移任务目标主机相同、data盘符相同的迁移任务index列表
        self.disk_size = dict()
        # 目标主机磁盘大小信息，used_percent 当前磁盘使用率, used_percent_future 预估磁盘使用率, 格式如下：
        # {'used': x, 'total': y, 'used_percent': x,
        # 'mount_point': '/data', 'host': 'x.x.x.x', 'used_percent_future': z}
        self.suggestion = ""  # 评估建议

    def assess_suggestion(self, total_db_size: int, factor: int = 1):
        self.same_target_sum_size = total_db_size
        disk_size = self.disk_size
        lower = round((disk_size["used"] + total_db_size * 1024 * 1024 * 1024) / disk_size["total"] * 100.0, 2)
        upper = round(
            (disk_size["used"] + factor * total_db_size * 1024 * 1024 * 1024) / disk_size["total"] * 100.0, 2
        )
        if factor == 1:
            self.disk_size["used_percent_future"] = "{}%".format(lower)
        else:
            self.disk_size["used_percent_future"] = "{}% ~ {}%".format(lower, upper)
        if upper >= DISK_PERCENT_FULL:
            self.suggestion = _("严重风险")
        elif upper >= DISK_PERCENT_SAFETY_THRESHOLD:
            self.suggestion = _("轻度风险")
        else:
            self.suggestion = _("安全")


def mysql_data_merge_disk_space(bk_biz_id: int, migrations: list = None, factor: int = 1) -> list:
    """
    预估数据合并磁盘使用情况，给出评估建议
    """
    tasks, db_size_sql_placeholders, db_size_sql_params, targets = parameters_from_data_migrate(migrations)
    db_size = get_db_size(db_size_sql_placeholders, db_size_sql_params)
    disk_size, no_disk_stats = get_disk_size(bk_biz_id, targets)
    same_disk = same_target_host_disk(tasks, disk_size, no_disk_stats)
    calulate_disk_size(tasks, db_size, same_disk, factor)
    return tasks


def calulate_disk_size(tasks: list, db_size: dict, same_disk: dict, factor: int = 1):
    """
    计算目标主机相同、data盘符相同的迁移任务db大小合计，预估合并后磁盘使用率
    """
    for task_indices in same_disk.values():
        total_db_size = 0
        no_db_size = False
        for index in task_indices:
            task = tasks[index]
            task.same_target_index = task_indices
            for db in task.db_list:
                if db_size.get("{}|{}".format(task.source, db)) is None:
                    logger.info(_("无源集群:{} db:{} db大小上报数据".format(task.source, db)))
                    no_db_size = True
                    task.db_size[db] = 0
                else:
                    size_gb = db_size.get("{}|{}".format(task.source, db), 0)
                    task.db_size[db] = size_gb
                    total_db_size += size_gb
        for index in task_indices:
            task = tasks[index]
            if no_db_size:
                task.suggestion = _("无源集群db大小上报数据")
            if not task.suggestion:
                task.assess_suggestion(total_db_size, factor)


def same_target_host_disk(tasks: list, disk_size: dict, no_disk_stats: list) -> dict:
    """
    获取目标主机相同、data盘符相同的迁移任务
    """
    same_cluster = defaultdict(list)
    same_disk = defaultdict(list)
    for index, task in enumerate(tasks):
        if task.target in no_disk_stats:
            task.db_size = {db: 0 for db in task.db_list}
            task.suggestion = _("无目标集群磁盘上报数据")
            continue
        task.disk_size = disk_size[task.target]
        if task.data_schema_grant == "schema":
            task.assess_suggestion(total_db_size=0)
            continue
        same_cluster[task.target].append(index)
    for immute_domain, disk in disk_size.items():
        same_disk["{}_{}".format(disk["host"], disk["mount_point"])].extend(same_cluster[immute_domain])
    return dict(same_disk)


def parameters_from_data_migrate(migrations: list = None) -> (list, str, list, dict):
    """
    提取参数
    """
    tasks = []
    placeholders = []
    sql_params = []
    targets = defaultdict(list)
    for info in migrations:
        for target in info["target_clusters"]:
            task = MigrateTask(
                info["source_cluster"],
                target,
                info["db_list"],
                info["clone_db_list"],
                info["ignore_db_list"],
                info["data_schema_grant"],
            )
            targets[task.target_cluster_type].append(task.target)
            if info["data_schema_grant"] == "schema":
                task.db_size = {db: 0 for db in info["db_list"]}
                tasks.append(task)
                continue
            tasks.append(task)
            db_placeholders = ",".join(["%s"] * len(info["db_list"]))
            task_placeholders = "(cluster_domain = %s and database_name IN ({}))".format(db_placeholders)
            placeholders.append(task_placeholders)
            sql_params.append(task.source)
            sql_params.extend(info["db_list"])
    logger.info("placeholders: %s sql_params: %s targets: %s", " or ".join(placeholders), sql_params, targets)
    return tasks, " or ".join(placeholders), sql_params, targets


def get_db_size(placeholders: str, sql_params: list = None) -> dict:
    """
    获取db大小
    """
    logger.info("query_db_size started")
    client = StatsDBClient()
    query_template = DB_QUERY_TEMPLATE.get("DBSIZE") % placeholders
    resp = client.query(query_template, sql_params)
    logger.info("query_db_size finished: %s", resp)
    dict_data = {}
    for record in resp:
        dict_data[record["db"]] = record["gb"]
    logger.info("query_db_size finished: db_size_data: %s", dict_data)
    return dict_data


def get_disk_size(bk_biz_id: int, domains: dict) -> (dict, list):
    """
    获取集群磁盘使用情况
    """
    logger.info("query_cluster_capacity started")
    cluster_cap_bytes = defaultdict(list)
    no_stats = []
    for cluster_type, immute_domains in domains.items():
        if immute_domains:
            disk, no_data = query_capacity_for_clusters(bk_biz_id, cluster_type, list(set(immute_domains)))
            cluster_cap_bytes.update(disk)
            no_stats.extend(no_data)
    logger.info("query_cluster_capacity finished: cluster_cap_bytes: %s no_stats: %s", cluster_cap_bytes, no_stats)
    return cluster_cap_bytes, no_stats
