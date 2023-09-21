import logging

from celery.schedules import crontab
from django.db.models import Q
from django.utils.translation import ugettext as _
from django_celery_beat.schedulers import ModelEntry

from backend.components import MySQLPrivManagerApi
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.models import DBPeriodicTask
from backend.exceptions import ApiResultError
from backend.flow.consts import TDBCTL_USER

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(day_of_week="*", hour="10", minute="3"))
def auto_randomize_password_daily():
    """每日随机化密码"""
    randomize_admin_password(if_async=True, range_type="randmize_daily")


@register_periodic_task(run_every=crontab(minute="*"))
def auto_randomize_password_expired():
    """当密码锁定到期，随机化密码"""
    randomize_admin_password(if_async=True, range_type="randmize_expired")


def randomize_admin_password(if_async: bool, range_type: str):
    """密码随机化定时任务，只随机化mysql数据库"""
    cluster_types = [ClusterType.TenDBCluster.value, ClusterType.TenDBHA.value, ClusterType.TenDBSingle.value]
    cluster_ids = [cluster.id for cluster in Cluster.objects.filter(cluster_type__in=cluster_types)]
    clusters = []
    for cluster_id in cluster_ids:
        clusters.append(get_mysql_instance(cluster_id))
    try:
        MySQLPrivManagerApi.modify_mysql_admin_password(
            params={
                "username": "ADMIN",  # 管理用户
                "component": "mysql",
                "operator": range_type,
                "clusters": clusters,
                "security_rule_name": "password",  # 用于生成随机化密码的安全规则
                "async": if_async,  # 异步执行，避免占用资源
                "range": range_type,  # 被锁定的密码到期，需要被随机化
            },
            raw=True,
        )
    except ApiResultError as e:
        # 捕获接口返回结果异常
        logger.error(_("「接口modify_mysql_admin_password返回结果异常」{}").format(e.message))
    except Exception as e:
        # 捕获接口其他未知异常
        logger.error(_("「接口modify_mysql_admin_password调用异常」{}").format(e))
    return


def get_mysql_instance(cluster_id: int):
    cluster = Cluster.objects.get(id=cluster_id)
    instances = [
        {
            "role": AccessLayer.STORAGE.value,
            "addresses": [
                {
                    "ip": instance.machine.ip,
                    "port": instance.port,
                }
                for instance in cluster.storageinstance_set.all()
            ],
        }
    ]
    # spider节点和tdbctl节点修改密码指令不同，需区别
    if cluster.cluster_type == ClusterType.TenDBCluster:
        spiders = cluster.proxyinstance_set.all()
        dbctls = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )
        instances.append(
            {
                "role": MachineType.SPIDER.value,
                "addresses": [
                    {
                        "ip": instance.machine.ip,
                        "port": instance.port,
                    }
                    for instance in spiders
                ],
            }
        )
        instances.append(
            {
                "role": TDBCTL_USER,
                "addresses": [
                    {
                        "ip": instance.machine.ip,
                        "port": instance.admin_port,
                    }
                    for instance in dbctls
                ],
            },
        )
    return {"bk_cloud_id": cluster.bk_cloud_id, "cluster_type": cluster.cluster_type, "instances": instances}


def modify_periodic_task_run_every(run_every, func_name):
    """修改定时任务的运行周期"""
    model_schedule, model_field = ModelEntry.to_model_schedule(run_every)
    # 不存在抛出错误
    db_task = DBPeriodicTask.objects.get(name__contains=func_name)
    celery_task = db_task.task
    setattr(celery_task, model_field, model_schedule)
    celery_task.save(update_fields=[model_field])


def get_periodic_task_run_every(func_name):
    """获取定时任务的运行周期"""
    db_task = DBPeriodicTask.objects.get(name__contains=func_name)
    return db_task.task.crontab.schedule
