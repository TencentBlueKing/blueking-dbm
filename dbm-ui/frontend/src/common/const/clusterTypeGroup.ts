import type { DBTypes } from './dbTypes';
import { clusterTypesByDBTypeRaw } from './queryClusterTypes';

// DBTypes → ClusterTypes 映射类型（可索引访问具体 DB 大类对应的集群类型联合）
export type ClusterTypeGroup = { [K in DBTypes]: (typeof clusterTypesByDBTypeRaw)[K][number] };

// 所有已登记集群类型的联合
export type GroupedClusterTypes = ClusterTypeGroup[DBTypes];

// 正向查询：给定 DB 大类，返回其包含的集群类型联合
export type ClusterTypesOf<T extends DBTypes> = ClusterTypeGroup[T];

// 反向查询：给定集群类型，推导其所属的 DB 大类
export type DBTypeOf<C extends GroupedClusterTypes> = {
  [K in DBTypes]: C extends (typeof clusterTypesByDBTypeRaw)[K][number] ? K : never;
}[DBTypes];
