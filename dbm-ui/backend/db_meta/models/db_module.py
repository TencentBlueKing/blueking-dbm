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
import logging
from typing import Any, Dict, List

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from jsonschema.validators import validate

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType, ClusterTypeMachineTypeDefine
from backend.db_meta.models import AppCache
from backend.db_meta.models.db_version import DBVersion

logger = logging.getLogger("root")


class DBVersionInfoContainer(object):
    """
    新版本管理下, db module 的版本信息结构复杂
    如果返回一个字典会很难用, 所以放到一个类对象返回
    """

    def __init__(self, data):
        db_version_id = data["db_version_id"]
        self.db_version: DBVersion = DBVersion.objects.get(pk=db_version_id)
        self.permit_os_type: str = data["permit_os_type"]
        self.permit_os: List[str] = data["permit_os"]


class DBModule(AuditedModel):
    """
    一个 meta_cluster_type 的 db_module 在 cc 上会有 count(meta_type) 个 bk module
    """

    bk_biz_id = models.IntegerField(default=0)
    db_module_name = models.CharField(default="", max_length=200)
    alias_name = models.CharField(default="", max_length=200, help_text=_("dbmodule 别名,用于生成域名"))
    db_module_id = models.BigAutoField(primary_key=True)
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")

    in_upgrade = models.BooleanField(default=False, help_text=_("在升级状态"))
    # 这样一致性才好保证, 虽然数据不直观
    current_db_version_info_dict = models.JSONField(help_text=_("当前版本信息 id"), default=dict)
    target_db_version_info_dict = models.JSONField(help_text=_("目标版本信息 id"), default=dict, null=True, blank=True)

    # 只读控制信息
    extra_info = models.JSONField(help_text=_("扩展信息, mysql/sqlsvr 用到"), default=dict, null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = _("DB模块(DBModule)")
        unique_together = [("db_module_name", "bk_biz_id", "cluster_type")]
        indexes = [
            models.Index(fields=["bk_biz_id", "alias_name"]),
            models.Index(fields=["alias_name"]),
        ]

    @classmethod
    def db_module_map(cls):
        return dict(cls.objects.values_list("db_module_id", "db_module_name"))

    @classmethod
    def get_choices(cls):
        try:
            db_module_choices = [
                (module.db_module_id, f"[{module.db_module_id}]{module.cluster_type}-{module.db_module_name}")
                for module in cls.objects.all()
            ]
        except Exception:  # pylint: disable=broad-except
            # 忽略出现的异常，此时可能因为表未初始化
            db_module_choices = []
        return db_module_choices

    @classmethod
    def get_choices_with_filter(cls, cluster_type=None):
        try:
            q = Q()
            if cluster_type:
                q = Q(cluster_type=cluster_type)

            db_module_choices = []
            appcache_dict = AppCache.get_appcache(key="appcache_dict")

            for dm in cls.objects.filter(q).all():
                appcache = appcache_dict.get(str(dm.bk_biz_id))
                db_app_abbr = appcache["db_app_abbr"] if appcache else ""
                db_module_choices.append(
                    (
                        dm.db_module_id,
                        f"[{dm.db_module_id}]-" f"[{dm.cluster_type}]-[app:{db_app_abbr}]-" f"{dm.db_module_name}",
                    )
                )

        except Exception as err:  # pylint: disable=broad-except
            # 忽略出现的异常，此时可能因为表未初始化
            logger.warning("DBModule get_choices_with_filter error, {}".format(err))
            db_module_choices = []
        return db_module_choices

    @property
    def current_db_version(self) -> Dict[str, DBVersionInfoContainer]:
        return self.__db_version_getter(DBModule.current_db_version_info_dict.field.name)

    @property
    def target_db_version(self) -> Dict[str, DBVersionInfoContainer]:
        return self.__db_version_getter(DBModule.target_db_version_info_dict.field.name)

    @current_db_version.setter
    def current_db_version(self, data: Dict):
        """
        支持partial set
        这样调用
        dm.current_db_version = {
          'proxy':{
            'db_version_id': 1,
            'permit_os_type': 'windows',
            'permit_os': ['2005', '2006']
          }
        }
        dm.save()
        """
        self.__db_version_setter(DBModule.current_db_version_info_dict.field.name, data)

    @target_db_version.setter
    def target_db_version(self, data: Dict):
        self.__db_version_setter(DBModule.target_db_version_info_dict.field.name, data)

    def __db_version_getter(self, field_name: str) -> Dict[str, DBVersionInfoContainer]:
        """
        返回字典的 key 是集群类型的 machine type
        """
        res = {}
        machine_types = ClusterTypeMachineTypeDefine[self.cluster_type]
        if self.cluster_type == ClusterType.TenDBCluster:
            machine_types.append("tdbctl")

        for m in machine_types:
            data = getattr(self, field_name, None)
            if data and m.value in data:
                res[m.value] = DBVersionInfoContainer(data=data[m.value])

        return res

    def __db_version_setter(self, field_name: str, data: Dict):
        """
        字典的 key 是集群类型的 machine type
        tendbsingle 样例
        data = {
            "single": {
                "db_version_id": 1,
                "permit_os_type": "Linux",
                "permit_os": ["tlinux", "centos"]
            }
        }
        tendbha 样例
        data = {
            "proxy": {
                "db_version_id": 1,
                "permit_os_type": "Linux",
                "permit_os": ["tlinux", "centos"]
            }
        }
                支持只输入部分 machine type 做 partial update
        """
        machine_types = ClusterTypeMachineTypeDefine[self.cluster_type]

        # 中控不是个 machine type
        # 为了方便写代码, 注入伪造下
        if self.cluster_type == ClusterType.TenDBCluster:
            machine_types.append("tdbctl")

        # list 转换不能少, 相当于 copy
        # 不然会报 RuntimeError: dictionary changed size during iteration
        # 这样的预处理能增加操作的容错性
        for k in list(data.keys()):
            if k not in machine_types:
                del data[k]

        # key 都是 optional 的
        # 这样能方便的 partial update
        schema = {
            "type": "object",
            "$defs": {
                "version_description": {
                    "type": "object",
                    "properties": {
                        "db_version_id": {"type": "integer"},
                        "permit_os_type": {"type": "string"},
                        "permit_os": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["db_version_id", "permit_os_type", "permit_os"],
                    "additionalProperties": False,
                }
            },
            "properties": {m: {"$ref": "#/$defs/version_description"} for m in machine_types},
            "propertyNames": {"enum": machine_types},
            "additionalProperties": False,
        }
        validate(instance=data, schema=schema)

        db_type = ClusterType.cluster_type_to_db_type(self.cluster_type)

        # 校验 dbtype 和 pkgtype 是不是吻合
        for machine_type, mdata in data.items():
            # 目前只校验了 dbtype
            # 这里有个问题
            # 可以给 backend 绑定一个 proxy 的 db version
            # ToDo 该如何验证呢
            # ToDo 似乎需要一个 cluster_type-machine_type 和 db_type-pkg_type 的映射
            DBVersion.objects.get(
                pk=mdata["db_version_id"],
                distribution_snapshot__db_type=db_type,
            )

        original_data = getattr(self, field_name)
        original_data.update(data)

        self.current_db_version_info_dict = original_data

    def query_user_conf(self) -> Any:
        """
        这是个占位方法
        新的版本管理中, 类似 my.cnf 这样的信息成为 dbconfig 中的 user conf
        user conf 在 dbconfig 中以 bkbizid-dbmoduleid-fullversion (未定) 做唯一键
        在 TenDBCluster 集群的场景下要分别能够返回
        spider-current, spider-target, remote-current, remote-target 的 user conf
        由于 target version 会在升级中途切换, 所以 dbconfig 中的 user conf 原则上来说新建后是不能删的
        另外, query_user_conf 方法肯定不是放在 dbmodule 里
        因为集群的扩缩容, 迁移这样涉及新增机器的情况是需要独立获得 user conf
        """
        pass


# 讨论后, 原本决定从 dbconfig 挪回 dbmeta 的只读控制信息, 还是放在 dbconfig
# 所以目前挪过来的只有 engine 一个
# class DBModuleExt(AuditedModel):
#     """
#     目前只有 MySQL 和 SqlServer 用到了 dbmodule
#     特有的扩展信息放到 ext 里
#     """
#
#     db_module = models.OneToOneField(DBModule, on_delete=models.PROTECT)
#     ext_info = models.JSONField(help_text=_("扩展信息, mysql/sqlsvr 用到"))
