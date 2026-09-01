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
import re

from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_monitor.constants import TargetLevel
from backend.db_monitor.models import MonitorPolicy
from backend.exceptions import ApiRequestError


def match_target_value(method, value, query_value):
    """
    普通类型监控目标的匹配规则: eq, neq, include, exclude, reg, nreg
    include代表包含, exclude代表不包含, value是目标值列表
    """
    if method == "eq":
        return query_value in value
    if method == "neq":
        return query_value not in value
    if method == "include":
        return any(v in query_value for v in value)
    if method == "exclude":
        return all(v not in query_value for v in value)
    if method == "reg":
        return any(re.search(v, query_value) for v in value)
    if method == "nreg":
        return all(not re.search(v, query_value) for v in value)
    return False


def match_promql_target(method, value, domain):
    """
    promql类型监控目标的匹配规则: =, !=, =~, !~
    value是值列表, 正则匹配(=~ / !~)时value是正则规则列表
    """
    if method == "=":
        return domain in value
    if method == "!=":
        return domain not in value
    if method == "=~":
        return any(re.search(v, domain) for v in value)
    if method == "!~":
        return all(not re.search(v, domain) for v in value)
    return False


def is_alert_level_matched(policy, alert_level):
    """如果指定了告警级别, 则看当前策略的test_rules有没有设定该级别"""
    if not alert_level:
        return True
    # test_rules存的都是列表
    return any(rule.get("level") == alert_level for rule in policy.test_rules or [])


def _iter_target_rules(targets):
    """遍历 targets, 产出每条 target 的 (key, method, value), 跳过没有 rule 的 target"""
    for target in targets:
        rule = target.get("rule")
        if not rule:
            continue
        yield rule["key"], rule["method"], rule["value"]


def _match_cluster_domain(targets, policy, alert_level, cluster_id_domain_map, target_policy, matcher):
    """按集群域名维度匹配 targets 中的 cluster_domain 规则, 命中则回填 target_policy 并移除该集群"""
    for key, method, value in _iter_target_rules(targets):
        if key != "cluster_domain":
            continue
        for cluster_id, domain in list(cluster_id_domain_map.items()):
            if matcher(method, value, domain) and is_alert_level_matched(policy, alert_level):
                target_policy[cluster_id] = policy
                cluster_id_domain_map.pop(cluster_id)


def _match_all_clusters(policy, alert_level, cluster_id_domain_map, target_policy):
    """策略命中所有剩余集群(业务/父级策略或无集群维度时), 回填并移除"""
    if not is_alert_level_matched(policy, alert_level):
        return
    for cluster_id in list(cluster_id_domain_map):
        target_policy[cluster_id] = policy
        cluster_id_domain_map.pop(cluster_id)


def _match_dimensions(targets, dimension_param_map):
    """
    按 topic/消费组维度匹配, 返回 (是否匹配, 集群域名规则值)
    value为空代表匹配全部; 未传该维度参数时不参与过滤
    """
    dimension_matched = True
    cluster_domain_value = None
    for key, method, value in _iter_target_rules(targets):
        if key == "cluster_domain":
            cluster_domain_value = value
            continue
        # 只关心 topic / 消费组维度
        if key not in dimension_param_map or not value:
            continue
        param_value = dimension_param_map[key]
        # 查询未传该维度参数时, 该维度不参与过滤; 传了但不满足规则才不匹配
        if not param_value:
            continue
        if not match_target_value(method, value, param_value):
            dimension_matched = False
    return dimension_matched, cluster_domain_value


def classify_policy(policies):
    parent_policy, biz_policy, sub_policy = [], [], []
    for policy in policies:
        if not policy.parent_id:
            parent_policy.append(policy)
        elif policy.target_level == TargetLevel.APP.value:
            biz_policy.append(policy)
        else:
            sub_policy.append(policy)
    return parent_policy, biz_policy, sub_policy


def get_policy_threshold(
    db_type, policy_code, bk_biz_id, cluster_id="", consumergroup=None, topic=None, alert_level=None
):
    if not cluster_id:
        raise ApiRequestError(_("缺少集群id"))
    cluster_ids = [int(cluster_id) for cluster_id in cluster_id.split(",") if cluster_id]
    all_policy = MonitorPolicy.objects.filter(
        db_type=db_type, policy_code=policy_code, bk_biz_id__in=[0, bk_biz_id], is_enabled=True
    ).order_by("-create_at")
    if not all_policy:
        return None

    parent_policy, biz_policy, sub_policy = classify_policy(all_policy)
    target_policy = {}
    clusters = Cluster.objects.filter(id__in=cluster_ids, bk_biz_id=bk_biz_id)
    if not clusters:
        return None
    db_types = set([ClusterType.cluster_type_to_db_type(cluster.cluster_type) for cluster in clusters])
    if len(db_types) != 1:
        return None
    if db_types.pop() != db_type:
        return None
    cluster_id_domain_map = {cluster.id: cluster.immute_domain for cluster in clusters}

    for policy in sub_policy:
        targets = policy.targets
        # promql类型监控目标只有集群维度, 匹配规则有 =, !=, =~, !~
        if policy.agg_info and policy.agg_info[0].get("promql"):
            if not cluster_id_domain_map:
                break
            _match_cluster_domain(
                targets, policy, alert_level, cluster_id_domain_map, target_policy, match_promql_target
            )

        # 普通类型, 匹配规则有 eq, neq, include, exclude, reg, nreg; include代表包含, exclude代表不包含
        elif topic or consumergroup:
            dimension_param_map = {"topic": topic, "consumergroup": consumergroup}
            dimension_matched, cluster_domain_value = _match_dimensions(targets, dimension_param_map)
            if not dimension_matched:
                continue
            # 策略的集群维度没填写则代表所有集群都匹配
            if cluster_domain_value:
                _match_cluster_domain(
                    targets, policy, alert_level, cluster_id_domain_map, target_policy, match_target_value
                )
            else:
                _match_all_clusters(policy, alert_level, cluster_id_domain_map, target_policy)
        else:
            _match_cluster_domain(
                targets, policy, alert_level, cluster_id_domain_map, target_policy, match_target_value
            )

    # 子策略没匹配完匹配业务策略, 业务策略匹配不上匹配全局父策略
    if cluster_id_domain_map:
        for policy in biz_policy:
            _match_all_clusters(policy, alert_level, cluster_id_domain_map, target_policy)

    if cluster_id_domain_map:
        for policy in parent_policy:
            _match_all_clusters(policy, alert_level, cluster_id_domain_map, target_policy)

    if not target_policy:
        return None

    result = {}
    for cluster_id, matched_policy in target_policy.items():
        if alert_level:
            result[cluster_id] = [rule for rule in matched_policy.test_rules if rule.get("level") == alert_level]
        else:
            result[cluster_id] = matched_policy.test_rules
    return result
