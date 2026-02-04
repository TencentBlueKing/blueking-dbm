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

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from rest_framework.response import Response

from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.spec import machine_type_to_spec_machine_type
from backend.db_meta.models import Machine, Spec
from backend.dbm_aiagent.mcp_tools.common.impl.recommend_host_spec import recommend_specs_for_hosts
from backend.dbm_aiagent.mcp_tools.common.serializers.recommend_spec import (
    RecommendSpecInputSerializer,
    RecommendSpecOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.update_machine_spec import (
    UpdateMachineSpecInputSerializer,
    UpdateMachineSpecOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpNotBusinessDBAPrimaryException,
    DBMMcpUsernameNotFoundException,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

logger = logging.getLogger("root")


class DBMetaUpdateMcpToolsViewSet(McpToolsViewSet):
    """Meta Update MCP ViewSet for database administration tasks."""

    default_permission_class = [DBManagePermission()]

    @staticmethod
    def _is_empty_spec_config(spec_config):
        """
        判断规格配置是否为空

        空规格定义:
        - None: 规格未设置
        - {}: 空字典
        - {"id": 0}: id 为 0 表示无效规格

        Args:
            spec_config: 规格配置字典

        Returns:
            bool: True 表示空规格，False 表示有效规格
        """
        if not spec_config:
            return True
        if spec_config == {}:
            return True
        # 判断 {"id": 0} 的情况
        if isinstance(spec_config, dict) and spec_config.get("id") == 0:
            return True
        return False

    def _validate_machines_consistency(self, machines, failed_list):
        """校验所有机器的 cluster_type 和 machine_type 一致"""
        cluster_types = set(machines.values_list("cluster_type", flat=True))
        machine_types = set(machines.values_list("machine_type", flat=True))

        if len(cluster_types) > 1:
            logger.warning(_("机器的 cluster_type 不一致: {}").format(cluster_types))
            for machine in machines:
                failed_list.append(
                    {
                        "ip": machine.ip,
                        "reason": _(
                            "Machines have inconsistent cluster_type: {}. " "机器的 cluster_type 不一致: {}。"
                        ).format(cluster_types, cluster_types),
                    }
                )
            return None, None

        if len(machine_types) > 1:
            logger.warning(_("机器的 machine_type 不一致: {}").format(machine_types))
            for machine in machines:
                failed_list.append(
                    {
                        "ip": machine.ip,
                        "reason": _(
                            "Machines have inconsistent machine_type: {}. " "机器的 machine_type 不一致: {}。"
                        ).format(machine_types, machine_types),
                    }
                )
            return None, None

        return cluster_types.pop(), machine_types.pop()

    def _validate_business_dba_permission(self, machines, username, machine_cluster_type, failed_list):
        """校验用户是否为业务 DBA 负责人"""
        bk_biz_ids = set(machines.values_list("bk_biz_id", flat=True))
        if len(bk_biz_ids) > 1:
            logger.warning(_("机器属于不同业务: {}").format(bk_biz_ids))
            for machine in machines:
                failed_list.append(
                    {
                        "ip": machine.ip,
                        "reason": _("机器属于不同业务，无法批量更新。Machines belong to different businesses."),
                    }
                )
            return None

        bk_biz_id = bk_biz_ids.pop()

        # 将 cluster_type 转换为 db_type
        try:
            db_type = ClusterType.cluster_type_to_db_type(machine_cluster_type)
        except ValueError as e:
            logger.error(_("无法转换 cluster_type: {}").format(e))
            for machine in machines:
                failed_list.append(
                    {
                        "ip": machine.ip,
                        "reason": _(
                            "Cannot convert cluster_type {} to DBType. " "无法将 cluster_type {} 转换为 DBType。"
                        ).format(machine_cluster_type, machine_cluster_type),
                    }
                )
            return None

        # 校验用户是否为业务 DBA 负责人
        try:
            dba_admins = DBAdministrator.objects.get(bk_biz_id=bk_biz_id, db_type=db_type)
            if username not in (dba_admins.users or []):
                logger.warning(
                    _("用户 {} 不是业务 {} 的 {} DBA 负责人，负责人列表: {}").format(username, bk_biz_id, db_type, dba_admins.users)
                )
                raise DBMMcpNotBusinessDBAPrimaryException(username=username, bk_biz_id=bk_biz_id, db_type=db_type)
        except DBAdministrator.DoesNotExist:
            logger.warning(_("业务 {} 未配置 {} DBA 负责人").format(bk_biz_id, db_type))
            raise DBMMcpNotBusinessDBAPrimaryException(username=username, bk_biz_id=bk_biz_id, db_type=db_type)

        return db_type

    def _validate_spec_match(self, spec, machine_db_type, machine_machine_type, machines, failed_list):
        """校验规格与机器类型匹配"""
        if spec.spec_cluster_type != machine_db_type:
            logger.warning(
                _("规格的 spec_cluster_type ({}) 与机器的 DBType ({}) 不匹配").format(spec.spec_cluster_type, machine_db_type)
            )
            for machine in machines:
                failed_list.append(
                    {
                        "ip": machine.ip,
                        "reason": _(
                            "Spec cluster_type ({}) does not match machine DBType ({}). "
                            "规格的 cluster_type ({}) 与机器的 DBType ({}) 不匹配。"
                        ).format(spec.spec_cluster_type, machine_db_type, spec.spec_cluster_type, machine_db_type),
                    }
                )
            return False

        # 将 MachineType 转换为对应的 SpecMachineType 进行比较
        try:
            expected_spec_machine_type = machine_type_to_spec_machine_type(machine_machine_type)
        except ValueError as e:
            logger.warning(_("无法转换 machine_type ({}): {}").format(machine_machine_type, str(e)))
            for machine in machines:
                failed_list.append(
                    {
                        "ip": machine.ip,
                        "reason": _("无法转换机器类型 ({}) 为规格类型: {}").format(machine_machine_type, str(e)),
                    }
                )
            return False

        if spec.spec_machine_type != expected_spec_machine_type:
            logger.warning(
                _("规格的 spec_machine_type ({}) 与机器的 machine_type ({}) 转换后的规格类型 ({}) 不匹配").format(
                    spec.spec_machine_type, machine_machine_type, expected_spec_machine_type
                )
            )
            for machine in machines:
                failed_list.append(
                    {
                        "ip": machine.ip,
                        "reason": _(
                            "Spec machine_type ({}) does not match machine type ({}) converted spec type ({}). "
                            "规格的 machine_type ({}) 与机器类型 ({}) 转换后的规格类型 ({}) 不匹配。"
                        ).format(
                            spec.spec_machine_type,
                            machine_machine_type,
                            expected_spec_machine_type,
                            spec.spec_machine_type,
                            machine_machine_type,
                            expected_spec_machine_type,
                        ),
                    }
                )
            return False

        return True

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Update machine spec configuration in batch. "
                "批量更新机器规格配置。\n\n"
                "**Use Cases / 使用场景:**\n"
                "- Assign spec to newly added machines / 为新增机器分配规格\n"
                "- Correct spec mismatch after migration / 迁移后修正规格不匹配\n"
                "- Batch update spec for capacity planning / 容量规划时批量更新规格\n\n"
                "**Constraints / 约束条件:**\n"
                "- All IPs must have same cluster_type and machine_type / 所有 IP 必须是相同集群类型和机器类型\n"
                "- Spec must match machine's cluster_type (as DBType) and machine_type / "
                "规格必须匹配机器的集群类型和机器类型\n"
                "- Machine's device class (bk_svr_device_cls_name) must be in spec's device_class list / "
                "机器的机型必须在规格的允许机型列表中\n"
                "- By default, only empty spec machines can be updated (use force=True to override) / "
                "默认只能更新空规格机器（使用 force=True 强制覆盖）"
            )
        ),
        request_slz=UpdateMachineSpecInputSerializer,
        response_slz=UpdateMachineSpecOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.DBMETA_UPDATE],
        name_prefix="dba_tool",
    )
    def update_machine_spec(self, request, *args, **kwargs):
        """
        Update machine spec configuration in batch.
        批量更新机器规格配置。
        """
        ip_list = self.get_param("ip_list")
        spec_id = self.get_param("spec_id")
        bk_cloud_id = self.get_param("bk_cloud_id", 0)
        force = self.get_param("force", False)

        failed_list = []
        success_count = 0
        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        # 1. 校验规格存在
        try:
            spec: Spec = Spec.objects.get(spec_id=spec_id)
        except Spec.DoesNotExist:
            logger.warning(_("规格 {} 不存在").format(spec_id))
            return Response(
                {
                    "success_count": 0,
                    "failed_list": [
                        {"ip": ip, "reason": _("Spec {} not found. 规格不存在。").format(spec_id)} for ip in ip_list
                    ],
                }
            )

        # 2. 查询所有机器
        machines = Machine.objects.filter(ip__in=ip_list, bk_cloud_id=bk_cloud_id)
        found_ips = set(machines.values_list("ip", flat=True))
        not_found_ips = set(ip_list) - found_ips

        # 记录未找到的机器
        for ip in not_found_ips:
            failed_list.append(
                {
                    "ip": ip,
                    "reason": _("Machine not found in cloud area {}. 机器在云区域 {} 中未找到。").format(
                        bk_cloud_id, bk_cloud_id
                    ),
                }
            )

        if not machines.exists():
            logger.warning(_("没有找到任何机器: ip_list={}, bk_cloud_id={}").format(ip_list, bk_cloud_id))
            return Response({"success_count": 0, "failed_list": failed_list})

        # 3. 校验所有机器的 cluster_type 和 machine_type 一致
        machine_cluster_type, machine_machine_type = self._validate_machines_consistency(machines, failed_list)
        if machine_cluster_type is None:
            return Response({"success_count": 0, "failed_list": failed_list})

        # 4. 校验用户是否为业务 DBA 负责人
        db_type = self._validate_business_dba_permission(machines, username, machine_cluster_type, failed_list)
        if db_type is None:
            return Response({"success_count": 0, "failed_list": failed_list})

        # 5. 校验规格与机器类型匹配
        if not self._validate_spec_match(spec, db_type, machine_machine_type, machines, failed_list):
            return Response({"success_count": 0, "failed_list": failed_list})

        # 6. 检查空规格限制和机型匹配
        spec_config = spec.get_spec_info()
        spec_device_classes = spec.device_class if spec.device_class else []

        for machine in machines:
            # 判断是否为空规格
            is_empty = self._is_empty_spec_config(machine.spec_config)

            if not is_empty and not force:
                failed_list.append(
                    {
                        "ip": machine.ip,
                        "reason": _(
                            "Machine already has spec_config, use force=True to override. "
                            "机器已有规格配置，使用 force=True 强制覆盖。"
                        ),
                    }
                )
                continue

            # 非强制模式下，校验机器机型是否在规格的 device_class 中
            if not force and spec_device_classes:
                machine_device_class = machine.bk_svr_device_cls_name or ""
                if machine_device_class and machine_device_class not in spec_device_classes:
                    logger.warning(
                        _("机器 {} 的机型 {} 不在规格 {} 的允许机型列表中: {}").format(
                            machine.ip, machine_device_class, spec_id, spec_device_classes
                        )
                    )
                    failed_list.append(
                        {
                            "ip": machine.ip,
                            "reason": _(
                                "Machine device class '{}' is not in spec's allowed device_class list: {}. "
                                "机器机型 '{}' 不在规格的允许机型列表中: {}。"
                            ).format(
                                machine_device_class, spec_device_classes, machine_device_class, spec_device_classes
                            ),
                        }
                    )
                    continue

            # 7. 更新机器规格
            machine.spec_id = spec_id
            machine.spec_config = spec_config
            machine.save(update_fields=["spec_id", "spec_config"])
            success_count += 1
            logger.info(_("成功更新机器 {} 的规格为 {}").format(machine.ip, spec_id))

        return Response({"success_count": success_count, "failed_list": failed_list})

    @mcp_tools_api_decorator(
        description=str(
            gettext_lazy(
                "根据主机信息推荐合适的规格。\n\n"
                "**功能说明 / Function:**\n"
                "- 根据主机的集群类型、机器类型和机型推荐匹配的规格\n"
                "- Recommend specs based on host's cluster type, machine type and device class\n\n"
                "**推荐规则 / Recommendation Rules:**\n"
                "1. spec_cluster_type 必须匹配主机的 cluster_type\n"
                "2. spec_machine_type 必须匹配主机的 machine_type\n"
                "3. 主机的机型（bk_svr_device_cls_name）必须在规格的 device_class 列表中\n"
                "4. 规格的 device_class 不能为空列表\n"
                "5. 规格名称（spec_name）模糊匹配关键字（默认：标准、推荐、standard）\n\n"
                "**输出格式 / Output Format:**\n"
                "- 按 spec_id 聚合，相同规格的主机 IP 合并到 matched_hosts 列表中\n"
                "- Grouped by spec_id, host IPs with same spec are merged into matched_hosts list"
            )
        ),
        request_slz=RecommendSpecInputSerializer,
        response_slz=RecommendSpecOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DBMETA_UPDATE],
        name_prefix="dba_tool",
    )
    def recommend_host_spec(self, request, *args, **kwargs):
        """
        根据主机信息推荐合适的规格
        Recommend suitable specs based on host information
        """
        ip_list = self.get_param("ip_list")
        bk_cloud_id = self.get_param("bk_cloud_id", 0)
        spec_name_keywords = self.get_param("spec_name_keywords", ["标准", "推荐", "standard"])

        # 调用实现层函数
        recommendations, failed_hosts = recommend_specs_for_hosts(
            ip_list=ip_list,
            bk_cloud_id=bk_cloud_id,
            spec_name_keywords=spec_name_keywords,
        )

        return Response({"recommendations": recommendations, "failed_hosts": failed_hosts})
