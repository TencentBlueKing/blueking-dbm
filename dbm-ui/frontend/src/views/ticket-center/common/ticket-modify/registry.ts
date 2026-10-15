/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import _ from 'lodash';

import { TicketTypes } from '@common/const';

import { t } from '@locales/index';

import { type DiffOptions, formatValue } from './utils';

type DomainList = { key: string }[] | undefined;
type HostList = { ip: string }[] | undefined;
type K8sComponentList =
  | { component_name: string; replicas: number; request_cpu: string; request_memory: string; storage?: string }[]
  | undefined;
type RedisInsInfoList =
  { backend_group?: { master: { ip: string } }; cluster_name: string; databases: number }[] | undefined;
type ReplicaSetList = { domain: string; name: string }[] | undefined;

/**
 * resource_spec 下各角色的公共对比口径：
 * spec_name / cpu / mem / qps / storage_spec / instance_num 由 SpecSelector 按 spec_id 带出，label_names 随 labels 带出，都不计入差异；
 * spec_id、labels 展示为同一角色下的名称
 * capacity 不在这里忽略：有的类型是规格带出，有的类型（TENDBCLUSTER）是用户填写，按类型登记
 */
export const RESOURCE_SPEC_DIFF: Required<Pick<DiffOptions, 'formatters' | 'ignorePaths'>> = {
  formatters: {
    'resource_spec.*.labels': (value, snapshot, path) =>
      formatValue(_.get(snapshot, path.replace(/labels$/, 'label_names')) || value),
    'resource_spec.*.spec_id': (value, snapshot, path) =>
      formatValue(_.get(snapshot, path.replace(/spec_id$/, 'spec_name')) || value),
  },
  ignorePaths: [
    'resource_spec.*.cpu',
    'resource_spec.*.instance_num',
    'resource_spec.*.label_names',
    'resource_spec.*.mem',
    'resource_spec.*.qps',
    'resource_spec.*.spec_name',
    'resource_spec.*.storage_spec',
  ],
};

/**
 * MySQL 单节点 / 主从部署共用 mysql/common/apply：
 * 地域、容灾以顶层 city_code / disaster_tolerance_level 为准；后端不保存顶层园区，园区按 resource_spec 下的
 * location_spec 计。随之带出的 city_name / affinity / location_spec.city、按集群数推算的 count、规格带出的 capacity、
 * 由 DB 模块配置带出的字符集都不计入差异
 */
const MYSQL_APPLY_DIFF: Required<Pick<DiffOptions, 'formatters' | 'ignorePaths' | 'labels'>> = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    apply_clb: (value) => (value ? 'CLB' : '--'),
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
    domains: (value) => formatValue((value as DomainList)?.map((item) => item.key)),
    'nodes.*': (value) => formatValue((value as HostList)?.map((item) => item.ip)),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'charset',
    'city_name',
    'resource_spec.*.affinity',
    'resource_spec.*.capacity',
    'resource_spec.*.count',
    'resource_spec.*.location_spec.city',
    // 主从部署的 proxy 与 backend_group 园区相同，只按 backend_group 计
    'resource_spec.proxy.location_spec',
  ],
  labels: {
    apply_clb: t('负载均衡'),
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_count: t('集群数量'),
    db_module_id: t('所属DB模块'),
    disaster_tolerance_level: t('容灾要求'),
    domains: t('域名设置'),
    'resource_spec.*.labels': t('资源标签'),
    'resource_spec.*.location_spec.include_or_exclude': t('园区'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.backend_group.spec_id': t('后端存储资源规格'),
    'resource_spec.backend.spec_id': t('后端存储资源规格'),
    'resource_spec.proxy.spec_id': t('Proxy 存储资源规格'),
    start_mysql_port: t('MySQL起始端口'),
    start_proxy_port: t('Proxy起始端口'),
  },
};

/**
 * SQLServer 单节点 / 主从部署共用 sqlserver/common/apply，口径同 MySQL：
 * 地域、容灾以顶层字段为准，园区按 resource_spec 下的 location_spec 计，顶层园区不重复计；随之带出的
 * city_name / affinity / location_spec.city、按集群数推算的 count、规格带出的 capacity 不计入差异。
 * 页面未开放手动录入主机，nodes 不参与对比
 */
const SQLSERVER_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
    domains: (value) => formatValue((value as DomainList)?.map((item) => item.key)),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'city_name',
    'nodes',
    'resource_spec.*.affinity',
    'resource_spec.*.capacity',
    'resource_spec.*.count',
    'resource_spec.*.location_spec.city',
    'sub_zone_ids',
    'sub_zone_names',
  ],
  labels: {
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_count: t('集群数量'),
    db_module_id: t('所属DB模块'),
    disaster_tolerance_level: t('容灾要求'),
    domains: t('域名设置'),
    inst_num: t('每组主机部署集群'),
    'resource_spec.*.labels': t('资源标签'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.*.spec_id': t('后端存储资源规格'),
    start_mssql_port: t('SQLServer 起始端口'),
  },
};

/**
 * TenDBCluster 集群部署：地域、容灾以顶层字段为准，园区按 backend_group 的 location_spec 计，spider 与之相同不重复计。
 * 随之带出的 city_name / affinity / location_spec.city、spider 规格带出的 capacity、部署方案明细 spec_info、
 * 按「组数 × 单机分片数」推算的集群分片数、由所属业务带出的业务代号不计入差异。
 * backend_group 的 capacity / future_capacity 是用户填写的容量需求，计入差异
 */
const TENDBCLUSTER_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    apply_clb: (value) => (value ? 'CLB' : '--'),
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
    // backend_group 同层没有 spec_name，规格名在部署方案明细 spec_info 里
    'resource_spec.backend_group.spec_id': (value, snapshot) =>
      formatValue(_.get(snapshot, 'resource_spec.backend_group.spec_info.spec_name') || value),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'city_name',
    'cluster_shard_num',
    'db_app_abbr',
    'resource_spec.*.affinity',
    'resource_spec.*.location_spec.city',
    'resource_spec.backend_group.spec_info',
    'resource_spec.spider.capacity',
    'resource_spec.spider.location_spec',
  ],
  labels: {
    apply_clb: t('负载均衡'),
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    db_module_id: t('DB参数模块'),
    disaster_tolerance_level: t('容灾级别'),
    remote_shard_num: t('单机分片数'),
    'resource_spec.backend_group.capacity': t('集群容量需求'),
    'resource_spec.backend_group.count': t('需机器组数'),
    'resource_spec.backend_group.future_capacity': t('未来集群容量需求'),
    'resource_spec.backend_group.labels': t('后端存储资源标签'),
    'resource_spec.backend_group.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.backend_group.spec_id': t('后端存储资源规格'),
    'resource_spec.spider.count': t('数量'),
    'resource_spec.spider.labels': t('Spider Master 资源标签'),
    'resource_spec.spider.spec_id': t('Spider Master 规格'),
    spider_port: t('访问端口'),
  },
};

/**
 * Redis 集群部署：地域、容灾以顶层字段为准，园区按 backend_group 的 location_spec 计，proxy 与之相同不重复计；
 * 随之带出的 affinity / location_spec.city、proxy 规格带出的 capacity、随部署架构带出的 proxy 规格类型、
 * 后端存储方案明细 spec_info、由所属业务带出的业务代号不计入差异。单机分片数不保存，只体现在 cluster_shard_num 上，所以它计入差异
 */
const REDIS_CLUSTER_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    apply_clb: (value) => (value ? 'CLB' : '--'),
    apply_polaris: (value) => (value ? t('北极星') : '--'),
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
    'nodes.*': (value) => formatValue((value as HostList)?.map((item) => item.ip)),
    // details 里是明文密码，不展示
    proxy_pwd: (value) => (value ? '******' : '--'),
    // 后端存储的规格名在方案明细 spec_info 里
    'resource_spec.backend_group.spec_id': (value, snapshot) =>
      formatValue(_.get(snapshot, 'resource_spec.backend_group.spec_info.spec_name') || value),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'city_name',
    'db_app_abbr',
    'resource_spec.*.affinity',
    'resource_spec.*.location_spec.city',
    'resource_spec.backend_group.spec_info',
    'resource_spec.proxy.capacity',
    'resource_spec.proxy.location_spec',
    'resource_spec.proxy.spec_cluster_type',
    'resource_spec.proxy.spec_machine_type',
  ],
  labels: {
    apply_clb: t('负载均衡'),
    apply_polaris: t('负载均衡'),
    bk_cloud_id: t('管控区域'),
    cap_key: t('总容量'),
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    cluster_shard_num: t('集群分片数'),
    cluster_type: t('部署架构'),
    db_version: t('版本'),
    disaster_tolerance_level: t('容灾要求'),
    'nodes.master': t('Master 主机'),
    'nodes.proxy': t('Proxy 主机'),
    'nodes.slave': t('Slave 主机'),
    proxy_port: t('访问端口'),
    proxy_pwd: t('访问密码'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.backend_group.count': t('需机器组数'),
    'resource_spec.backend_group.labels': t('资源标签'),
    'resource_spec.backend_group.spec_id': t('后端存储'),
    'resource_spec.proxy.count': t('Proxy 数量'),
    'resource_spec.proxy.labels': t('Proxy 资源标签'),
    'resource_spec.proxy.spec_id': t('Proxy 规格'),
  },
};

/**
 * Redis 主从部署：地域、容灾以顶层字段为准，园区按 backend_group 的 location_spec 计；随之带出的
 * affinity / location_spec.city、规格带出的 capacity、随部署方式带出的 ip_source、由所属业务带出的业务代号不计入差异。
 * 后端不保存「每组主机部署集群」，它的改动只体现在 backend_group.count 上，所以 count 计入差异
 */
const REDIS_INS_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    append_apply: (value) => (value ? t('已有主从所在主机追加部署') : t('全新主机部署')),
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
    // 只拼集群标识时，只改 Databases 或追加部署的主库主机，变更前后看起来一样
    infos: (value) =>
      formatValue(
        (value as RedisInsInfoList)?.map((item) =>
          _.compact([item.cluster_name, `Databases: ${item.databases}`, item.backend_group?.master.ip]).join(' / '),
        ),
      ),
    // details 里是明文密码，不展示
    redis_pwd: (value) => (value ? '******' : '--'),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'db_app_abbr',
    'ip_source',
    'resource_spec.*.affinity',
    'resource_spec.*.capacity',
    'resource_spec.*.location_spec.city',
  ],
  labels: {
    append_apply: t('部署方式'),
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    db_version: t('Redis 版本'),
    disaster_tolerance_level: t('容灾要求'),
    infos: t('域名设置'),
    port: t('Redis 起始端口'),
    redis_pwd: t('访问密码'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.backend_group.count': t('需机器组数'),
    'resource_spec.backend_group.labels': t('资源标签'),
    'resource_spec.backend_group.spec_id': t('后端存储规格'),
  },
};

/**
 * MongoDB 副本集部署：地域、容灾以顶层字段为准，园区按 resource_spec 下的 location_spec 计；
 * 随之带出的 city_name / affinity / location_spec.city、规格带出的 capacity、与 Shard 节点数同值的 count、
 * 与 resource_spec 同值的顶层 spec_id 不计入差异
 */
const MONGODB_REPLICASET_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
    replica_sets: (value) =>
      formatValue((value as ReplicaSetList)?.map((item) => (item.name ? `${item.domain}(${item.name})` : item.domain))),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'city_name',
    'resource_spec.*.affinity',
    'resource_spec.*.capacity',
    'resource_spec.*.count',
    'resource_spec.*.location_spec.city',
    'spec_id',
  ],
  labels: {
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    db_version: t('MongoDB版本'),
    disaster_tolerance_level: t('容灾级别'),
    node_count: t('Shard 节点数'),
    node_replica_count: t('每组主机部署副本集数量'),
    oplog_percent: t('每台主机 oplog 容量占比'),
    replica_count: t('部署副本集数量'),
    replica_sets: t('域名设置'),
    'resource_spec.*.labels': t('资源标签'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.*.spec_id': t('后端存储规格'),
    start_port: t('访问端口'),
  },
};

/**
 * MongoDB 分片集群部署：地域、容灾以顶层字段为准；三个角色提交同一份地域容灾参数，园区只按 mongo_config 计。
 * 随之带出的 city_name / affinity / location_spec.city、Config Server 与 Mongos 规格带出的 capacity 不计入差异；
 * ShardSvr 的 capacity 是用户填写的容量需求，count 是「每个 Shard 节点数」唯一的提交载体，都计入差异
 */
const MONGODB_SHARD_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'city_name',
    'resource_spec.*.affinity',
    'resource_spec.*.location_spec.city',
    'resource_spec.mongo_config.capacity',
    'resource_spec.mongodb.location_spec',
    'resource_spec.mongos.capacity',
    'resource_spec.mongos.location_spec',
    'sub_zone_ids',
  ],
  labels: {
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    db_version: t('MongoDB版本'),
    disaster_tolerance_level: t('容灾级别'),
    oplog_percent: t('每台主机 oplog 容量占比'),
    'resource_spec.mongo_config.labels': t('Config Server 资源标签'),
    'resource_spec.mongo_config.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.mongo_config.spec_id': t('Config Server资源规格'),
    'resource_spec.mongodb.capacity': t('集群容量需求'),
    'resource_spec.mongodb.count': t('总机器数'),
    'resource_spec.mongodb.labels': t('资源标签'),
    'resource_spec.mongodb.spec_id': t('ShardSvr资源规格'),
    'resource_spec.mongos.count': t('数量'),
    'resource_spec.mongos.labels': t('Mongos 资源标签'),
    'resource_spec.mongos.spec_id': t('Mongos资源规格'),
    shard_machine_group: t('机器组数'),
    shard_num: t('集群 Shard 数'),
    start_port: t('访问端口'),
  },
};

/**
 * 大数据部署（ES / Kafka / HDFS / Pulsar / Doris）的公共口径：地域以顶层字段为准，各角色共用一份地域园区，
 * 园区只按一个必选角色计。随之带出的 city_name / affinity / location_spec.city、规格带出的 capacity、
 * 由所属业务带出的业务代号不计入差异；各角色数量由用户填写，计入差异。顶层 sub_zone_ids / sub_zone_names 不重复计。
 * 后端把容灾级别统一改写为尽量分散，选「无容灾要求」的唯一效果是带上园区，已由 location_spec.sub_zone_ids 体现，
 * 容灾级别本身不计入差异
 */
const BIG_DATA_APPLY_DIFF: Required<Pick<DiffOptions, 'formatters' | 'ignorePaths'>> = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
    'nodes.*': (value) => formatValue((value as HostList)?.map((item) => item.ip)),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'city_name',
    'db_app_abbr',
    'disaster_tolerance_level',
    'resource_spec.*.affinity',
    'resource_spec.*.capacity',
    'resource_spec.*.location_spec.city',
    'sub_zone_ids',
    'sub_zone_names',
  ],
};

/**
 * ES 部署：园区按必选的 master 计；client / hot / cold 为可选角色，数量为 0 时不提交，增删角色按并集比较
 */
const ES_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...BIG_DATA_APPLY_DIFF.formatters,
    apply_clb: (value) => (value ? 'CLB' : '--'),
    apply_polaris: (value) => (value ? t('北极星') : '--'),
  },
  ignorePaths: [
    ...BIG_DATA_APPLY_DIFF.ignorePaths,
    'resource_spec.client.location_spec',
    'resource_spec.cold.location_spec',
    'resource_spec.hot.location_spec',
  ],
  labels: {
    apply_clb: t('负载均衡'),
    apply_polaris: t('负载均衡'),
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    db_version: t('ES版本'),
    http_port: t('访问端口'),
    'nodes.client': t('Client节点'),
    'nodes.cold': t('冷节点'),
    'nodes.hot': t('热节点'),
    'nodes.master': t('Master节点'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.client.count': t('Client节点'),
    'resource_spec.client.labels': t('Client 节点资源标签'),
    'resource_spec.client.spec_id': t('Client节点规格'),
    'resource_spec.cold.count': t('冷节点'),
    'resource_spec.cold.labels': t('冷节点资源标签'),
    'resource_spec.cold.spec_id': t('冷节点规格'),
    'resource_spec.hot.count': t('热节点'),
    'resource_spec.hot.labels': t('热节点资源标签'),
    'resource_spec.hot.spec_id': t('热节点规格'),
    'resource_spec.master.count': t('Master节点'),
    'resource_spec.master.labels': t('Master 节点资源标签'),
    'resource_spec.master.spec_id': t('Master节点规格'),
  },
  unionPaths: ['resource_spec.*'],
};

/**
 * Kafka 部署：园区按 zookeeper 计（页面回填也取 zookeeper）；zookeeper 固定 3 台、页面不可改，不登记数量名称
 */
const KAFKA_APPLY_DIFF: DiffOptions = {
  formatters: BIG_DATA_APPLY_DIFF.formatters,
  ignorePaths: [...BIG_DATA_APPLY_DIFF.ignorePaths, 'resource_spec.broker.location_spec'],
  labels: {
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    db_version: t('kafka版本'),
    'nodes.broker': t('Broker节点'),
    'nodes.zookeeper': t('Zookeeper节点'),
    partition_num: t('Partition数量'),
    port: t('访问端口'),
    replication_num: t('副本数量'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.broker.count': t('Broker节点'),
    'resource_spec.broker.labels': t('Broker 节点资源标签'),
    'resource_spec.broker.spec_id': t('Broker节点规格'),
    'resource_spec.zookeeper.labels': t('Zookeeper 节点资源标签'),
    'resource_spec.zookeeper.spec_id': t('Zookeeper节点规格'),
    retention_bytes: t('消息保留大小'),
    retention_hours: t('消息保留时间'),
  },
};

/**
 * HDFS 部署：园区按 namenode 计（页面回填也取 namenode）；namenode 固定 2 台、页面不可改，不登记数量名称；
 * 后端不保存 http_port / rpc_port，不参与对比
 */
const HDFS_APPLY_DIFF: DiffOptions = {
  formatters: BIG_DATA_APPLY_DIFF.formatters,
  ignorePaths: [
    ...BIG_DATA_APPLY_DIFF.ignorePaths,
    'resource_spec.datanode.location_spec',
    'resource_spec.zookeeper.location_spec',
  ],
  labels: {
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    db_version: t('Hadoop版本'),
    'nodes.datanode': t('DataNode节点'),
    // NameNode / Zookeeper/JournalNode 是组件名，申请页也未翻译
    'nodes.namenode': 'NameNode',
    'nodes.zookeeper': 'Zookeeper/JournalNode',
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.datanode.count': t('DataNode节点'),
    'resource_spec.datanode.labels': t('DataNodes 资源标签'),
    'resource_spec.datanode.spec_id': t('DataNode节点规格'),
    'resource_spec.namenode.labels': t('NameNode 资源标签'),
    'resource_spec.namenode.spec_id': `NameNode ${t('规格')}`,
    'resource_spec.zookeeper.count': 'Zookeeper/JournalNode',
    'resource_spec.zookeeper.labels': t('Zookeepers/JournalNodes 资源标签'),
    'resource_spec.zookeeper.spec_id': `Zookeeper/JournalNode ${t('规格')}`,
  },
};

/**
 * Pulsar 部署：三个角色园区相同，只按 zookeeper 计（回填也取 zookeeper）
 */
const PULSAR_APPLY_DIFF: DiffOptions = {
  formatters: BIG_DATA_APPLY_DIFF.formatters,
  ignorePaths: [
    ...BIG_DATA_APPLY_DIFF.ignorePaths,
    'resource_spec.bookkeeper.location_spec',
    'resource_spec.broker.location_spec',
  ],
  labels: {
    ack_quorum: t('至少写入成功副本数量'),
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    db_version: t('Pulsar版本'),
    'nodes.bookkeeper': t('Bookkeeper节点'),
    'nodes.broker': t('Broker节点'),
    'nodes.zookeeper': t('Zookeeper节点'),
    partition_num: t('Partition数量'),
    port: t('访问端口'),
    replication_num: t('副本数量'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.bookkeeper.count': t('Bookkeeper节点'),
    'resource_spec.bookkeeper.labels': t('Bookkeeper 节点资源标签'),
    'resource_spec.bookkeeper.spec_id': t('Bookkeeper节点规格'),
    'resource_spec.broker.count': t('Broker节点'),
    'resource_spec.broker.labels': t('Broker 节点资源标签'),
    'resource_spec.broker.spec_id': t('Broker节点规格'),
    'resource_spec.zookeeper.count': t('Zookeeper节点'),
    'resource_spec.zookeeper.labels': t('Zookeeper 节点资源标签'),
    'resource_spec.zookeeper.spec_id': t('Zookeeper节点规格'),
    retention_hours: t('消息保留'),
  },
};

/**
 * Doris 部署：园区只按必选的 follower 计（回填也取 follower）；observer / hot / warm 为可选角色，
 * 数量为 0 时页面与后端都不保存该角色，增删角色按并集比较
 */
const DORIS_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...BIG_DATA_APPLY_DIFF.formatters,
    enable_cold_storage: (value) => (value ? t('是') : t('否')),
  },
  ignorePaths: [
    ...BIG_DATA_APPLY_DIFF.ignorePaths,
    'resource_spec.hot.location_spec',
    'resource_spec.observer.location_spec',
    'resource_spec.warm.location_spec',
  ],
  labels: {
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    db_version: t('Doris版本'),
    enable_cold_storage: t('启用低频存储'),
    http_port: t('http端口'),
    'nodes.follower': t('Follower节点'),
    'nodes.hot': t('热节点'),
    'nodes.observer': t('Observer节点'),
    'nodes.warm': t('温节点'),
    query_port: t('查询端口'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.follower.count': t('Follower节点'),
    'resource_spec.follower.labels': t('Follower 节点资源标签'),
    'resource_spec.follower.spec_id': t('Follower节点规格'),
    'resource_spec.hot.count': t('热节点'),
    'resource_spec.hot.labels': t('热节点资源标签'),
    'resource_spec.hot.spec_id': t('热节点规格'),
    'resource_spec.observer.count': t('Observer节点'),
    'resource_spec.observer.labels': t('Observer节点资源标签'),
    'resource_spec.observer.spec_id': t('Observer节点规格'),
    'resource_spec.warm.count': t('温节点'),
    'resource_spec.warm.labels': t('温节点资源标签'),
    'resource_spec.warm.spec_id': t('温节点规格'),
  },
  unionPaths: ['resource_spec.*'],
};

/**
 * InfluxDB 部署，没有集群维度，按分组部署：地域、容灾以顶层字段为准，园区按 resource_spec 下的 location_spec 计。
 * 随之带出的 affinity（后端会统一改写）/ location_spec.city、规格带出的 capacity、随分组带出的 group_name 不计入差异
 */
const INFLUXDB_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
    group_id: (value, snapshot) => formatValue(snapshot.group_name || value),
    'nodes.*': (value) => formatValue((value as HostList)?.map((item) => item.ip)),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'group_name',
    'resource_spec.*.affinity',
    'resource_spec.*.capacity',
    'resource_spec.*.location_spec.city',
  ],
  labels: {
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    db_version: t('InfluxDB版本'),
    disaster_tolerance_level: t('容灾级别'),
    group_id: t('分组名'),
    'nodes.influxdb': t('InfluxDB实例'),
    port: t('访问端口'),
    'resource_spec.*.labels': t('资源标签'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.influxdb.count': t('数量'),
    'resource_spec.influxdb.spec_id': t('规格'),
  },
};

/**
 * Riak 集群部署：地域、容灾以顶层字段为准，园区按 resource_spec 下的 location_spec 计。随之带出的
 * city_name / affinity / location_spec.city、规格带出的 capacity、随业务带出的 db_app_abbr、随模块带出的 db_module_name 不计入差异
 */
const RIAK_CLUSTER_APPLY_DIFF: DiffOptions = {
  formatters: {
    ...RESOURCE_SPEC_DIFF.formatters,
    city_code: (value, snapshot) => formatValue(snapshot.city_name || value),
    db_module_id: (value, snapshot) => formatValue(snapshot.db_module_name || value),
    'nodes.*': (value) => formatValue((value as HostList)?.map((item) => item.ip)),
  },
  ignorePaths: [
    ...RESOURCE_SPEC_DIFF.ignorePaths,
    'city_name',
    'db_app_abbr',
    'db_module_name',
    'resource_spec.*.affinity',
    'resource_spec.*.capacity',
    'resource_spec.*.location_spec.city',
  ],
  labels: {
    bk_cloud_id: t('管控区域'),
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    db_module_id: t('DB参数模块'),
    disaster_tolerance_level: t('容灾级别'),
    'nodes.riak': t('服务器'),
    'resource_spec.*.labels': t('资源标签'),
    'resource_spec.*.location_spec.sub_zone_ids': t('园区'),
    'resource_spec.riak.count': t('节点数量'),
    'resource_spec.riak.spec_id': t('资源规格'),
  },
};

/**
 * K8s 部署（SurrealDB 集群 / 单节点、Qdrant 集群）提交体与后端 details 字段相同，三种类型共用：
 * 管控区域固定取 0 号，bk_cloud_id / bk_cloud_region 随之带出（bk_cloud_id 提交为字符串、后端存整数）；
 * 业务名、业务代号随所属业务带出，大版本随版本带出，details.remark 是顶层备注的副本，都不计入差异。
 * component_list 为数组，任一组件的 CPU / 内存 / 存储 / 节点数改动整体计 1 项
 */
const K8S_APPLY_DIFF: DiffOptions = {
  formatters: {
    component_list: (value) =>
      formatValue(
        (value as K8sComponentList)?.map((item) => {
          const spec = [`${item.request_cpu}C`, item.request_memory, item.storage].filter(Boolean).join(' / ');
          return `${item.component_name}: ${spec} × ${item.replicas}`;
        }),
      ),
    is_public: (value) => (value === false ? t('独占集群') : t('共享集群')),
  },
  ignorePaths: ['bk_biz_name', 'bk_cloud_id', 'bk_cloud_region', 'db_app_abbr', 'major_version', 'remark'],
  labels: {
    city_code: t('地域'),
    cluster_alias: t('集群别名'),
    cluster_name: t('集群标识'),
    component_list: t('资源配置'),
    db_version: t('版本'),
    is_public: t('部署类型'),
    k8s_cluster_name: t('BCS 集群'),
  },
};

/**
 * 改单接入名单：列入即代为修改、重新编辑、调整申请三种模式一并可用，单据详情只读这份名单，不按单据类型写分支。
 *
 * 接入条件：该类型提单页能以改单模式路由进入（申请页路由名与单据类型同名），按单据现有内容预填全部字段，
 * 按改单规则置只读后提交。提单页完成改造后再列入，并登记变更对比用的字段名称、忽略字段与展示格式。
 * 后端详情序列化器会补 city_name 等展示字段，表单 details 里有同名字段的必须列入忽略，否则会多计变更
 */
export const TICKET_MODIFY_REGISTRY: Partial<Record<TicketTypes, DiffOptions>> = {
  [TicketTypes.DORIS_APPLY]: DORIS_APPLY_DIFF,
  [TicketTypes.ES_APPLY]: ES_APPLY_DIFF,
  [TicketTypes.HDFS_APPLY]: HDFS_APPLY_DIFF,
  [TicketTypes.INFLUXDB_APPLY]: INFLUXDB_APPLY_DIFF,
  [TicketTypes.K8S_QDRANT_HA_APPLY]: K8S_APPLY_DIFF,
  [TicketTypes.K8S_SURREALDB_HA_APPLY]: K8S_APPLY_DIFF,
  [TicketTypes.K8S_SURREALDB_SINGLE_APPLY]: K8S_APPLY_DIFF,
  [TicketTypes.KAFKA_APPLY]: KAFKA_APPLY_DIFF,
  [TicketTypes.MONGODB_REPLICASET_APPLY]: MONGODB_REPLICASET_APPLY_DIFF,
  [TicketTypes.MONGODB_SHARD_APPLY]: MONGODB_SHARD_APPLY_DIFF,
  [TicketTypes.MYSQL_HA_APPLY]: {
    ...MYSQL_APPLY_DIFF,
    labels: {
      ...MYSQL_APPLY_DIFF.labels,
      inst_num: t('每组主机部署集群数量'),
    },
  },
  [TicketTypes.MYSQL_SINGLE_APPLY]: {
    ...MYSQL_APPLY_DIFF,
    labels: {
      ...MYSQL_APPLY_DIFF.labels,
      inst_num: t('每台主机实例数量'),
    },
  },
  [TicketTypes.PULSAR_APPLY]: PULSAR_APPLY_DIFF,
  [TicketTypes.REDIS_CLUSTER_APPLY]: REDIS_CLUSTER_APPLY_DIFF,
  [TicketTypes.REDIS_INS_APPLY]: REDIS_INS_APPLY_DIFF,
  [TicketTypes.RIAK_CLUSTER_APPLY]: RIAK_CLUSTER_APPLY_DIFF,
  [TicketTypes.SQLSERVER_HA_APPLY]: SQLSERVER_APPLY_DIFF,
  [TicketTypes.SQLSERVER_SINGLE_APPLY]: SQLSERVER_APPLY_DIFF,
  [TicketTypes.TENDBCLUSTER_APPLY]: TENDBCLUSTER_APPLY_DIFF,
};

export const isTicketModifiable = (ticketType: TicketTypes) => Boolean(TICKET_MODIFY_REGISTRY[ticketType]);

export const getTicketModifyDiffOptions = (ticketType: TicketTypes) => TICKET_MODIFY_REGISTRY[ticketType] || {};
