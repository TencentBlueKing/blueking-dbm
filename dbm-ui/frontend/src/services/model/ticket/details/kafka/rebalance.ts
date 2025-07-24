import type { DetailBase, DetailClusters } from '../common';

/**
 * Kafka Topic 均衡
 */
export interface Rebalance extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
  instance_info: {
    agent_status: number;
    create_at: string;
    intance_address: string;
  }[];
  instance_list: {
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
  }[];
  throttle_rate: number;
  topics: string[];
}
