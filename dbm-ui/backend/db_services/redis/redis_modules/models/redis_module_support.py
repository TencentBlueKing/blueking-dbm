from django.db import models
from django.utils.translation import gettext_lazy as _

# CREATE TABLE `tb_redis_module_support` (
#   `major_version` varchar(32) NOT NULL DEFAULT '',
#   `module_name` varchar(32) NOT NULL DEFAULT '',
#   `so_file` varchar(32) NOT NULL DEFAULT '',
#   PRIMARY KEY (`major_version`,`module_name`,`so_file`)
# ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4


class TbRedisModuleSupport(models.Model):
    major_version = models.CharField(_("主版本号"), max_length=32, default="")
    module_name = models.CharField(_("module名"), max_length=32, default="")
    so_file = models.CharField(_("so文件名"), max_length=64, default="")

    class Meta:
        verbose_name = _("Redis module支持")
        verbose_name_plural = _("Redis module支持")
        db_table = "tb_redis_module_support"
        unique_together = (("major_version", "module_name", "so_file"),)

    @classmethod
    def init_default_modules(cls, *args, **kwargs):
        """初始化module 默认数据"""
        default_modules = [
            {"major_version": "Redis-4", "module_name": "redisbloom", "so_file": "redisbloom-2.6.13.so"},
            {"major_version": "Redis-4", "module_name": "rediscell", "so_file": "libredis_cell_0.3.1.so"},
            {"major_version": "Redis-4.0.9", "module_name": "fo4_lock", "so_file": "redis_fo4lock.so"},
            {"major_version": "Redis-4.0.9", "module_name": "fo4_matchmaker", "so_file": "redis_fo4matchmaker.so"},
            {"major_version": "Redis-4.0.9", "module_name": "fo4_util", "so_file": "redis_fo4util.so"},
            {
                "major_version": "Redis-4.0.9",
                "module_name": "jlsy-b2",
                "so_file": "libB2RedisModule_linux64_service30000.so",
            },
            {"major_version": "Redis-4.0.9", "module_name": "redisbloom", "so_file": "redisbloom-2.6.13.so"},
            {"major_version": "Redis-4.0.9", "module_name": "rediscell", "so_file": "libredis_cell_0.3.1.so"},
            {"major_version": "Redis-5", "module_name": "redisbloom", "so_file": "redisbloom-2.6.13.so"},
            {"major_version": "Redis-5", "module_name": "rediscell", "so_file": "libredis_cell_0.3.1.so"},
            {"major_version": "Redis-6", "module_name": "redisbloom", "so_file": "redisbloom-2.6.13.so"},
            {"major_version": "Redis-6", "module_name": "rediscell", "so_file": "libredis_cell_0.3.1.so"},
            {"major_version": "Redis-6", "module_name": "redisjson", "so_file": "librejson-2.6.6.so"},
            {"major_version": "Redis-7", "module_name": "redisbloom", "so_file": "redisbloom-2.6.13.so"},
            {"major_version": "Redis-7", "module_name": "rediscell", "so_file": "libredis_cell_0.3.1.so"},
            {"major_version": "Redis-7", "module_name": "redisjson", "so_file": "librejson-2.6.11.so"},
        ]

        # 获取已存在的记录集合
        existing_set = list(
            cls.objects.filter(
                major_version__in=[module["major_version"] for module in default_modules],
                module_name__in=[module["module_name"] for module in default_modules],
                so_file__in=[module["so_file"] for module in default_modules],
            )
            .values_list("major_version", "module_name", "so_file")
            .distinct()
        )

        # 准备要批量创建的新记录
        modules_to_create = [
            cls(major_version=module["major_version"], module_name=module["module_name"], so_file=module["so_file"])
            for module in default_modules
            if (module["major_version"], module["module_name"], module["so_file"]) not in existing_set
        ]

        # 批量创建新记录
        cls.objects.bulk_create(modules_to_create)


class ClusterRedisModuleAssociate(models.Model):
    """redis集群-module关联表"""

    cluster_id = models.IntegerField(_("集群ID"), default=0)
    module_names = models.JSONField(_("module名称列表"), default=list)

    class Meta:
        verbose_name = _("Cluster Redis module关联")
        verbose_name_plural = _("Cluster Redis module关联")
        db_table = "tb_cluster_redis_module_associate"
        unique_together = (("cluster_id"),)
