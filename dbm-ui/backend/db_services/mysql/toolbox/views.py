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
import traceback
from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, ClusterEntry, DBModule
from backend.db_services.mysql.toolbox.handlers import ToolboxHandler
from backend.db_services.mysql.toolbox.serializers import GetSpiderVersionModulesSerializer  # 新增
from backend.db_services.mysql.toolbox.serializers import (
    ChangeClusterSpecSerializer,
    GetStorageVersionModulesSerializer,
    MysqlDiskSpace,
    MySQLRollbackExerciseByClusterSerializer,
    QueryPkgListByCompareVersionSerializer,
    QuerySpiderPkgListByCompareVersionSerializer,
    TdbctlUpgradeProgressSerializer,
    TdbctlUpgradeRecordsSerializer,
    TdbctlUpgradeScheduleSerializer,
    TdbctlUpgradeSerializer,
    TendbhaAddSlaveDomainSerializer,
    TendbhaTransferToOtherBizSerializer,
)
from backend.db_services.mysql.toolbox.storage_upgrade_tool import get_storage_version_modules_api
from backend.db_services.mysql.toolbox.tdbctl_upgrade_handler import TdbctlUpgradeHandler
from backend.db_services.mysql.toolbox.tdbctl_upgrade_scheduler import (
    TdbctlUpgradeScheduler,
    _check_any_biz_lock_exists,
    _is_global_lock_held,
    tdbctl_upgrade_task,
)
from backend.db_services.mysql.toolbox.upgrade_tool import get_spider_version_modules_api
from backend.flow.engine.bamboo.scene.mysql.mysql_data_merge_disk_space import mysql_data_merge_disk_space
from backend.flow.engine.controller.mysql_backup_data_recovery_exercise import MySQLBackupDataRecoveryController
from backend.flow.utils.dns_manage import DnsManage
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


SWAGGER_TAG = "db_services/mysql/toolbox"


class ToolboxViewSet(viewsets.SystemViewSet):
    """工具箱视图集

    Args:
        viewsets (_type_): _description_

    Returns:
        _type_: _description_
    """

    default_permission_class = [DBManagePermission()]

    # This method is deprecated, use `query_higher_version_pkg_list` instead
    @common_swagger_auto_schema(
        operation_summary=_("查询 MySQL 可以用的升级包"),
        request_body=QueryPkgListByCompareVersionSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryPkgListByCompareVersionSerializer)
    def query_higher_version_pkg_list(self, request, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id, higher_major_version, higher_all_version = (
            data["cluster_id"],
            data["higher_major_version"],
            data["higher_all_version"],
        )
        return Response(
            ToolboxHandler().query_higher_version_pkg_list(cluster_id, higher_major_version, higher_all_version)
        )

    # This method is deprecated, use `query_spider_higher_version_pkg_list` instead
    @common_swagger_auto_schema(
        operation_summary=_("查询 Spider 可以用的升级包"),
        request_body=QuerySpiderPkgListByCompareVersionSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QuerySpiderPkgListByCompareVersionSerializer)
    def query_spider_higher_version_pkg_list(self, request, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id, higher_major_version, higher_sub_version = (
            data["cluster_id"],
            data["higher_major_version"],
            data["higher_sub_version"],
        )
        return Response(
            ToolboxHandler().query_higher_spider_ver_pkgs(cluster_id, higher_major_version, higher_sub_version)
        )

    @common_swagger_auto_schema(
        operation_summary=_("更改集群规格"),
        request_body=ChangeClusterSpecSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ChangeClusterSpecSerializer)
    def change_cluster_spec(self, request, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id = data["cluster_id"]
        cluster_type = data["cluster_type"]
        spec_id = data["spec_id"]
        machine_type = data["machine_type"]

        result = ToolboxHandler().change_cluster_spec(cluster_id, cluster_type, spec_id, machine_type)
        return Response(result)

    @common_swagger_auto_schema(
        operation_summary=_("获取spider版本模块列表"),
        request_body=GetSpiderVersionModulesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GetSpiderVersionModulesSerializer)
    def get_spider_version_modules(self, request, **kwargs):
        """
        统一的API接口：获取spider版本模块列表
        通过 higher_major_version 和 higher_sub_version 参数来控制查找策略
        """
        data = self.params_validate(self.get_serializer_class())
        cluster_id = data["cluster_id"]
        higher_major_version = data["higher_major_version"]
        higher_sub_version = data["higher_sub_version"]

        # 从请求中获取业务ID，如果没有则从URL参数中获取
        bk_biz_id = getattr(request, "bk_biz_id", None)
        if not bk_biz_id:
            # 如果从请求中无法获取，可以从集群信息中获取
            from backend.db_meta.models import Cluster

            try:
                cluster = Cluster.objects.get(id=cluster_id)
                bk_biz_id = cluster.bk_biz_id
            except Cluster.DoesNotExist:
                return Response(
                    {
                        "code": 1,
                        "result": False,
                        "message": _("集群 %(cluster_id)s 不存在") % {"cluster_id": cluster_id},
                        "data": [],
                    }
                )

        result = get_spider_version_modules_api(
            cluster_id=cluster_id,
            bk_biz_id=bk_biz_id,
            higher_major_version=higher_major_version,
            higher_sub_version=higher_sub_version,
        )

        return Response(result)

    @common_swagger_auto_schema(
        operation_summary=_("获取存储层版本模块列表"),
        request_body=GetStorageVersionModulesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GetStorageVersionModulesSerializer)
    def get_storage_version_modules(self, request, **kwargs):
        """
        统一的API接口：获取存储层版本模块列表
        通过 higher_major_version 和 higher_sub_version 参数来控制查找策略
        """
        data = self.params_validate(self.get_serializer_class())
        cluster_id = data["cluster_id"]
        higher_major_version = data["higher_major_version"]
        higher_sub_version = data["higher_sub_version"]

        logger.info(
            _("API请求获取存储层版本模块 - cluster_id: {}, higher_major_version: {}, higher_sub_version: {}").format(
                cluster_id, higher_major_version, higher_sub_version
            )
        )

        # 根据集群ID获取业务ID
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            bk_biz_id = cluster.bk_biz_id
            logger.info(_("获取到集群 {} 的业务ID: {}").format(cluster_id, bk_biz_id))
        except Cluster.DoesNotExist:
            logger.error(_("集群 {} 不存在").format(cluster_id))
            return Response(
                {
                    "code": 1,
                    "result": False,
                    "message": _("集群 %(cluster_id)s 不存在") % {"cluster_id": cluster_id},
                    "data": [],
                }
            )

        result = get_storage_version_modules_api(
            cluster_id=cluster_id,
            bk_biz_id=bk_biz_id,
            higher_major_version=higher_major_version,
            higher_sub_version=higher_sub_version,
        )

        logger.info(
            _("API响应结果 - code: {}, result: {}, data数量: {}").format(
                result.get("code"), result.get("result"), len(result.get("data", []))
            )
        )

        return Response(result)

    @common_swagger_auto_schema(
        operation_summary=_("按集群执行MySQL回档演练"),
        request_body=MySQLRollbackExerciseByClusterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=MySQLRollbackExerciseByClusterSerializer)
    def rollback_exercise_by_cluster(self, request, **kwargs):
        """
        按集群执行MySQL回档演练
        支持指定备份ID或自动查询最近3天的备份记录
        """
        data = self.params_validate(self.get_serializer_class())
        logger.info(_("开始按集群执行MySQL回档演练: cluster_id={}").format(data["cluster_id"]))

        root_id = generate_root_id()
        logger.info(_("生成root_id: {}").format(root_id))

        # 调用Controller处理业务逻辑
        try:
            flow = MySQLBackupDataRecoveryController(root_id, data)
            flow.mysql_rollback_exercise_by_cluster()
            return Response({"root_id": root_id, "result": True, "message": _("回档演练任务已启动")})
        except ValueError as e:
            logger.error(_("回档演练失败: {}").format(str(e)))
            return Response({"root_id": root_id, "result": False, "message": _("回档演练失败")}, status=400)
        except Exception as e:
            logger.exception(_("回档演练异常: {}").format(str(e)))
            return Response({"root_id": root_id, "result": False, "message": _("回档演练异常")}, status=500)

    @common_swagger_auto_schema(
        operation_summary=_("待办处理"),
        request_body=MysqlDiskSpace(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=MysqlDiskSpace)
    def mysql_disk_space(self, request, *args, **kwargs):
        """
        评估 MySQL数据融合磁盘空间大小
        """
        validated_data = self.params_validate(self.get_serializer_class())
        check_data = mysql_data_merge_disk_space(
            validated_data["bk_biz_id"], validated_data["migrations"], validated_data["factor"]
        )
        return Response(data=check_data)


class TendbHaSlaveInstanceAddDomainSet(viewsets.SystemViewSet):
    """
    给从库添加域名
    """

    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("给从库添加域名"),
        request_body=TendbhaAddSlaveDomainSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TendbhaAddSlaveDomainSerializer)
    def slave_ins_add_domain(self, request, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id = data["cluster_id"]
        domain = data["domain_name"]
        slave_ip = data["slave_ip"]
        slave_port = data["slave_port"]
        cluster_obj = Cluster.objects.get(id=cluster_id)
        if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=domain).exists():
            cluster_entry = ClusterEntry.objects.get(cluster_id=cluster_id, entry=domain)
        else:
            cluster_entry = ClusterEntry.objects.create(
                cluster=cluster_obj,
                cluster_entry_type=ClusterEntryType.DNS.value,
                entry=domain,
                role=ClusterEntryRole.SLAVE_ENTRY.value,
            )
        dns_manage = DnsManage(bk_biz_id=cluster_obj.bk_biz_id, bk_cloud_id=cluster_obj.bk_cloud_id)
        slave_ins = cluster_obj.storageinstance_set.filter(
            instance_inner_role=InstanceInnerRole.SLAVE.value, machine__ip=slave_ip, port=slave_port
        )
        cluster_entry.storageinstance_set.add(*slave_ins)
        try:
            dns_manage.create_domain(instance_list=["{}#{}".format(slave_ip, str(slave_port))], add_domain_name=domain)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(_("添加dns记录失败:{}".format(e)))
            return Response({"result": False, "message": _("添加dns记录失败")})
        return Response({"result": True, "message": _("success")})


class TendbhaTransferToOtherBizViewSet(viewsets.SystemViewSet):
    """
    转移tendbha 集群到其他业务
    """

    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("TenDBHA 集群转移到其他业务"),
        request_body=TendbhaTransferToOtherBizSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TendbhaTransferToOtherBizSerializer)
    def transfer_tendbha_to_other_biz(self, request, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        logger.info(_("请求数据: {}").format(data))
        db_module_id = data["db_module_id"]
        target_biz_id = data["target_biz_id"]
        bk_biz_id = data["bk_biz_id"]
        cluster_domain_list = data["cluster_domain_list"]

        result = DBModule.objects.filter(db_module_id=db_module_id, bk_biz_id=target_biz_id)
        if not result.exists():
            return Response({"result": False, "message": _("目标业务的db模块不存在")})
        if target_biz_id == bk_biz_id:
            return Response({"result": False, "message": _("目标业务不能是自己")})

        clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain__in=cluster_domain_list).all()
        source_db_module_ids = []
        cluster_types = []
        for cluster in clusters:
            source_db_module_ids.append(cluster.db_module_id)
            cluster_types.append(cluster.cluster_type)

        uniq_cluster_types = list(set(cluster_types))
        if len(uniq_cluster_types) != 1:
            return Response({"result": False, "message": _("迁移的集群必须在同一个类型")})

        cluster_type = uniq_cluster_types[0]
        if cluster_type not in [ClusterType.TenDBHA.value, ClusterType.TenDBSingle.value]:
            return Response({"result": False, "message": _("目前只能转移 TenDBHA 和 TenDBSingle 集群")})

        target_module_db_version, target_module_charset = self.__get_version_and_charset(
            target_biz_id, db_module_id, cluster_type
        )

        for src_db_module_id in list(set(source_db_module_ids)):
            src_module_db_version, src_module_charset = self.__get_version_and_charset(
                bk_biz_id, src_db_module_id, cluster_type
            )
            if src_module_db_version != target_module_db_version or src_module_charset != target_module_charset:
                return Response({"result": False, "message": _("源模块和目标模块的版本或字符集不一致,请检查一下")})

        TendbhaTransferToOtherBizSerializer(data=data).is_valid(raise_exception=True)
        Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_HA_TRANSFER_TO_OTHER_BIZ,
            creator=request.user.username,
            bk_biz_id=data["bk_biz_id"],
            remark=self.transfer_tendbha_to_other_biz.__name__,
            details=data,
        )
        return Response(data)

    def __get_version_and_charset(self, bk_biz_id, db_module_id, cluster_type) -> Any:
        """获取版本号和字符集信息"""
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.MODULE,
                "level_value": str(db_module_id),
                "conf_file": "deploy_info",
                "conf_type": "deploy",
                "namespace": cluster_type,
                "format": FormatType.MAP,
            }
        )["content"]
        return data["charset"], data["db_version"]


class TdbctlUpgradeViewSet(viewsets.SystemViewSet):
    """
    TdbCtl 全局升级调度视图集

    提供以下接口：
    - schedule: 触发一批集群升级
    - progress: 查询升级进度
    - records: 查询升级记录
    """

    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("触发 tdbctl 升级调度"),
        request_body=TdbctlUpgradeScheduleSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TdbctlUpgradeScheduleSerializer)
    def schedule(self, request, **kwargs):
        """
        触发 tdbctl 升级调度（异步）

        调度一批集群进行 tdbctl 升级，支持：
        - 指定业务范围
        - 指定每批集群数量
        - 自动过滤已成功或正在升级的集群
        - 后台异步执行，按业务串行调度
        """
        data = self.params_validate(self.get_serializer_class())
        logger.info(_("开始 tdbctl 升级调度（异步）: {}").format(data))

        try:
            # 先验证升级包是否存在
            TdbctlUpgradeScheduler(
                pkg_id=data["pkg_id"],
                bk_biz_ids=data.get("bk_biz_ids"),
            )

            # 前置锁检查，避免提交后在异步任务中静默失败
            is_global_schedule = not data.get("bk_biz_ids")
            if is_global_schedule:
                # 全局调度：检查全局锁和业务锁
                if _is_global_lock_held():
                    return Response(
                        {"result": False, "message": _("全局锁被持有，可能存在其他全局调度任务正在执行，请稍后重试")},
                        status=409,
                    )
                locked_biz_ids = _check_any_biz_lock_exists()
                if locked_biz_ids:
                    return Response(
                        {
                            "result": False,
                            "message": _("存在业务锁，无法执行全局调度，被锁定的业务ID: {}").format(locked_biz_ids),
                        },
                        status=409,
                    )
            else:
                # 业务粒度调度：检查全局锁
                if _is_global_lock_held():
                    return Response(
                        {"result": False, "message": _("全局锁被持有，无法执行业务粒度调度，请稍后重试")},
                        status=409,
                    )

            # 异步执行升级调度任务（后台按业务串行调度）
            task_result = tdbctl_upgrade_task.apply_async(
                kwargs={
                    "pkg_id": data["pkg_id"],
                    "bk_biz_ids": data.get("bk_biz_ids"),
                    "batch_size": data.get("batch_size", 20),
                    "operator": request.user.username,
                    "schedule_interval_seconds": data.get("schedule_interval_seconds", 180),
                }
            )

            logger.info(_("tdbctl 升级调度任务已提交，task_id={}").format(task_result.id))

            return Response(
                {
                    "result": True,
                    "message": _("升级调度任务已提交，后台按业务串行执行中"),
                    "task_id": task_result.id,
                    "pkg_id": data["pkg_id"],
                    "bk_biz_ids": data.get("bk_biz_ids"),
                    "batch_size": data.get("batch_size", 20),
                    "schedule_interval_seconds": data.get("schedule_interval_seconds", 180),
                }
            )
        except ValueError as e:
            logger.error(_("tdbctl 升级调度参数错误 {}").format(str(e)))
            return Response({"result": False, "message": _("tdbctl 升级调度参数错误")}, status=400)
        except Exception as e:
            logger.exception(_("tdbctl 升级调度异常: {}").format(str(e)))
            return Response(
                {"result": False, "message": _("tdbctl 升级调度异常")},
                status=500,
            )

    @common_swagger_auto_schema(
        operation_summary=_("查询 tdbctl 升级进度"),
        request_body=TdbctlUpgradeProgressSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TdbctlUpgradeProgressSerializer)
    def progress(self, request, **kwargs):
        """
        查询 tdbctl 升级进度

        返回：
        - 总集群数
        - 各状态集群数量（待升级、升级中、成功、失败、跳过）
        """
        data = self.params_validate(self.get_serializer_class())
        logger.info(_("查询 tdbctl 升级进度: {}").format(data))

        try:
            scheduler = TdbctlUpgradeScheduler(
                pkg_id=data["pkg_id"],
                bk_biz_ids=data.get("bk_biz_ids"),
            )
            result = scheduler.get_upgrade_progress()
            return Response({"result": True, "data": result})
        except ValueError as e:
            logger.error(_("查询升级进度参数错误: {}").format(str(e)))
            return Response({"result": False, "message": _("查询升级进度参数错误")}, status=400)
        except Exception as e:
            logger.exception(_("查询升级进度异常: {}").format(str(e)))
            return Response(
                {"result": False, "message": _("查询异常")},
                status=500,
            )

    @common_swagger_auto_schema(
        operation_summary=_("查询 tdbctl 升级记录"),
        request_body=TdbctlUpgradeRecordsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TdbctlUpgradeRecordsSerializer)
    def records(self, request, **kwargs):
        """
        查询 tdbctl 升级记录

        支持按状态、集群ID过滤，支持分页
        """
        data = self.params_validate(self.get_serializer_class())
        logger.info(_("查询 tdbctl 升级记录: {}").format(data))

        try:
            scheduler = TdbctlUpgradeScheduler(
                pkg_id=data["pkg_id"],
                bk_biz_ids=data.get("bk_biz_ids"),
            )
            result = scheduler.get_upgrade_records(
                status=data.get("status"),
                cluster_id=data.get("cluster_id"),
                limit=data.get("limit", 100),
                offset=data.get("offset", 0),
            )
            return Response({"result": True, "data": result})
        except ValueError as e:
            logger.error(_("查询升级记录参数错误: {}").format(str(e)))
            return Response({"result": False, "message": _("查询升级记录参数错误")}, status=400)
        except Exception as e:
            logger.exception(_("查询升级记录异常: {}").format(str(e)))
            return Response(
                {"result": False, "message": _("查询升级记录异常")},
                status=500,
            )

    @common_swagger_auto_schema(
        operation_summary=_("同步执行 tdbctl 升级"),
        request_body=TdbctlUpgradeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TdbctlUpgradeSerializer)
    def upgrade(self, request, **kwargs):
        """
        同步执行 tdbctl 升级

        功能说明：
        1. 验证升级包是否存在
        2. 根据 upgrade_all 确定要升级的集群
        3. 校验并过滤已升级的集群（版本已是最新的跳过）
        4. 同步调用 UpgradeTdbctlFlow
        """
        data = self.params_validate(self.get_serializer_class())

        try:
            handler = TdbctlUpgradeHandler(
                bk_biz_id=data["bk_biz_id"],
                pkg_id=data["pkg_id"],
                operator=request.user.username,
            )
            result = handler.upgrade(
                cluster_ids=data.get("cluster_ids", []),
                upgrade_all=data.get("upgrade_all", False),
            )
            return Response(result)
        except ValueError as e:
            logger.error(_("tdbctl 升级参数错误: {}").format(str(e)))
            return Response({"result": False, "message": _("tdbctl 升级参数错误")}, status=400)
        except Exception as e:
            logger.exception(_("tdbctl 升级异常: {}").format(str(e)))
            return Response(
                {"result": False, "message": _("tdbctl 升级异常")},
                status=500,
            )

    @common_swagger_auto_schema(
        operation_summary=_("创建 tdbctl 升级单据"),
        request_body=TdbctlUpgradeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TdbctlUpgradeSerializer)
    def create_upgrade_ticket(self, request, **kwargs):
        """
        创建 tdbctl 升级单据

        功能说明：
        1. 验证请求参数的有效性
        2. 创建升级单据，待审批后执行
        3. 支持指定集群ID列表或升级业务下所有集群

        返回：
        - 单据ID
        - 单据详情
        """
        data = self.params_validate(self.get_serializer_class())
        logger.info(_("创建 tdbctl 升级单据: {}").format(data))

        try:
            # 验证参数
            TdbctlUpgradeSerializer(data=data).is_valid(raise_exception=True)

            # 创建单据
            ticket = Ticket.create_ticket(
                ticket_type=TicketType.TENDBCLUSTER_TDBCTL_UPGRADE.value,
                creator=request.user.username,
                bk_biz_id=data["bk_biz_id"],
                remark=_("TdbCtl 升级"),
                details=data,
            )

            logger.info(
                _("TdbCtl 升级单据创建成功: ticket_id={}, bk_biz_id={}, pkg_id={}").format(
                    ticket.id, data["bk_biz_id"], data["pkg_id"]
                )
            )

            return Response(
                {
                    "result": True,
                    "message": _("升级单据创建成功"),
                    "data": {
                        "ticket_id": ticket.id,
                        "bk_biz_id": data["bk_biz_id"],
                        "pkg_id": data["pkg_id"],
                        "cluster_ids": data.get("cluster_ids", []),
                        "upgrade_all": data.get("upgrade_all", False),
                    },
                }
            )
        except ValueError as e:
            logger.error(_("创建升级单据参数错误: {}").format(str(e)))
            return Response({"result": False, "message": _("创建升级单据参数错误")}, status=400)
        except Exception as e:
            logger.exception(_("创建升级单据异常: {}").format(str(e)))
            return Response(
                {"result": False, "message": _("创建升级单据异常")},
                status=500,
            )
