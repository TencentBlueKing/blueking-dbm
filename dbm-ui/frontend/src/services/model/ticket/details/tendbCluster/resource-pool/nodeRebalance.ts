import type { ResourcePoolDetailBase } from '../../common';

/**
 * TenDB Cluster 集群容量变更
 */
export interface NodeRebalance extends ResourcePoolDetailBase {
  backup_source: string;
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
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
        specName: string;
      };
    };
    spec_id: number;
  }[];
  need_checksum: true;
  resource_request_id: string;
  trigger_checksum_time: string;
  trigger_checksum_type: string;
}
