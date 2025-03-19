import type { ResourcePoolDetailBase } from '../../common';

type MongoInstanceInfo = {
  cluster_ids: number[];
  current_shard_nodes_num: number;
  db_version: string;
  machine_instance_num: number;
  reduce_shard_nodes: number;
  shard_num: number;
}[];

export interface ReduceShardNodes extends ResourcePoolDetailBase {
  infos: {
    MongoReplicaSet: MongoInstanceInfo;
    MongoShardedCluster: MongoInstanceInfo;
    old_nodes: {
      reduced_shard_hosts: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
  };
  is_safe: boolean;
}
