import type { DetailBase, DetailClusters, NodeInfo, SpecInfo } from '../common';

/**
 * TenDB Cluster 集群容量变更
 */

export interface NodeRebalance extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    cluster_shard_num: number; // 集群分片数
    prev_cluster_spec_name: string;
    prev_machine_pair: number;
    remote_shard_num: number; // 单机分片数
    resource_spec: {
      backend_group: {
        affinity: string;
        count: number;
        futureCapacity: number;
        specName: string;
        spec_id: number;
      };
    };
  }[];
  ip_source: string;
  need_checksum: true;
  nodes: Record<
    string,
    {
      master: NodeInfo[];
      slave: NodeInfo[];
    }[]
  >;
  resource_request_id: string;
  specs: Record<number, SpecInfo>;
  trigger_checksum_type: string;
  trigger_checksum_time: string;
}
