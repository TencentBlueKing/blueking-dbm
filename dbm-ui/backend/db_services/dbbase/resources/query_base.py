from django.db.models import Q

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryType


def build_q_for_domain_by_cluster(domains, role=None):
    # 基础查询条件
    base_query = Q(clusterentry__cluster_entry_type=ClusterEntryType.DNS.value)
    if role:
        base_query &= Q(clusterentry__role=role)

    # 单个域名模糊查询，多个域名精确查询
    if len(domains) == 1:
        query = Q(clusterentry__entry__icontains=domains[0].strip())
    else:
        # 使用strip确保去除前后空格
        domains = [domain.strip() for domain in domains if domain.strip()]
        query = Q(clusterentry__entry__in=domains)
    return base_query & query


def build_q_for_domain_by_instance(query_params):
    # 从查询参数中提取域
    domains = query_params.get("domain", "").split(",")

    # 基础查询条件
    base_query = Q(cluster__clusterentry__cluster_entry_type=ClusterEntryType.DNS.value)

    if len(domains) == 1:  # 单个域，执行模糊查询
        query = Q(cluster__clusterentry__entry__icontains=domains[0].strip())
    else:
        domains = [domain.strip() for domain in domains if domain.strip()]
        query = Q(cluster__clusterentry__entry__in=domains)

    return base_query & query


def build_q_for_instance_filter(params_data: dict) -> Q:
    instance_list = params_data.get("instance", "").split(",")
    # 初始化两个空的Q对象，稍后用于构造过滤条件
    q_ip = Q()
    q_ip_port = Q()
    # 对筛选条件进行区分ip,还是ip:port
    for instance in instance_list:
        if IP_PORT_DIVIDER in instance:
            ip, port = instance.split(IP_PORT_DIVIDER)
            q_ip_port |= Q(machine__ip=ip, port=port)
        else:
            q_ip |= Q(machine__ip=instance)

    # 合并两种过滤条件
    return q_ip | q_ip_port
