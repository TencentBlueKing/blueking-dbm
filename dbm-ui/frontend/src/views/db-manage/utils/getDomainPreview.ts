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
import { ClusterTypes } from '@common/const';

/** 域名占位文字 */
const DomainPlaceholders = {
  clusterName: '{集群标识}',
  dbAppAbbr: '{业务代号}',
  moduleName: '{模块名}',
} as const;

// ==================== 类型定义 ====================

/** MySQL / SQLServer 集群类型集合 */
type MysqlSqlserverType =
  ClusterTypes.TENDBHA | ClusterTypes.TENDBSINGLE | ClusterTypes.SQLSERVER_HA | ClusterTypes.SQLSERVER_SINGLE;

/** 大数据集群类型集合 */
type BigDataType = ClusterTypes.DORIS | ClusterTypes.ES | ClusterTypes.HDFS | ClusterTypes.KAFKA | ClusterTypes.PULSAR;

/** Mongodb 集群类型集合 */
type MongodbType = ClusterTypes.MONGO_REPLICA_SET | ClusterTypes.MONGO_SHARED_CLUSTER;

/** Redis 集群类型集合 */
type RedisType =
  | ClusterTypes.REDIS_INSTANCE
  | ClusterTypes.TWEMPROXY_REDIS_INSTANCE
  | ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE
  | ClusterTypes.PREDIXY_REDIS_CLUSTER
  | ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE
  | ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER;

/**
 * 域名分段结构（按集群标识分界）
 */
export interface DomainSegment {
  /** 前缀（集群标识之前的部分） */
  prefix: string;
  /** 后缀（集群标识之后的部分） */
  suffix: string;
}

/**
 * 域名预览结果接口
 */
export interface DomainPreviewResult {
  /** 主域名 */
  masterDomain: DomainSegment;
  /** 从域名（如果有的话） */
  slaveDomain?: DomainSegment;
}

/**
 * 策略执行参数接口
 */
export interface BaseDomainStrategyParams {
  /** 集群标识 */
  clusterName: string;
  /** 业务代号 */
  dbAppAbbr: string;
}

/**
 * MySQL / SQLServer 策略执行参数（需要模块名）
 */
export interface MysqlSqlserverStrategyParams extends BaseDomainStrategyParams {
  /** 模块名 */
  moduleName: string;
}

/**
 * 泛型策略执行参数 - 根据 clusterType 约束不同参数
 */
export type DomainStrategyParams<T extends ClusterTypes = ClusterTypes> = T extends MysqlSqlserverType
  ? { clusterType: T } & MysqlSqlserverStrategyParams
  : { clusterType: T } & BaseDomainStrategyParams;

// ==================== 策略定义 ====================

/**
 * 域名生成策略上下文参数
 */
interface StrategyContext {
  /** 集群标识（有值或占位符） */
  clusterName: string;
  /** 业务代号（有值或占位符） */
  dbAppAbbr: string;
  /** 模块名（有值或占位符） */
  moduleName: string;
}

/**
 * 内部基础策略函数类型（用于策略链存储）
 */
type BaseDomainStrategy = (ctx: StrategyContext, params: Record<string, unknown>) => DomainPreviewResult;

/**
 * 域名生成策略函数类型（对外暴露，带泛型约束）
 *
 * @example
 * ```typescript
 * // 获取 MySQL 策略后执行
 * const strategy = getDomainStrategy(ClusterTypes.TENDBHA);
 * const result = strategy({
 *   clusterType: ClusterTypes.TENDBHA,
 *   clusterName: 'my-cluster',
 *   dbAppAbbr: 'testdb',
 *   moduleName: 'mymodule', // MySQL 必须传
 * });
 * ```
 */
export type DomainStrategy<T extends ClusterTypes = ClusterTypes> = (
  params: DomainStrategyParams<T>,
) => DomainPreviewResult;

/**
 * MySQL / SQLServer 域名策略：{模块名}db.{集群标识}.{业务代号}.db / {模块名}dr.{集群标识}.{业务代号}.db
 */
const mysqlSqlserverStrategy: BaseDomainStrategy = (ctx, { bizId }) => {
  const dbAppAbbr = ctx.dbAppAbbr || `biz-${bizId}`;
  return {
    masterDomain: { prefix: `${ctx.moduleName}db.`, suffix: `.${dbAppAbbr}.db` },
    slaveDomain: { prefix: `${ctx.moduleName}dr.`, suffix: `.${dbAppAbbr}.db` },
  };
};

/**
 * TenDBCluster 域名策略：spider.{集群标识}.{业务代号}.db
 */
const tendbclusterStrategy: BaseDomainStrategy = (ctx) => ({
  masterDomain: { prefix: 'spider.', suffix: `.${ctx.dbAppAbbr}.db` },
});

/**
 * Mongodb 域名策略：固定前缀.{集群标识}.{业务代号}.db
 */
const mongodbStrategy: BaseDomainStrategy = (ctx, params) => {
  const MongodbTypeMap: Partial<Record<MongodbType, string>> = {
    [ClusterTypes.MONGO_REPLICA_SET]: 'm1',
    [ClusterTypes.MONGO_SHARED_CLUSTER]: 'mongos',
  };
  const clusterType = params.clusterType;
  const prefix = MongodbTypeMap[clusterType];
  return { masterDomain: { prefix: `${prefix}.`, suffix: `.${ctx.dbAppAbbr}.db` } };
};

/**
 * Redis 域名策略：{集群类型}.{集群标识}.{业务代号}.db
 */
const redisStrategy: BaseDomainStrategy = (ctx, params) => {
  /** Redis 集群类型到域名前缀的映射 */
  const RedisClusterTypeMap: Partial<Record<RedisType, string>> = {
    [ClusterTypes.PREDIXY_REDIS_CLUSTER]: 'rediscluster',
    [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: 'tendisplus',
    [ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE]: 'tendisplus',
    [ClusterTypes.REDIS_INSTANCE]: 'ins',
    [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: 'cache',
    [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: 'ssd',
  };
  console.log('??');
  const redisType = params.clusterType;
  const prefix = RedisClusterTypeMap[redisType];
  return { masterDomain: { prefix: `${prefix}.`, suffix: `.${ctx.dbAppAbbr}.db` } };
};

/**
 * 大数据域名策略，无模块（ES/Kafka/Doris/HDFS）：{数据库类型}.{集群标识}.{业务代号}.db
 */
const bigDataNoModuleStrategy: BaseDomainStrategy = (ctx, params) => {
  const DbTypeToPrefixMap: Partial<Record<ClusterTypes, string>> = {
    [ClusterTypes.DORIS]: 'doris',
    [ClusterTypes.ES]: 'es',
    [ClusterTypes.HDFS]: 'hdfs',
    [ClusterTypes.KAFKA]: 'kafka',
    [ClusterTypes.PULSAR]: 'pulsar',
  };
  const prefix = DbTypeToPrefixMap[params.clusterType as BigDataType];
  return { masterDomain: { prefix: `${prefix}.`, suffix: `.${ctx.dbAppAbbr}.db` } };
};

/**
 * 大数据域名策略，有模块（Riak）：{数据库类型}.{集群标识}-{模块名}.{业务代号}.db
 */
const bigDataWithModuleStrategy: BaseDomainStrategy = (ctx, params) => {
  const DbTypeToPrefixMap: Partial<Record<ClusterTypes, string>> = {
    [ClusterTypes.RIAK]: 'riak',
  };
  const prefix = DbTypeToPrefixMap[params.clusterType as BigDataType];
  return {
    masterDomain: { prefix: `${prefix}.`, suffix: `-${ctx.moduleName}.${ctx.dbAppAbbr}.db` },
  };
};

/**
 * k8s域名策略：{数据库类型}.{集群标识}.{业务代号}.db
 */
const k8sStrategy: BaseDomainStrategy = (ctx, params) => {
  const DbTypeToPrefixMap: Partial<Record<ClusterTypes, string>> = {
    [ClusterTypes.K8S_QDRANT_HA]: 'qdrant',
    [ClusterTypes.K8S_SURREALDB_HA]: 'surrealdb',
    [ClusterTypes.K8S_SURREALDB_SINGLE]: 'surrealdb',
  };
  const prefix = DbTypeToPrefixMap[params.clusterType as BigDataType];
  return { masterDomain: { prefix: `${prefix}.`, suffix: `.${ctx.dbAppAbbr}.db` } };
};

/**
 * 默认域名策略
 */
const defaultStrategy: BaseDomainStrategy = () => ({
  masterDomain: { prefix: '', suffix: '' },
});

/** 策略映射表（clusterType → 策略函数） */
const strategyMap: Partial<Record<ClusterTypes, BaseDomainStrategy>> = {
  [ClusterTypes.DORIS]: bigDataNoModuleStrategy,
  [ClusterTypes.ES]: bigDataNoModuleStrategy,
  [ClusterTypes.HDFS]: bigDataNoModuleStrategy,
  [ClusterTypes.K8S_QDRANT_HA]: k8sStrategy,
  [ClusterTypes.K8S_SURREALDB_HA]: k8sStrategy,
  [ClusterTypes.K8S_SURREALDB_SINGLE]: k8sStrategy,
  [ClusterTypes.KAFKA]: bigDataNoModuleStrategy,
  [ClusterTypes.MONGO_REPLICA_SET]: mongodbStrategy,
  [ClusterTypes.MONGO_SHARED_CLUSTER]: mongodbStrategy,
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: redisStrategy,
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: redisStrategy,
  [ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE]: redisStrategy,
  [ClusterTypes.PULSAR]: bigDataNoModuleStrategy,
  [ClusterTypes.REDIS_INSTANCE]: redisStrategy,
  [ClusterTypes.RIAK]: bigDataWithModuleStrategy,
  [ClusterTypes.SQLSERVER]: mysqlSqlserverStrategy,
  [ClusterTypes.SQLSERVER_HA]: mysqlSqlserverStrategy,
  [ClusterTypes.SQLSERVER_SINGLE]: mysqlSqlserverStrategy,
  [ClusterTypes.TENDBCLUSTER]: tendbclusterStrategy,
  [ClusterTypes.TENDBHA]: mysqlSqlserverStrategy,
  [ClusterTypes.TENDBSINGLE]: mysqlSqlserverStrategy,
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: redisStrategy,
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: redisStrategy,
};

// ==================== 内部工具函数 ====================

/**
 * 从策略参数构建策略上下文
 */
function buildContext(params: Record<string, unknown>): StrategyContext {
  return {
    clusterName: (params.clusterName as string) || DomainPlaceholders.clusterName,
    dbAppAbbr: (params.dbAppAbbr as string) || DomainPlaceholders.dbAppAbbr,
    moduleName: (params.moduleName as string) || DomainPlaceholders.moduleName,
  };
}

// ==================== 公共 API ====================

/**
 * 根据集群类型获取对应的域名生成策略（带泛型约束）
 * @param clusterType 集群类型
 * @returns 对应类型的域名生成策略函数
 *
 * @example
 * ```typescript
 * // 获取 MySQL 策略 - 执行时需要传入 moduleName
 * const strategy = getDomainStrategy(ClusterTypes.TENDBHA);
 * const result = strategy({
 *   clusterType: ClusterTypes.TENDBHA,
 *   clusterName: 'my-cluster',
 *   dbAppAbbr: 'testdb',
 *   moduleName: 'mymodule', // 必填
 * });
 *
 * // 获取 Redis 策略 -
 * const redisStrategy = getDomainStrategy(ClusterTypes.REDIS_CLUSTER);
 * const redisResult = redisStrategy({
 *   clusterType: ClusterTypes.REDIS_CLUSTER,
 *   clusterName: 'redis-01',
 *   dbAppAbbr: 'testdb',
 * });
 * ```
 */
export function getDomainStrategy<T extends ClusterTypes>(clusterType: T): DomainStrategy<T> {
  const strategy = strategyMap[clusterType] || defaultStrategy;
  return ((params: DomainStrategyParams<T>) =>
    strategy(buildContext(params as unknown as Record<string, unknown>), {
      ...params,
      clusterType,
    } as unknown as Record<string, unknown>)) as DomainStrategy<T>;
}
