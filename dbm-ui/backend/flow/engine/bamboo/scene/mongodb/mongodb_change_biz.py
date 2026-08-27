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

from django.db import transaction
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DBConfigApi
from backend.components.cc.client import CCApi
from backend.components.dns.client import DnsApi
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import AppCache, Cluster, ClusterEntry, Machine
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import add_install_dbmon
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mongodb.migrate_meta import MongoDBMigrateMetaComponent
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.mongodb.migrate_meta import MongoDBMigrateMeta
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository

logger = logging.getLogger("flow")


class MongoDBUpdateDBMetaService(BaseService):
    """更新 MongoDB DB 元数据 Service"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_id = kwargs["cluster_id"]
        target_bk_biz_id = kwargs["target_bk_biz_id"]
        source_bk_biz_id = kwargs["source_bk_biz_id"]

        self.log_info(
            _("开始更新 DB 元数据: cluster_id={}, 源业务ID={}, 目标业务ID={}").format(cluster_id, source_bk_biz_id, target_bk_biz_id)
        )

        try:
            with transaction.atomic():
                cluster = Cluster.objects.select_for_update().get(id=cluster_id, bk_biz_id=source_bk_biz_id)
                self.log_info(
                    _("获取集群信息成功: domain={}, cluster_type={}").format(cluster.immute_domain, cluster.cluster_type)
                )

                # 更新存储实例业务ID
                storage_count = cluster.storageinstance_set.all().update(bk_biz_id=target_bk_biz_id)
                self.log_info(_("更新存储实例业务ID完成: 共更新 {} 个存储实例").format(storage_count))

                # 更新代理实例业务ID（分片集群有 mongos）
                proxy_count = cluster.proxyinstance_set.all().update(bk_biz_id=target_bk_biz_id)
                self.log_info(_("更新代理实例业务ID完成: 共更新 {} 个代理实例").format(proxy_count))

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


class MongoDBUpdateDBMetaComponent(Component):
    name = __name__
    code = "mongodb_update_db_meta"
    bound_service = MongoDBUpdateDBMetaService


class MongoDBUpdateCCService(BaseService):
    """更新 CC 标签和主机属性 Service"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_id = kwargs["cluster_id"]

        self.log_info(_("开始更新 CC 数据: cluster_id={}").format(cluster_id))

        try:
            cluster = Cluster.objects.get(id=cluster_id)
            self.log_info(
                _("获取集群信息成功: domain={}, cluster_type={}").format(cluster.immute_domain, cluster.cluster_type)
            )

            # 获取存储实例和代理实例的 bk_instance_id
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

            # 批量更新 CC 标签，CC 接口限制 100 个一批
            total_instances = len(bk_instance_ids)
            self.log_info(_("开始批量更新 CC 标签，共 {} 个实例，分 {} 批处理").format(total_instances, (total_instances // 100 + 1)))
            for page in range(total_instances // 100 + 1):
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
                _("更新 CC 数据成功: cluster_id={}, domain={}, bk_biz_id={}, hosts={}").format(
                    cluster_id, cluster.immute_domain, bk_biz_id, len(bk_host_ids)
                )
            )
            return True
        except Exception as e:
            self.log_error(_("更新 CC 数据失败: cluster_id={}, 错误信息: {}").format(cluster_id, str(e)))
            return False


class MongoDBUpdateCCComponent(Component):
    name = __name__
    code = "mongodb_update_cc"
    bound_service = MongoDBUpdateCCService


class MongoDBUpdateConfigCenterService(BaseService):
    """更新配置中心 Service"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_id = kwargs["cluster_id"]
        source_bk_biz_id = kwargs["source_bk_biz_id"]
        target_bk_biz_id = kwargs["target_bk_biz_id"]

        self.log_info(
            _("开始更新配置中心: cluster_id={}, 源业务ID={}, 目标业务ID={}").format(cluster_id, source_bk_biz_id, target_bk_biz_id)
        )

        try:
            cluster = Cluster.objects.get(id=cluster_id)
            self.log_info(
                _("获取集群信息成功: domain={}, cluster_type={}").format(cluster.immute_domain, cluster.cluster_type)
            )

            DBConfigApi.change_bk_biz_id(
                params={
                    "bk_biz_id": str(source_bk_biz_id),
                    "new_bk_biz_id": str(target_bk_biz_id),
                    "cluster_domains": [cluster.immute_domain],
                }
            )
            self.log_info(
                _("更新配置中心成功: cluster_id={}, domain={}, {} -> {}").format(
                    cluster_id, cluster.immute_domain, source_bk_biz_id, target_bk_biz_id
                )
            )
            return True
        except Exception as e:
            self.log_error(_("更新配置中心失败: cluster_id={}, 错误信息: {}").format(cluster_id, str(e)))
            return False


class MongoDBUpdateConfigCenterComponent(Component):
    name = __name__
    code = "mongodb_update_config_center"
    bound_service = MongoDBUpdateConfigCenterService


class MongoDBUpdateDNSService(BaseService):
    """更新 DNS 所属业务 Service"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_id = kwargs["cluster_id"]
        source_bk_biz_id = kwargs["source_bk_biz_id"]
        target_bk_biz_id = kwargs["target_bk_biz_id"]

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

            # 从 ClusterEntry 表查出该集群所有 DNS 类型的域名
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
                return True

            self.log_info(_("集群 {} 共找到 {} 条 DNS 域名: {}").format(cluster_id, len(domains), ", ".join(domains)))

            success_count = 0
            fail_count = 0
            for domain_name in domains:
                # MongoDB 域名需要以 "." 结尾
                domain_name_with_dot = domain_name if domain_name.endswith(".") else "{}.".format(domain_name)
                try:
                    self.log_info(_("开始更新域名 {} 的业务归属").format(domain_name_with_dot))
                    ret = DnsApi.update_domain_belong_app(
                        {
                            "app": str(source_bk_biz_id),
                            "new_app": str(target_bk_biz_id),
                            "bk_cloud_id": cluster.bk_cloud_id,
                            "domain_name": domain_name_with_dot,
                        }
                    )
                    self.log_info(
                        _("更新 DNS 成功: domain={}, {} -> {}, 返回结果: {}").format(
                            domain_name_with_dot, source_bk_biz_id, target_bk_biz_id, ret
                        )
                    )
                    success_count += 1
                except Exception as e:  # pylint: disable=broad-except
                    self.log_error(
                        _("更新 DNS 记录异常: domain={}, {} -> {}, 错误信息: {}").format(
                            domain_name_with_dot, source_bk_biz_id, target_bk_biz_id, e
                        )
                    )
                    fail_count += 1

            if fail_count > 0:
                self.log_error(_("DNS 更新完成但有失败记录: 成功 {} 条, 失败 {} 条").format(success_count, fail_count))
                return False

            self.log_info(_("DNS 更新全部成功: 共更新 {} 条域名记录").format(success_count))
            return True

        except Exception as e:
            self.log_error(_("更新 DNS 业务归属失败: cluster_id={}, 错误信息: {}").format(cluster_id, str(e)))
            return False


class MongoDBUpdateDNSComponent(Component):
    name = __name__
    code = "mongodb_update_dns"
    bound_service = MongoDBUpdateDNSService


class MongoDBChangeBizFlow(object):
    """
    MongoDB 转移业务流程

    入参示例:
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by": "admin",
        "ticket_type": "MONGODB_CHANGE_BIZ",
        "infos": [
            {
                "cluster_ids": [1, 2, 3],
                "source_bk_biz_id": 100,
                "target_bk_biz_id": 200
            }
        ]
    }

    流程步骤（每个集群独立子流程，并行执行）:
    Step1: 更新 DNS 域名所属业务
    Step2: 更新主机 CC 标签
    Step3: 更新配置中心
    Step4: 更新 DBM 元数据（Cluster / StorageInstance / ProxyInstance / Machine）
    Step5: 重新挪 CC 模块（gse_reload）
    Step6: 重装 dbmon
    """

    def __init__(self, root_id: str, data: dict):
        self.root_id = root_id
        self.data = data

    def run_flow(self):
        """
        遍历 infos，按集群类型（副本集 / 分片集群）分别构建子流程，并行执行。
        """
        logger.info(_("开始执行 MongoDB 变更业务流程，root_id={}").format(self.root_id))

        pipeline = Builder(root_id=self.root_id, data=self.data)
        all_sub_pipelines = []

        infos = self.data.get("infos", [])
        logger.info(_("共收到 {} 个变更信息组").format(len(infos)))

        for info_idx, info in enumerate(infos):
            cluster_ids = info.get("cluster_ids", [])
            if not cluster_ids:
                raise ValueError(_("第 {} 个变更信息组中 cluster_ids 不能为空").format(info_idx + 1))

            source_bk_biz_id = info["source_bk_biz_id"]
            target_bk_biz_id = info["target_bk_biz_id"]

            logger.info(
                _("处理第 {} 个变更信息组: 集群数量={}, 源业务ID={}, 目标业务ID={}").format(
                    info_idx + 1, len(cluster_ids), source_bk_biz_id, target_bk_biz_id
                )
            )

            for cluster_id in cluster_ids:
                cluster = Cluster.objects.get(id=cluster_id)
                logger.info(
                    _("构建集群子流程: cluster_id={}, domain={}, cluster_type={}").format(
                        cluster_id, cluster.immute_domain, cluster.cluster_type
                    )
                )

                if cluster.cluster_type == ClusterType.MongoReplicaSet.value:
                    sub = self._build_replicaset_sub_pipeline(cluster, source_bk_biz_id, target_bk_biz_id)
                elif cluster.cluster_type == ClusterType.MongoShardedCluster.value:
                    sub = self._build_sharded_cluster_sub_pipeline(cluster, source_bk_biz_id, target_bk_biz_id)
                else:
                    raise ValueError(
                        _("不支持的集群类型: cluster_id={}, cluster_type={}").format(cluster_id, cluster.cluster_type)
                    )

                all_sub_pipelines.append(sub)

        if not all_sub_pipelines:
            raise ValueError(_("没有可执行的集群，请检查输入"))

        logger.info(_("所有子流程构建完成，共 {} 个子流程，开始并行执行").format(len(all_sub_pipelines)))
        pipeline.add_parallel_sub_pipeline(sub_flow_list=all_sub_pipelines)
        pipeline.run_pipeline()
        logger.info(_("MongoDB 变更业务流程执行完成"))

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _build_common_steps(
        self, sub_pipeline: SubBuilder, cluster: Cluster, source_bk_biz_id: int, target_bk_biz_id: int
    ):
        """
        构建公共的 Step1~Step4，供副本集和分片集群复用。
        Step1: 更新 DNS 域名所属业务
        Step2: 更新主机 CC 标签
        Step3: 更新配置中心
        Step4: 更新 DBM 元数据
        """
        base_kwargs = {
            "cluster_id": cluster.id,
            "source_bk_biz_id": source_bk_biz_id,
            "target_bk_biz_id": target_bk_biz_id,
        }

        # Step1: 更新 DNS
        sub_pipeline.add_act(
            act_name=_("更新DNS域名业务"),
            act_component_code=MongoDBUpdateDNSComponent.code,
            kwargs=dict(base_kwargs),
        )

        # Step2: 更新 CC 标签（注意：此时 DBM 元数据尚未更新，bk_biz_id 仍是旧值，
        #        CC 标签更新需要在 DBM 元数据更新后执行，因此调整到 Step4 之后）
        # Step3: 更新配置中心
        sub_pipeline.add_act(
            act_name=_("更新配置中心"),
            act_component_code=MongoDBUpdateConfigCenterComponent.code,
            kwargs=dict(base_kwargs),
        )

        # Step4: 更新 DBM 元数据（本地数据库操作）
        sub_pipeline.add_act(
            act_name=_("更新DBM元数据"),
            act_component_code=MongoDBUpdateDBMetaComponent.code,
            kwargs=dict(base_kwargs),
        )

        # Step5: 更新 CC 标签（依赖 DBM 元数据更新完成，此时 bk_biz_id 已是新值）
        sub_pipeline.add_act(
            act_name=_("更新主机CC标签"),
            act_component_code=MongoDBUpdateCCComponent.code,
            kwargs={"cluster_id": cluster.id},
        )

    def _build_replicaset_sub_pipeline(self, cluster: Cluster, source_bk_biz_id: int, target_bk_biz_id: int):
        """
        构建副本集集群变更业务子流程。
        副本集：同一组机器上可能有多个副本集实例（多实例部署），
        gse_reload 时需要串行挪模块（is_increment 参数）。
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        sub_name = _("MongoDB副本集变更业务-{}").format(cluster.immute_domain)

        logger.info(_("构建副本集子流程: cluster_id={}, domain={}").format(cluster.id, cluster.immute_domain))

        # Step1~5: 公共步骤
        self._build_common_steps(sub_pipeline, cluster, source_bk_biz_id, target_bk_biz_id)

        # Step6: gse_reload 挪 CC 模块（副本集串行处理，is_increment=False 表示首次）
        sub_pipeline.add_act(
            act_name=_("挪CC模块"),
            act_component_code=MongoDBMigrateMetaComponent.code,
            kwargs={
                "cluster_type": ClusterType.MongoReplicaSet.value,
                "cluster_id": 0,
                "cluster_id_set": [cluster.id],
                "meta_func_name": MongoDBMigrateMeta.gse_reload.__name__,
            },
        )

        # Step7: 重装 dbmon
        cluster_info = MongoRepository.fetch_one_cluster(id=cluster.id)
        if cluster_info:
            exec_ips = [node.ip for node in cluster_info.get_shards()[0].members]
            bk_cloud_id = cluster.bk_cloud_id
            add_install_dbmon(
                root_id=self.root_id,
                flow_data=self.data,
                pipeline=sub_pipeline,
                iplist=exec_ips,
                bk_cloud_id=bk_cloud_id,
                allow_empty_instance=True,
            )

        return sub_pipeline.build_sub_process(sub_name=sub_name)

    def _build_sharded_cluster_sub_pipeline(self, cluster: Cluster, source_bk_biz_id: int, target_bk_biz_id: int):
        """
        构建分片集群变更业务子流程。
        分片集群包含 mongos（代理）、configsvr、shardsvr 三类节点。
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        sub_name = _("MongoDB分片集群变更业务-{}").format(cluster.immute_domain)

        logger.info(_("构建分片集群子流程: cluster_id={}, domain={}").format(cluster.id, cluster.immute_domain))

        # Step1~5: 公共步骤
        self._build_common_steps(sub_pipeline, cluster, source_bk_biz_id, target_bk_biz_id)

        # Step6: gse_reload 挪 CC 模块（分片集群）
        sub_pipeline.add_act(
            act_name=_("挪CC模块"),
            act_component_code=MongoDBMigrateMetaComponent.code,
            kwargs={
                "cluster_type": ClusterType.MongoShardedCluster.value,
                "cluster_id": cluster.id,
                "cluster_id_set": [],
                "meta_func_name": MongoDBMigrateMeta.gse_reload.__name__,
            },
        )

        # Step7: 重装 dbmon（收集所有节点 IP）
        cluster_info = MongoRepository.fetch_one_cluster(id=cluster.id)
        if cluster_info:
            exec_ips = []
            # mongos
            for node in cluster_info.get_mongos():
                exec_ips.append(node.ip)
            # configsvr
            config_rs = cluster_info.get_config()
            if config_rs:
                for node in config_rs.members:
                    exec_ips.append(node.ip)
            # shardsvr
            host_set = set()
            for shard in cluster_info.get_shards():
                for node in shard.members:
                    if node.ip not in host_set:
                        host_set.add(node.ip)
                        exec_ips.append(node.ip)

            exec_ips = list(set(exec_ips))
            bk_cloud_id = cluster.bk_cloud_id
            add_install_dbmon(
                root_id=self.root_id,
                flow_data=self.data,
                pipeline=sub_pipeline,
                iplist=exec_ips,
                bk_cloud_id=bk_cloud_id,
                allow_empty_instance=True,
            )

        return sub_pipeline.build_sub_process(sub_name=sub_name)
