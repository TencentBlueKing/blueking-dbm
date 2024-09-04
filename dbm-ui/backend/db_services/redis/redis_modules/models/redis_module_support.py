from django.db import models
from django.utils.translation import ugettext_lazy as _

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
