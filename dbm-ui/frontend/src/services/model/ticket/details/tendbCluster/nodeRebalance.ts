import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 集群容量变更
 */

export interface NodeRebalance extends DetailBase {
  clusters: DetailClusters;
  need_checksum: true;
  trigger_checksum_type: string;
  trigger_checksum_time: string;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    db_module_id: number;
    cluster_shard_num: number; // 集群分片数
    remote_shard_num: number; // 单机分片数
    resource_spec: {
      backend_group: {
        spec_id: number;
        count: number;
        affinity: string; // 亲和性要求
      };
    };
    prev_machine_pair: number;
    prev_cluster_spec_name: string;
  }[];
}
