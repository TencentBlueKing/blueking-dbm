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
import logging.config
from dataclasses import asdict

from django.db import transaction
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DBConfigApi
from backend.components.cc.client import CCApi
from backend.components.dns.client import DnsApi
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import AppCache, Cluster, ClusterEntry, Machine, NosqlStorageSetDtl
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    ClusterDbmonInstallAtomJob,
    SingleClusterDbmonInstallAtomJob,
)
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")

# Redis 主从版实例类型列表（单机多实例场景）
REDIS_INSTANCE_CLUSTER_TYPES = [
    ClusterType.TendisRedisInstance.value,
    ClusterType.TendisTendisSSDInstance.value,
    ClusterType.TendisTendisplusInsance.value,
]


class RedisUpdateDBMetaService(BaseService):
    """更新 Redis DB 元数据 Service"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_id = kwargs["cluster"]["cluster_id"]
        target_bk_biz_id = kwargs["cluster"]["target_bk_biz_id"]
        source_bk_biz_id = kwargs["cluster"]["source_bk_biz_id"]

        self.log_info(
            _("开始更新 DB 元数据: cluster_id={}, 源业务ID={}, 目标业务ID={}").format(cluster_id, source_bk_biz_id, target_bk_biz_id)
        )

        try:
            # 使用事务保护，确保所有更新操作要么全部成功，要么全部回滚
            with transaction.atomic():
                cluster = Cluster.objects.select_for_update().get(id=cluster_id, bk_biz_id=source_bk_biz_id)
                self.log_info(
                    _("获取集群信息成功: domain={}, cluster_type={}").format(cluster.immute_domain, cluster.cluster_type)
                )

                # 更新代理实例业务ID
                proxy_count = cluster.proxyinstance_set.all().update(bk_biz_id=target_bk_biz_id)
                self.log_info(_("更新代理实例业务ID完成: 共更新 {} 个代理实例").format(proxy_count))

                # 更新存储实例业务ID
                storage_count = cluster.storageinstance_set.all().update(bk_biz_id=target_bk_biz_id)
                self.log_info(_("更新存储实例业务ID完成: 共更新 {} 个存储实例").format(storage_count))

                # 更新存储集详情业务ID
                set_dtl_count = NosqlStorageSetDtl.objects.filter(cluster_id=cluster_id).update(
                    bk_biz_id=target_bk_biz_id
                )
                self.log_info(_("更新存储集详情业务ID完成: 共更新 {} 条记录").format(set_dtl_count))

                # 更新机器业务ID
                machine_ids = set()
                machine_ids.update(cluster.storageinstance_set.values_list("machine_id", flat=True))
                machine_ids.update(cluster.proxyinstance_set.values_list("machine_id", flat=True))
                Machine.objects.filter(bk_host_id__in=machine_ids).update(bk_biz_id=target_bk_biz_id)
                self.log_info(_("更新机器业务ID完成: 共更新 {} 台机器").format(len(machine_ids)))

                # 更新集群业务ID
                cluster.bk_biz_id = target_bk_biz_id
                cluster.save(update_fields=["bk_biz_id"])
                self.log_info(_("更新集群业务ID完成"))

                self.log_info(
                    _("更新 DB 元数据成功: cluster_id={}, domain={}, cluster_type={}, {} -> {}").format(
                        cluster_id,
                        cluster.immute_domain,
                        cluster.cluster_type,
                        source_bk_biz_id,
                        target_bk_biz_id,
                    )
                )
                return True
        except Exception as e:
            self.log_error(_("更新 DB 元数据失败: cluster_id={}, 错误信息: {}").format(cluster_id, str(e)))
            return False


class RedisUpdateDBMetaComponent(Component):
    name = __name__
    code = "redis_update_db_meta"
    bound_service = RedisUpdateDBMetaService


class RedisUpdateCCService(BaseService):
    """更新 CC 标签和主机属性 Service"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_id = kwargs["cluster"]["cluster_id"]

        self.log_info(_("开始更新 CC 数据: cluster_id={}").format(cluster_id))

        try:
            cluster = Cluster.objects.get(id=cluster_id)
            self.log_info(
                _("获取集群信息成功: domain={}, cluster_type={}").format(cluster.immute_domain, cluster.cluster_type)
            )

            # 获取存储实例和代理实例ID
            storage_instance_ids = list(
                cluster.storageinstance_set.exclude(bk_instance_id=0).values_list("bk_instance_id", flat=True)
            )
            proxy_instance_ids = list(
                cluster.proxyinstance_set.exclude(bk_instance_id=0).values_list("bk_instance_id", flat=True)
            )
            self.log_info(
                _("获取实例ID完成: 存储实例 {} 个, 代理实例 {} 个").format(len(storage_instance_ids), len(proxy_instance_ids))
            )

            bk_biz_id = cluster.bk_biz_id
            bk_instance_ids = [*storage_instance_ids, *proxy_instance_ids]
            db_app_abbr = AppCache.get_app_attr(bk_biz_id=bk_biz_id)

            if not db_app_abbr:
                self.log_error(
                    _("未获取到业务 {} 的 db_app_abbr，cluster_id={}, domain={}").format(
                        bk_biz_id, cluster_id, cluster.immute_domain
                    )
                )
                return False

            self.log_info(_("获取业务属性成功: db_app_abbr={}").format(db_app_abbr))

            # 插入标签，CC 接口限制 100 个一批
            total_instances = len(bk_instance_ids)
            self.log_info(_("开始批量更新 CC 标签，共 {} 个实例，分 {} 批处理").format(total_instances, (total_instances // 100 + 1)))

            for page in range(len(bk_instance_ids) // 100 + 1):
                instance_ids = bk_instance_ids[page * 100 : (page + 1) * 100]
                if instance_ids:
                    self.log_info(_("正在处理第 {} 批实例，数量: {}").format(page + 1, len(instance_ids)))
                    CCApi.add_label_for_service_instance(
                        {
                            "bk_biz_id": bk_biz_id,
                            "instance_ids": instance_ids,
                            "labels": {"app": db_app_abbr, "app_name": db_app_abbr, "appid": str(bk_biz_id)},
                        }
                    )
                    self.log_info(_("第 {} 批实例标签更新完成").format(page + 1))

            # 更新主机属性
            storage_machine_ids = list(cluster.storageinstance_set.values_list("machine", flat=True))
            proxy_machine_ids = list(cluster.proxyinstance_set.values_list("machine", flat=True))
            bk_host_ids = [*storage_machine_ids, *proxy_machine_ids]
            self.log_info(_("开始更新主机属性，共 {} 台主机").format(len(bk_host_ids)))

            CcManage(bk_biz_id, cluster.cluster_type).update_host_properties(
                bk_host_ids=bk_host_ids, need_monitor=True
            )
            self.log_info(_("主机属性更新完成"))

            self.log_info(
                _(
                    "更新 CC 数据成功: cluster_id={}, domain={}, cluster_type={}, bk_biz_id={}, "
                    "storage_instances={}, proxy_instances={}, hosts={}"
                ).format(
                    cluster_id,
                    cluster.immute_domain,
                    cluster.cluster_type,
                    bk_biz_id,
                    len(storage_instance_ids),
                    len(proxy_instance_ids),
                    len(bk_host_ids),
                )
            )
            return True
        except Exception as e:
            self.log_error(_("更新 CC 数据失败: cluster_id={}, 错误信息: {}").format(cluster_id, str(e)))
            return False


class RedisUpdateCCComponent(Component):
    name = __name__
    code = "redis_update_cc"
    bound_service = RedisUpdateCCService


class RedisUpdateConfigCenterService(BaseService):
    """更新配置中心 Service"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_id = kwargs["cluster"]["cluster_id"]
        source_bk_biz_id = kwargs["cluster"]["source_bk_biz_id"]
        target_bk_biz_id = kwargs["cluster"]["target_bk_biz_id"]

        self.log_info(
            _("开始更新配置中心: cluster_id={}, 源业务ID={}, 目标业务ID={}").format(cluster_id, source_bk_biz_id, target_bk_biz_id)
        )

        try:
            cluster = Cluster.objects.get(id=cluster_id)
            self.log_info(
                _("获取集群信息成功: domain={}, cluster_type={}").format(cluster.immute_domain, cluster.cluster_type)
            )

            self.log_info(_("开始调用配置中心接口更新业务ID"))
            DBConfigApi.change_bk_biz_id(
                params={
                    "bk_biz_id": str(source_bk_biz_id),
                    "new_bk_biz_id": str(target_bk_biz_id),
                    "cluster_domains": [cluster.immute_domain],
                }
            )
            self.log_info(_("配置中心接口调用成功"))

            self.log_info(
                _("更新配置中心成功: cluster_id={}, domain={}, cluster_type={}, {} -> {}").format(
                    cluster_id,
                    cluster.immute_domain,
                    cluster.cluster_type,
                    source_bk_biz_id,
                    target_bk_biz_id,
                )
            )
            return True
        except Exception as e:
            self.log_error(
                _("更新配置中心失败: cluster_id={}, domain={}, 错误信息: {}").format(
                    cluster_id, cluster.immute_domain if "cluster" in locals() else "unknown", str(e)
                )
            )
            return False


class RedisUpdateConfigCenterComponent(Component):
    name = __name__
    code = "redis_update_config_center"
    bound_service = RedisUpdateConfigCenterService


class RedisUpdateDNSService(BaseService):
    """更新 DNS 所属业务 Service"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_id = kwargs["cluster"]["cluster_id"]
        source_bk_biz_id = kwargs["cluster"]["source_bk_biz_id"]
        target_bk_biz_id = kwargs["cluster"]["target_bk_biz_id"]

        self.log_info(
            _("开始更新 DNS 业务归属: cluster_id={}, 源业务ID={}, 目标业务ID={}").format(
                cluster_id, source_bk_biz_id, target_bk_biz_id
            )
        )

        try:
            cluster = Cluster.objects.get(id=cluster_id)
            self.log_info(
                _("获取集群信息成功: domain={}, cluster_type={}").format(cluster.immute_domain, cluster.cluster_type)
            )

            # 从 ClusterEntry 表查出该集群所有 DNS 类型的域名（含主域名、从域名等所有关联域名）
            dns_entries = ClusterEntry.objects.filter(
                cluster=cluster,
                cluster_entry_type__in=[ClusterEntryType.DNS.value, ClusterEntryType.CLBDNS.value],
            ).values_list("entry", flat=True)
            domains = list(dns_entries)

            if not domains:
                self.log_warning(
                    _("集群 {} (domain={}) 未找到任何 DNS 类型的 ClusterEntry，跳过 DNS 更新").format(
                        cluster_id, cluster.immute_domain
                    )
                )
                return True  # 没有DNS记录不算错误，正常返回

            self.log_info(
                _("集群 {} (domain={}) 共找到 {} 条 DNS 域名: {}").format(
                    cluster_id, cluster.immute_domain, len(domains), ", ".join(domains)
                )
            )

            success_count = 0
            fail_count = 0

            for domain_name in domains:
                try:
                    self.log_info(_("开始更新域名 {} 的业务归属").format(domain_name))
                    ret = DnsApi.update_domain_belong_app(
                        {
                            "app": str(source_bk_biz_id),
                            "new_app": str(target_bk_biz_id),
                            "bk_cloud_id": cluster.bk_cloud_id,
                            "domain_name": domain_name,
                        }
                    )
                    self.log_info(
                        _("更新 DNS 成功: cluster_id={}, domain={}, cluster_type={}, {} -> {}, 返回结果: {}").format(
                            cluster_id,
                            cluster.immute_domain,
                            cluster.cluster_type,
                            source_bk_biz_id,
                            target_bk_biz_id,
                            ret,
                        )
                    )
                    success_count += 1
                except Exception as e:  # pylint: disable=broad-except
                    self.log_error(
                        _("更新 DNS 记录异常: cluster_id={}, domain={}, {} -> {}, 错误信息: {}").format(
                            cluster_id, domain_name, source_bk_biz_id, target_bk_biz_id, e
                        )
                    )
                    fail_count += 1

            if fail_count > 0:
                self.log_error(_("DNS 更新完成但有失败记录: 成功 {} 条, 失败 {} 条").format(success_count, fail_count))
                return False
            else:
                self.log_info(_("DNS 更新全部成功: 共更新 {} 条域名记录").format(success_count))
                return True

        except Exception as e:
            self.log_error(_("更新 DNS 业务归属失败: cluster_id={}, 错误信息: {}").format(cluster_id, str(e)))
            return False


class RedisUpdateDNSComponent(Component):
    name = __name__
    code = "redis_update_dns"
    bound_service = RedisUpdateDNSService


class RedisChangeBizFlow(object):
    """
    Redis 转 业务
           {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"vitox",
        "ticket_type":"REDIS_CHANGE_BIZ",
        "infos": [
                {
                "cluster_ids":[1,2,3,5,6],
                "target_bk_biz_id": 123456,
                "source_bk_biz_id": 123456
                }
            ]
        }
    """

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data

    def run_redis_change_biz_flow(self):
        """
        遍历 infos，按集群类型拆分后将单实例和集群类型的 sub_pipeline 合并到同一批并行执行。
        支持混合架构输入：单实例类型和集群类型放在同一个 add_parallel_sub_pipeline 中并行处理。
        """
        logger.info(_("开始执行 Redis 变更业务流程，root_id={}").format(self.root_id))

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        all_sub_pipelines = []

        infos = self.data.get("infos", [])
        logger.info(_("共收到 {} 个变更信息组").format(len(infos)))

        for info_idx, info in enumerate(infos):
            cluster_ids = info.get("cluster_ids", [])
            if not cluster_ids:
                logger.error(_("第 {} 个变更信息组中 cluster_ids 为空").format(info_idx + 1))
                raise ValueError(_("cluster_ids 不能为空"))

            source_bk_biz_id = info.get("source_bk_biz_id")
            target_bk_biz_id = info.get("target_bk_biz_id")

            logger.info(
                _("处理第 {} 个变更信息组: 集群数量={}, 源业务ID={}, 目标业务ID={}").format(
                    info_idx + 1, len(cluster_ids), source_bk_biz_id, target_bk_biz_id
                )
            )

            # 按集群类型拆分：主从实例类型 vs 集群类型（支持混合架构输入）
            instance_cluster_ids = []
            normal_cluster_ids = []
            for cluster_id in cluster_ids:
                cluster = Cluster.objects.get(id=cluster_id)
                if cluster.cluster_type in REDIS_INSTANCE_CLUSTER_TYPES:
                    instance_cluster_ids.append(cluster_id)
                else:
                    normal_cluster_ids.append(cluster_id)

            logger.info(_("集群类型统计: 单实例类型 {} 个, 集群类型 {} 个").format(len(instance_cluster_ids), len(normal_cluster_ids)))

            # 单实例类型：先做单机多实例完整性检查，再构建 sub_pipeline
            if instance_cluster_ids:
                logger.info(_("开始构建单实例类型子流程，共 {} 个集群").format(len(instance_cluster_ids)))
                all_sub_pipelines.extend(
                    self._build_instance_sub_pipelines(instance_cluster_ids, source_bk_biz_id, target_bk_biz_id)
                )
            # 集群类型：直接构建 sub_pipeline
            if normal_cluster_ids:
                logger.info(_("开始构建集群类型子流程，共 {} 个集群").format(len(normal_cluster_ids)))
                all_sub_pipelines.extend(
                    self._build_cluster_sub_pipelines(normal_cluster_ids, source_bk_biz_id, target_bk_biz_id)
                )

        if not all_sub_pipelines:
            logger.error(_("没有可执行的集群，请检查输入"))
            raise ValueError(_("没有可执行的集群，请检查输入"))

        logger.info(_("所有子流程构建完成，共 {} 个子流程").format(len(all_sub_pipelines)))
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=all_sub_pipelines)
        logger.info(_("开始执行 Redis 变更业务流程"))
        redis_pipeline.run_pipeline()
        logger.info(_("Redis 变更业务流程执行完成"))

    def _build_single_cluster_sub_pipeline(self, cluster_id, source_bk_biz_id, target_bk_biz_id, sub_name):
        """
        构建单个集群变更业务的 sub_pipeline（Step1~5 公共逻辑），并返回 (sub_process, act_kwargs)。
        **优化后的步骤顺序（健壮性提升）:**
        Step1: 修改 DNS 域名所属业务（外部API，可能失败）
        Step2: 修改主机CC标签（外部API，可能失败）
        Step3: 修改配置中心（外部API，可能失败）
        Step4: 修改 DBM 元数据（本地数据库操作，基本不会失败）
        Step5: 重新标准化集群（依赖DBM元数据更新完成）
        """
        logger.info(_("开始构建单个集群子流程: cluster_id={}, 子流程名称={}").format(cluster_id, sub_name))

        cluster = Cluster.objects.get(id=cluster_id)
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = cluster.bk_cloud_id

        base_cluster_info = {
            "cluster_id": cluster_id,
            "source_bk_biz_id": source_bk_biz_id,
            "target_bk_biz_id": target_bk_biz_id,
        }

        logger.info(_("开始添加第1步: 更新DNS域名业务（外部API，可能失败）"))
        # Step1: 修改 DNS 域名所属业务（外部API，可能失败）
        act_kwargs.cluster = dict(base_cluster_info)
        sub_pipeline.add_act(
            act_name=_("更新DNS域名业务"),
            act_component_code=RedisUpdateDNSComponent.code,
            kwargs=asdict(act_kwargs),
        )

        logger.info(_("开始添加第2步: 更新主机CC标签（外部API，可能失败）"))
        # Step2: 更新主机CC标签（外部API，可能失败）
        act_kwargs.cluster = dict(base_cluster_info)
        sub_pipeline.add_act(
            act_name=_("更新主机CC标签"),
            act_component_code=RedisUpdateCCComponent.code,
            kwargs=asdict(act_kwargs),
        )

        logger.info(_("开始添加第3步: 更新配置中心（外部API，可能失败）"))
        # Step3: 修改配置中心（外部API，可能失败）
        act_kwargs.cluster = dict(base_cluster_info)
        sub_pipeline.add_act(
            act_name=_("更新配置中心"),
            act_component_code=RedisUpdateConfigCenterComponent.code,
            kwargs=asdict(act_kwargs),
        )

        logger.info(_("开始添加第4步: 更新DBM元数据（本地数据库操作，基本不会失败）"))
        # Step4: 修改 DBM 元数据（本地数据库操作，基本不会失败）
        act_kwargs.cluster = dict(base_cluster_info)
        sub_pipeline.add_act(
            act_name=_("更新DBM元数据"),
            act_component_code=RedisUpdateDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )

        logger.info(_("开始添加第5步: 更新服务实例（依赖DBM元数据更新完成）"))
        # Step5: 更新服务实例（依赖DBM元数据更新完成）
        act_kwargs.cluster = {
            "meta_func_name": RedisDBMeta.re_standardize_cluster.__name__,
            "get_kwargs_func": RedisDBMeta.re_standardize_cluster.__name__,
            "cluster_id": cluster_id,
        }
        sub_pipeline.add_act(
            act_name=_("更新服务实例"),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )

        logger.info(_("单个集群子流程构建完成: cluster_id={}, 共5个步骤").format(cluster_id))
        return sub_pipeline.build_sub_process(sub_name=sub_name), act_kwargs

    def _build_cluster_sub_pipelines(self, cluster_ids, source_bk_biz_id, target_bk_biz_id):
        """
        构建集群版变更业务的 sub_pipeline 列表。
        Step1~5 复用公共逻辑，Step6 用 ClusterDbmonInstallAtomJob 按集群维度重装 dbmon。
        """
        logger.info(_("开始构建集群类型子流程，集群数量: {}").format(len(cluster_ids)))
        sub_pipelines = []

        for cluster_idx, cluster_id in enumerate(cluster_ids):
            cluster = Cluster.objects.get(id=cluster_id)
            logger.info(
                _("构建第 {} 个集群子流程: cluster_id={}, domain={}").format(cluster_idx + 1, cluster_id, cluster.immute_domain)
            )

            sub_name = _("变更业务-{}").format(cluster.immute_domain)
            cluster_change_sub_process, act_kwargs = self._build_single_cluster_sub_pipeline(
                cluster_id, source_bk_biz_id, target_bk_biz_id, sub_name
            )

            # 外层包一层子流程，保证 dbmon 串行跟在集群变更子流程之后执行
            cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            cluster_sub_pipeline.add_sub_pipeline(cluster_change_sub_process)

            # Step6: 重装 dbmon（集群版：一台机器只属于一个集群，按集群维度重装即可）
            logger.info(_("集群 {} 开始构建 dbmon 重装任务").format(cluster.immute_domain))
            passwd_ret = PayloadHandler.redis_get_password_by_domain(cluster.immute_domain)
            dbmon_params = {
                "cluster_domain": cluster.immute_domain,
                "redis_password": passwd_ret.get("redis_password", "NO_REDIS_PAS_CONFIED"),
                "proxy_password": passwd_ret.get("redis_proxy_password", "NO_PROXY_PAS_CONFIED"),
                "is_stop": False,
                "restart_exporter": True,
            }
            cluster_sub_pipeline.add_sub_pipeline(
                ClusterDbmonInstallAtomJob(self.root_id, self.data, act_kwargs, dbmon_params)
            )

            sub_pipelines.append(cluster_sub_pipeline.build_sub_process(sub_name=sub_name))

        logger.info(_("集群类型子流程构建完成，共 {} 个子流程").format(len(sub_pipelines)))
        return sub_pipelines

    def _build_instance_sub_pipelines(self, cluster_ids, source_bk_biz_id, target_bk_biz_id):
        """
        构建主从实例版变更业务的 sub_pipeline 列表。
        单机多实例场景：同一台机器上的所有实例必须全部转移，否则拒绝执行。
        """
        logger.info(_("开始构建单实例类型子流程，集群数量: {}").format(len(cluster_ids)))

        # 收集涉及的机器 IP，并做单机多实例完整性检查
        machine_cluster_map = {}
        logger.info(_("开始收集机器信息并进行完整性检查"))

        # 使用事务保护完整性检查，确保检查期间数据不被修改
        with transaction.atomic():
            for cluster_id in cluster_ids:
                # 使用select_for_update锁定集群记录，防止并发修改
                cluster = Cluster.objects.select_for_update().get(id=cluster_id, bk_biz_id=source_bk_biz_id)
                for storage in cluster.storageinstance_set.all():
                    ip = storage.machine.ip
                    machine_cluster_map.setdefault(ip, set()).add(cluster_id)

        logger.info(_("共涉及 {} 台机器").format(len(machine_cluster_map)))

        # 检查每台机器上的所有集群是否都在本次转移列表中
        transfer_set = set(cluster_ids)
        logger.info(_("开始单机多实例完整性检查"))

        # 再次使用事务保护，确保检查的一致性
        with transaction.atomic():
            for ip, transfer_clusters in machine_cluster_map.items():
                # 使用select_for_update锁定相关记录
                all_clusters = set(
                    Cluster.objects.select_for_update()
                    .filter(storageinstance__machine__ip=ip, bk_biz_id=source_bk_biz_id)
                    .values_list("id", flat=True)
                )
                missing = all_clusters - transfer_set
                if missing:
                    logger.error(_("机器 {} 上存在未转移的实例，所属集群ID: {}").format(ip, ",".join(str(i) for i in missing)))
                    raise ValueError(
                        _("机器 {} 上存在未转移的实例，所属集群ID: {}，单机多实例场景必须全部转移").format(ip, ",".join(str(i) for i in missing))
                    )

        logger.info(_("单机多实例完整性检查通过"))

        # Step1~5：每个 cluster 各自构建 sub_pipeline（复用公共逻辑，不含 dbmon 重装）
        sub_pipelines = []

        for cluster_idx, cluster_id in enumerate(cluster_ids):
            cluster = Cluster.objects.get(id=cluster_id)
            logger.info(
                _("构建第 {} 个单实例集群子流程: cluster_id={}, domain={}").format(
                    cluster_idx + 1, cluster_id, cluster.immute_domain
                )
            )

            sub_name = _("Redis单实例变更业务-{}").format(cluster.immute_domain)
            sub_process, act_kwargs = self._build_single_cluster_sub_pipeline(
                cluster_id, source_bk_biz_id, target_bk_biz_id, sub_name
            )

            # 如果是最后一个集群，将dbmon重装任务添加到该子流程中
            if cluster_idx == len(cluster_ids) - 1:
                clusters = [Cluster.objects.get(id=cid) for cid in cluster_ids]
                if clusters:
                    logger.info(_("开始构建 dbmon 重装任务，涉及 {} 个集群，统一处理机器上的所有实例").format(len(clusters)))
                    sub_process.add_parallel_sub_pipeline(
                        sub_flow_list=[
                            SingleClusterDbmonInstallAtomJob(
                                self.root_id,
                                self.data,
                                act_kwargs,
                                clusters,
                                {"is_stop": False},
                            )
                        ]
                    )

            sub_pipelines.append(sub_process)

        logger.info(_("单实例类型子流程构建完成，共 {} 个子流程").format(len(sub_pipelines)))
        return sub_pipelines
