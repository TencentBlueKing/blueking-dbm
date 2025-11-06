import type { ClusterTypes } from '@common/const';

import type { ResourcePoolDetailBase } from '../../common';

export interface ReplicaAddShardNodes extends ResourcePoolDetailBase {
  cluster_type: ClusterTypes.MONGO_REPLICA_SET;
  infos: {
    add_shard_nodes_num: number;
    cluster_ids: number[];
    current_shard_nodes_num: number;
    db_version: string;
    node_replica_count: number;
    resource_spec: {
      shard_nodes: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  is_safe: boolean;
}
